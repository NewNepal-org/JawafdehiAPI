"""
Workflow ABC — defines the contract for all case workflow templates,
and owns the execution logic (formerly in WorkflowRunner).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, List

from django.conf import settings

if TYPE_CHECKING:
    from case_workflows.models import CaseWorkflowRun

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WorkflowStep
# ---------------------------------------------------------------------------


@dataclass
class WorkflowStep:
    """A single step within a workflow template."""

    id: str
    title: str
    description: str
    priority: int
    acceptance_criteria: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Workflow ABC
# ---------------------------------------------------------------------------


class Workflow(ABC):
    """
    Abstract base class for all case workflow templates.

    Subclasses live under ``case_workflows/workflows/<template_id>/workflow.py``
    and are auto-discovered by the registry on Django startup.

    Each instance doubles as both the template definition **and** the executor:

    .. code-block:: python

        workflow = get_workflow("ciaa_caseworker")
        workflow.initialize(runner="kiro")
        work_dir = workflow.setup_work_dir(run)
        workflow.execute(run, runner="kiro")
    """

    # ------------------------------------------------------------------
    # Template contract (must implement in subclasses)
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def workflow_id(self) -> str:
        """Unique identifier matching the template directory name."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in CLI output and admin."""
        ...

    @property
    @abstractmethod
    def steps(self) -> List[WorkflowStep]:
        """Ordered list of workflow steps."""
        ...

    @abstractmethod
    def get_eligible_cases(self) -> List[str]:
        """
        Return a list of Jawafdehi ``Case.case_id`` strings eligible for
        this workflow (e.g. ``["case-abc123", "case-def456"]``).

        The management command will iterate over these and create / resume
        a ``CaseWorkflowRun`` for each one.
        """
        ...

    @abstractmethod
    def get_prd_template(self) -> dict:
        """Return the PRD template dict to seed ``prd.json`` in each work dir."""
        ...

    # ------------------------------------------------------------------
    # Optional overrides
    # ------------------------------------------------------------------

    def get_template_dir(self) -> Path:
        """Directory containing this template's files (default: module dir)."""
        return Path(__file__).resolve().parent

    def get_instructions_dir(self) -> Path:
        """Directory containing instruction files for the agent."""
        return self.get_template_dir() / "instructions"

    def get_agent_name(self) -> str:
        """Agent name passed to the runner CLI."""
        return self.workflow_id

    def get_mcp_config_path(self) -> Path | None:
        """Return path to an MCP config JSON, or ``None`` to skip."""
        candidate = self.get_template_dir() / "etc" / "copilot-mcp-config.json"
        return candidate if candidate.exists() else None

    def on_work_dir_created(self, case_dir: Path) -> None:
        """
        Called after the base work directory is created.

        Override to add template-specific directory structure or files.
        Default is a no-op.
        """

    def on_initialize(self, runner: str) -> None:
        """
        Called after the runner binary is validated.

        Override to perform provider-specific setup, e.g. symlinking agent
        config files into the runner's config directory.
        Default is a no-op.
        """

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, runner: str = "copilot") -> None:
        """
        Verify the runner is usable and perform any one-time setup.

        Raises ``RuntimeError`` if the runner binary cannot be found.
        Calls ``on_initialize(runner)`` for template-specific setup.
        """
        self._resolve_agent_binary(runner)
        logger.info("Runner '%s' is available", runner)
        self.on_initialize(runner)

    # ------------------------------------------------------------------
    # Work directory
    # ------------------------------------------------------------------

    def get_work_dir(self, run: CaseWorkflowRun) -> Path:
        """
        Return the work directory path for a given run.

        Structure: ``<CASE_WORKFLOWS_WORK_DIR>/<workflow_id>/<case_id>/``
        """
        base = getattr(
            settings,
            "CASE_WORKFLOWS_WORK_DIR",
            Path(settings.BASE_DIR) / "workflow-runs",
        )
        return Path(base) / self.workflow_id / run.case_id

    def setup_work_dir(self, run: CaseWorkflowRun) -> Path:
        """
        Create the work directory for a run and populate base files.

        - If the directory already exists, logs a warning and deletes it
        - Copies the PRD template as ``prd.json``
        - Creates an empty ``progress.log``
        - Calls ``on_work_dir_created(case_dir)`` for template-specific setup

        Persists ``run.work_dir`` and returns the directory path.
        """
        case_dir = self.get_work_dir(run)

        if case_dir.is_dir():
            logger.warning(
                "Work directory already exists — deleting and recreating: %s", case_dir
            )
            shutil.rmtree(case_dir)

        case_dir.mkdir(parents=True, exist_ok=True)

        # Copy PRD template
        with open(case_dir / "prd.json", "w") as f:
            json.dump(self.get_prd_template(), f, indent=2)

        # Empty progress log
        (case_dir / "progress.log").write_text("")

        # Template-specific extra setup
        self.on_work_dir_created(case_dir)

        run.work_dir = str(case_dir)
        run.save(update_fields=["work_dir", "updated_at"])

        logger.info("Work directory created: %s", case_dir)
        return case_dir

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        run: CaseWorkflowRun,
        *,
        max_iterations: int = 15,
        runner: str = "copilot",
    ) -> None:
        """
        Main execution loop: check PRD completion, invoke agent CLI, repeat.

        Updates ``run`` on completion or failure.
        """
        case_dir = self.get_work_dir(run)
        if not case_dir.is_dir():
            raise RuntimeError(
                f"Work directory does not exist — call setup_work_dir() first: {case_dir}"
            )

        agent_bin = self._resolve_agent_binary(runner)

        run.mark_started()
        logger.info("Starting workflow loop for %s (runner=%s)", run.case_id, runner)

        retry_count = 0
        iteration_count = 0

        try:
            while iteration_count < max_iterations:
                # Check PRD completion
                prd_state = self._read_prd(case_dir)
                if prd_state and prd_state.get("is_complete", False):
                    if prd_state.get("failed", False):
                        run.mark_failed(
                            error_message="Workflow marked as failed in prd.json",
                            case_data=prd_state,
                        )
                        logger.warning("Workflow %s failed (prd.json flag)", run.case_id)
                    else:
                        run.mark_complete(case_data=prd_state)
                        logger.info("Workflow %s completed successfully", run.case_id)
                    return

                logger.info(
                    "Iteration %d/%d for %s",
                    iteration_count + 1,
                    max_iterations,
                    run.case_id,
                )

                cmd = self._build_command(agent_bin, runner, case_dir)

                try:
                    result = subprocess.run(cmd)
                    exit_code = result.returncode
                except KeyboardInterrupt:
                    logger.warning("Workflow interrupted by user")
                    run.mark_failed(error_message="Interrupted by user")
                    return

                if exit_code != 0:
                    if exit_code == 130:
                        logger.warning("Workflow interrupted (exit 130)")
                        run.mark_failed(error_message="Interrupted (exit 130)")
                        return

                    retry_count += 1
                    if retry_count > 3:
                        msg = f"{runner} CLI failed {retry_count} times consecutively"
                        logger.error(msg)
                        run.mark_failed(error_message=msg)
                        return

                    logger.warning(
                        "%s CLI exited %d — retry %d/3 in 10s",
                        runner,
                        exit_code,
                        retry_count,
                    )
                    time.sleep(10)
                    continue

                retry_count = 0
                iteration_count += 1
                time.sleep(2)

            # Exhausted iterations
            prd_state = self._read_prd(case_dir) or {}
            run.mark_failed(
                error_message=f"Reached max iterations ({max_iterations})",
                case_data=prd_state,
            )
            logger.warning("Max iterations reached for %s", run.case_id)

        except Exception as exc:
            run.mark_failed(error_message=str(exc))
            logger.exception("Workflow execution error for %s", run.case_id)
            raise

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_agent_binary(self, runner: str) -> str:
        """Locate the agent CLI binary on PATH. Raises ``RuntimeError`` if missing."""
        if runner == "copilot":
            codespaces = "/home/codespace/.local/bin/copilot"
            if os.path.isfile(codespaces):
                return codespaces
            found = shutil.which("copilot")
            if not found:
                raise RuntimeError(
                    "'copilot' not found on PATH. Install GitHub Copilot CLI first."
                )
            return found
        elif runner == "kiro":
            found = shutil.which("kiro-cli")
            if not found:
                raise RuntimeError("'kiro-cli' not found on PATH.")
            return found
        else:
            raise ValueError(f"Unknown runner: {runner!r}")

    def _build_command(
        self, agent_bin: str, runner: str, case_dir: Path
    ) -> list[str]:
        """Assemble the agent CLI invocation."""
        prompt = f"Follow {case_dir}/instructions/INSTRUCTIONS.md"
        if runner == "copilot":
            cmd = [
                agent_bin,
                "--allow-all",
                "--agent",
                self.get_agent_name(),
            ]
            mcp_config = self.get_mcp_config_path()
            if mcp_config and mcp_config.exists():
                cmd += ["--additional-mcp-config", f"@{mcp_config}"]
            cmd += ["-p", prompt]
            return cmd
        else:  # kiro
            return [
                agent_bin,
                "chat",
                "--agent",
                self.get_agent_name(),
                "--no-interactive",
                "--require-mcp-startup",
                prompt,
            ]

    @staticmethod
    def _read_prd(case_dir: Path) -> dict | None:
        """Read and parse ``prd.json`` from the work directory."""
        prd_file = case_dir / "prd.json"
        if not prd_file.exists():
            return None
        try:
            with open(prd_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read prd.json: %s", exc)
            return None
