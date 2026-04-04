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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

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
# Progress
# ---------------------------------------------------------------------------


@dataclass
class Progress:
    """Tracks execution state for a single workflow step.

    The agent writes to ``progress.json`` updating these fields as it works.
    The runner back-fills ``log_file_name`` after each iteration.
    """

    story: str                      # User story code, e.g. "US-001"
    story_title: str                # Human-readable title
    success: bool = False
    notes: str = ""                 # Multi-line markdown written by the agent
    started: Optional[str] = None   # ISO 8601 datetime set by the agent
    completed: Optional[str] = None # ISO 8601 datetime set by the agent
    log_file_name: str = ""         # e.g. "001_20260404T094100.log"; set by runner


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

    def get_prd(self) -> dict:
        """Return the PRD dict to seed ``prd.json`` in each work dir.

        Read-only reference for the agent — completion state lives in
        ``progress.json``, not here.
        Built dynamically from ``self.steps`` — no static JSON file required.
        """
        return {
            "project": "Jawafdehi",
            "description": f"Agentic Workflow Plan: {self.display_name}",
            "userStories": [asdict(step) for step in self.steps],
        }

    def get_progress_json_template(self) -> dict:
        """Return the initial ``progress.json`` schema for a new run.

        ``progress`` is an **append-only log** — each agent invocation adds
        one entry for the story it worked on.  The runner is the sole writer.
        """
        return {
            "is_complete": False,
            "failed": False,
            "progress": [],
        }

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
        - Writes ``prd.json`` (read-only spec for the agent)
        - Writes ``progress.json`` (agent updates this to track completion)
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

        # Static PRD spec (agent reads, never writes)
        with open(case_dir / "prd.json", "w") as f:
            json.dump(self.get_prd(), f, indent=2)

        # Progress tracking (agent writes, runner reads)
        with open(case_dir / "progress.json", "w") as f:
            json.dump(self.get_progress_json_template(), f, indent=2)

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
        Main execution loop — two phases per iteration:

        **Phase 1** ``_run_agent``: invoke the agent CLI and capture its output.
        The agent is forbidden from writing to ``prd.json`` or ``progress.json``;
        it communicates outcomes exclusively through stdout markers.

        **Phase 2** ``_review_and_update_progress``: the runner reads the agent's
        stdout, writes the iteration log, and is the sole writer of
        ``progress.json``.

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
                # Check progress.json before each iteration (updated by previous Phase 2)
                progress_data = self._read_progress(case_dir)
                if progress_data and progress_data.get("is_complete", False):
                    if progress_data.get("failed", False):
                        run.mark_failed(
                            error_message="Workflow marked as failed in progress.json",
                            case_data=progress_data,
                        )
                        logger.warning("Workflow %s failed (progress.json flag)", run.case_id)
                    else:
                        run.mark_complete(case_data=progress_data)
                        logger.info("Workflow %s completed successfully", run.case_id)
                    return

                iteration_count += 1
                logger.info(
                    "Iteration %d/%d | case %s",
                    iteration_count,
                    max_iterations,
                    run.case_id,
                )

                cmd = self._build_command(agent_bin, runner, case_dir)

                # ── Phase 1: run the agent (reads prd.json + progress.json itself) ─
                try:
                    result = self._run_agent(cmd)
                except KeyboardInterrupt:
                    logger.warning("Workflow interrupted by user")
                    run.mark_failed(error_message="Interrupted by user")
                    return

                if result.returncode == 130:
                    logger.warning("Workflow interrupted (exit 130)")
                    run.mark_failed(error_message="Interrupted (exit 130)")
                    return

                # ── Phase 2: review stdout and append to progress.json ──────
                self._review_and_update_progress(case_dir, result, iteration_count)

                if result.returncode != 0:
                    retry_count += 1
                    if retry_count > 3:
                        msg = f"{runner} CLI failed {retry_count} times consecutively"
                        logger.error(msg)
                        run.mark_failed(error_message=msg)
                        return

                    logger.warning(
                        "%s CLI exited %d — retry %d/3 in 10s",
                        runner,
                        result.returncode,
                        retry_count,
                    )
                    time.sleep(10)
                    continue

                retry_count = 0
                time.sleep(2)

            # Exhausted iterations
            progress_data = self._read_progress(case_dir) or {}
            run.mark_failed(
                error_message=f"Reached max iterations ({max_iterations})",
                case_data=progress_data,
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
    def _run_agent(cmd: list[str]) -> subprocess.CompletedProcess:
        """Phase 1 — execute the agent CLI and capture its output.

        The agent must NOT write to ``prd.json`` or ``progress.json``.
        All progress is communicated through stdout markers (see
        ``_parse_progress_from_stdout``).
        """
        return subprocess.run(cmd, capture_output=True, text=True)

    def _review_and_update_progress(
        self,
        case_dir: Path,
        result: subprocess.CompletedProcess,
        iteration: int,
    ) -> None:
        """Phase 2 — sole writer of ``progress.json``.

        1. Writes the iteration log to ``logs/``.
        2. Parses stdout for a ``WORKFLOW_PROGRESS`` marker emitted by the agent.
           The agent is responsible for reading ``prd.json`` and ``progress.json``
           to decide which story it worked on; the runner does not impose this.
        3. **Appends** the new ``Progress`` entry to the log if a marker was found.
           If the agent emits no marker, logs a warning and skips appending.
        4. Infers ``is_complete`` when every step id has a ``success: true``
           entry anywhere in the log.
        5. Checks for ``WORKFLOW_FAILED`` to short-circuit the loop.
        """
        log_filename = self._write_iteration_log(
            case_dir, iteration, result.stdout, result.stderr
        )

        data = self._read_progress(case_dir)
        if not data:
            logger.warning("progress.json missing — cannot apply updates")
            return

        # Parse the single WORKFLOW_PROGRESS marker from stdout
        updates = self._parse_progress_from_stdout(result.stdout)
        if not updates:
            logger.warning(
                "Iteration %d: no WORKFLOW_PROGRESS marker in stdout — nothing appended",
                iteration,
            )
        else:
            raw = updates[0]  # agent works on exactly one story per run
            new_entry = asdict(
                Progress(
                    story=raw.get("story", ""),
                    story_title=raw.get("story_title", ""),
                    success=bool(raw.get("success", False)),
                    notes=raw.get("notes", ""),
                    started=raw.get("started"),
                    completed=raw.get("completed"),
                    log_file_name=log_filename,
                )
            )
            data["progress"].append(new_entry)

        # Check for workflow failure signal
        failure_reason = self._parse_failure_from_stdout(result.stdout)
        if failure_reason:
            data["failed"] = True
            data["is_complete"] = True
            logger.warning("Agent signalled workflow failure: %s", failure_reason)

        # Infer completion when every defined step has a success=true entry
        if not data.get("is_complete"):
            succeeded = {e["story"] for e in data["progress"] if e.get("success")}
            if all(step.id in succeeded for step in self.steps):
                data["is_complete"] = True

        try:
            with open(case_dir / "progress.json", "w") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            logger.warning("Could not write progress.json: %s", exc)

    @staticmethod
    def _parse_progress_from_stdout(stdout: str) -> list[dict]:
        """Scan stdout for ``WORKFLOW_PROGRESS: <json>`` lines.

        The agent must emit one such line per completed step, e.g.::

            WORKFLOW_PROGRESS: {"story": "US-001", "success": true,
                                "notes": "Done.", "started": "...",
                                "completed": "..."}
        """
        updates = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("WORKFLOW_PROGRESS:"):
                payload = stripped[len("WORKFLOW_PROGRESS:"):].strip()
                try:
                    updates.append(json.loads(payload))
                except json.JSONDecodeError:
                    logger.warning("Malformed WORKFLOW_PROGRESS line: %s", stripped)
        return updates

    @staticmethod
    def _parse_failure_from_stdout(stdout: str) -> str | None:
        """Scan stdout for a ``WORKFLOW_FAILED: <reason>`` line.

        The agent emits this to signal an unrecoverable failure, e.g.::

            WORKFLOW_FAILED: Could not download required source documents.
        """
        for line in stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("WORKFLOW_FAILED:"):
                return stripped[len("WORKFLOW_FAILED:"):].strip()
        return None

    @staticmethod
    def _read_progress(case_dir: Path) -> dict | None:
        """Read and parse ``progress.json`` from the work directory."""
        progress_file = case_dir / "progress.json"
        if not progress_file.exists():
            return None
        try:
            with open(progress_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read progress.json: %s", exc)
            return None

    @staticmethod
    def _write_iteration_log(
        case_dir: Path,
        iteration: int,
        stdout: str,
        stderr: str,
    ) -> str:
        """Write captured agent output to ``logs/<n>_<timestamp>.log``.

        Returns the bare filename so it can be stored in ``progress.json`` entries.
        """
        logs_dir = case_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
        log_filename = f"{iteration:03d}_{timestamp}.log"

        parts = []
        if stdout:
            parts.append(stdout)
        if stderr:
            parts.append("--- STDERR ---\n" + stderr)

        (logs_dir / log_filename).write_text("\n".join(parts))
        logger.debug("Iteration log written: %s", log_filename)
        return log_filename
