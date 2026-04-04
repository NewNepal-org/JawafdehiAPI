"""
WorkflowRunner — orchestrates execution of a workflow for a single case.

Ported from ``.agents/caseworker/run_workflow.py`` with Django integration.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone

if TYPE_CHECKING:
    from case_workflows.models import CaseWorkflowRun
    from case_workflows.workflow import Workflow

logger = logging.getLogger(__name__)


class WorkflowRunner:
    """
    Runs a workflow for a single case.

    Lifecycle::

        runner = WorkflowRunner(workflow, run)
        runner.setup_work_dir()
        runner.execute(max_iterations=15, runner="copilot")
    """

    def __init__(self, workflow: Workflow, run: CaseWorkflowRun):
        self.workflow = workflow
        self.run = run

    # ------------------------------------------------------------------
    # Work directory setup
    # ------------------------------------------------------------------

    def get_work_dir(self) -> Path:
        """
        Return the work directory for this run.

        Structure: ``<base>/workflows/<workflow_id>/<case_id>/``
        """
        base = getattr(
            settings,
            "CASE_WORKFLOWS_WORK_DIR",
            Path(settings.BASE_DIR) / "workflows",
        )
        return Path(base) / self.workflow.workflow_id / self.run.case_id

    def setup_work_dir(self, *, overwrite: bool = False) -> Path:
        """
        Create the case working directory and populate it.

        - Creates ``sources/raw/`` and ``sources/markdown/`` sub-dirs
        - Copies the PRD template as ``prd.json``
        - Symlinks the instructions directory
        - Initialises ``progress.log``

        Returns the work directory path.
        """
        case_dir = self.get_work_dir()

        if case_dir.is_dir():
            if overwrite:
                logger.info("Overwriting existing work dir: %s", case_dir)
                shutil.rmtree(case_dir)
            else:
                logger.info("Reusing existing work dir: %s", case_dir)
                # Update the model to point at this directory
                self.run.work_dir = str(case_dir)
                self.run.save(update_fields=["work_dir", "updated_at"])
                return case_dir

        # Create directory tree
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "sources" / "raw").mkdir(parents=True, exist_ok=True)
        (case_dir / "sources" / "markdown").mkdir(parents=True, exist_ok=True)

        # Copy PRD template
        prd_data = self.workflow.get_prd_template()
        prd_file = case_dir / "prd.json"
        with open(prd_file, "w") as f:
            json.dump(prd_data, f, indent=2)

        # Symlink instructions
        instructions_src = self.workflow.get_instructions_dir()
        instructions_dest = case_dir / "instructions"
        if instructions_dest.exists():
            if instructions_dest.is_symlink() or instructions_dest.is_file():
                instructions_dest.unlink()
            else:
                shutil.rmtree(instructions_dest)
        try:
            os.symlink(instructions_src, instructions_dest)
        except OSError as exc:
            logger.warning("Failed to symlink instructions: %s", exc)

        # Initialise progress.log
        log_file = case_dir / "progress.log"
        timestamp = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y").strip()
        log_file.write_text(f"Case workflow started at {timestamp}\n")

        # Persist work_dir on the model
        self.run.work_dir = str(case_dir)
        self.run.save(update_fields=["work_dir", "updated_at"])

        logger.info("Work directory created: %s", case_dir)
        return case_dir

    # ------------------------------------------------------------------
    # Execution loop
    # ------------------------------------------------------------------

    def execute(
        self,
        *,
        max_iterations: int = 15,
        runner: str = "copilot",
    ) -> None:
        """
        Main loop: check PRD completion, invoke agent CLI, repeat.

        Updates ``CaseWorkflowRun`` on completion or failure.
        """
        case_dir = self.get_work_dir()
        if not case_dir.is_dir():
            raise RuntimeError(
                f"Work directory does not exist — call setup_work_dir() first: {case_dir}"
            )

        agent_bin = self._resolve_agent_binary(runner)

        self.run.mark_started()
        logger.info(
            "Starting workflow loop for %s (runner=%s, max_iter=%d)",
            self.run.case_id,
            runner,
            max_iterations,
        )

        retry_count = 0
        iteration_count = 0

        try:
            while iteration_count < max_iterations:
                # ---- check PRD completion ----
                prd_state = self._read_prd(case_dir)
                if prd_state:
                    if prd_state.get("is_complete", False):
                        if prd_state.get("failed", False):
                            self.run.mark_failed(
                                error_message="Workflow marked as failed in prd.json",
                                case_data=prd_state,
                            )
                            logger.warning(
                                "Workflow %s failed (prd.json flag)",
                                self.run.case_id,
                            )
                        else:
                            self.run.mark_complete(case_data=prd_state)
                            logger.info(
                                "Workflow %s completed successfully",
                                self.run.case_id,
                            )
                        return

                logger.info(
                    "Iteration %d/%d for %s",
                    iteration_count + 1,
                    max_iterations,
                    self.run.case_id,
                )

                # ---- build CLI command ----
                cmd = self._build_command(
                    agent_bin, runner, case_dir
                )

                # ---- invoke agent ----
                try:
                    result = subprocess.run(cmd)
                    exit_code = result.returncode
                except KeyboardInterrupt:
                    logger.warning("Workflow interrupted by user")
                    self.run.mark_failed(error_message="Interrupted by user")
                    return

                if exit_code != 0:
                    if exit_code == 130:
                        logger.warning("Workflow interrupted (exit 130)")
                        self.run.mark_failed(error_message="Interrupted (exit 130)")
                        return

                    retry_count += 1
                    if retry_count > 3:
                        msg = (
                            f"{runner} CLI failed {retry_count} times consecutively"
                        )
                        logger.error(msg)
                        self.run.mark_failed(error_message=msg)
                        return

                    logger.warning(
                        "%s CLI exited %d — retry %d/3 in 10s",
                        runner,
                        exit_code,
                        retry_count,
                    )
                    time.sleep(10)
                    continue

                # Successful iteration
                retry_count = 0
                iteration_count += 1
                time.sleep(2)

            # Exhausted iterations
            prd_state = self._read_prd(case_dir) or {}
            self.run.mark_failed(
                error_message=f"Reached max iterations ({max_iterations})",
                case_data=prd_state,
            )
            logger.warning(
                "Max iterations reached for %s", self.run.case_id
            )

        except Exception as exc:
            self.run.mark_failed(error_message=str(exc))
            logger.exception("Workflow execution error for %s", self.run.case_id)
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_agent_binary(self, runner: str) -> str:
        """Locate the agent CLI binary on PATH."""
        if runner == "copilot":
            # Try well-known Codespaces path first
            codespaces_path = "/home/codespace/.local/bin/copilot"
            if os.path.isfile(codespaces_path):
                return codespaces_path
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
            raise ValueError(f"Unknown runner: {runner}")

    def _build_command(
        self, agent_bin: str, runner: str, case_dir: Path
    ) -> list[str]:
        """Assemble the CLI invocation."""
        if runner == "copilot":
            cmd = [
                agent_bin,
                "--allow-all",
                "--agent",
                self.workflow.get_agent_name(),
            ]
            mcp_config = self.workflow.get_mcp_config_path()
            if mcp_config and mcp_config.exists():
                cmd += ["--additional-mcp-config", f"@{mcp_config}"]
            cmd += ["-p", f"Follow {case_dir}/instructions/INSTRUCTIONS.md"]
            return cmd
        else:
            return [
                agent_bin,
                "chat",
                "--agent",
                self.workflow.get_agent_name(),
                "--no-interactive",
                "--require-mcp-startup",
                f"Follow {case_dir}/instructions/INSTRUCTIONS.md",
            ]

    @staticmethod
    def _read_prd(case_dir: Path) -> dict | None:
        """Read and parse prd.json from the work directory."""
        prd_file = case_dir / "prd.json"
        if not prd_file.exists():
            return None
        try:
            with open(prd_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read prd.json: %s", exc)
            return None
