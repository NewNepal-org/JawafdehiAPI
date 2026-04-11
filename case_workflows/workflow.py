"""
Workflow ABC — defines the contract for all case workflow templates,
and owns the execution logic.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional

from asgiref.sync import sync_to_async
from django.conf import settings

from case_workflows.output import WorkflowPrinter
from case_workflows.storage_utils import (
    download_workflow_outputs,
    upload_workflow_outputs,
)

if TYPE_CHECKING:
    from case_workflows.models import CaseWorkflowRun

logger = logging.getLogger(__name__)


def _patch_gemini_null_properties() -> None:
    """
    Patch langchain_google_genai to handle tool schemas that Gemini rejects.

    Root cause: Gemini requires ``type`` to be explicitly ``"object"`` whenever
    ``properties`` is present.  Valid JSON Schema omits ``type`` when it is
    implied (e.g. Pydantic v2 model schemas, dereferenced ``$ref`` objects), but
    Gemini's strict validation rejects that.

    Two patches are applied:

    1. **``_format_json_schema_to_gapic``** — this is the function inside
       ``langchain_google_genai._function_utils`` that converts raw JSON Schema
       into the intermediate ``formatted_schema`` dict that
       ``_dict_to_genai_schema`` then reads.  After conversion, if the result
       has ``properties`` but no ``type`` (and no ``anyOf``), we add
       ``"type": "object"``.  Because the function recurses via LOAD_GLOBAL,
       this fix also covers every nested schema produced by its own recursion
       (including ``$ref``-expanded sub-schemas).

    2. **``_dict_to_genai_schema``** — kept for the original null-property
       fix: property slots whose schema converts to ``None`` crash pydantic;
       return an empty ``Schema()`` instead.
    """
    try:
        import langchain_google_genai._function_utils as _fu
        from google.genai import types as _genai_types

        # --- patch 1: _format_json_schema_to_gapic ---
        _orig_format = _fu._format_json_schema_to_gapic

        def _patched_format(schema: Any) -> Any:
            result = _orig_format(schema)
            if not isinstance(result, dict):
                return result

            # Pydantic v2 sometimes emits schemas with BOTH "properties" AND
            # "anyOf" where anyOf items are pure required-constraint dicts:
            #   anyOf: [{"required": ["x"]}, {"required": ["y"]}]
            # These carry no type information and Gemini rejects them with:
            #   "parameters.any_of[N].required: only allowed for OBJECT type"
            # Additionally, when anyOf is present alongside properties,
            # _dict_to_genai_schema intentionally drops "type" (per its comment
            # "when any_of is used, it must be the only field set"), so the
            # resulting Schema has properties but no type — also rejected by Gemini.
            #
            # Fix: remove anyOf items that are ONLY a required-constraint (no
            # type, no properties, no anyOf of their own).  If all items are
            # stripped, delete the anyOf key entirely so that _dict_to_genai_schema
            # will correctly set type=OBJECT for the parent schema.
            if "anyOf" in result:
                kept = [
                    item
                    for item in result["anyOf"]
                    if not (
                        isinstance(item, dict)
                        and "required" in item
                        and "type" not in item
                        and "properties" not in item
                        and "anyOf" not in item
                    )
                ]
                if kept:
                    result["anyOf"] = kept
                else:
                    del result["anyOf"]

            # After the cleanup above, if properties are present but type is
            # absent (and no anyOf remains), add the explicit "object" type that
            # Gemini requires.
            if (
                "properties" in result
                and "type" not in result
                and "anyOf" not in result
            ):
                result["type"] = "object"

            return result

        _fu._format_json_schema_to_gapic = _patched_format

        # --- patch 2: _dict_to_genai_schema (null-property fix) ---
        _orig_dict = _fu._dict_to_genai_schema

        def _patched_dict(
            schema, is_property: bool = False, is_any_of_item: bool = False
        ):
            result = _orig_dict(
                schema, is_property=is_property, is_any_of_item=is_any_of_item
            )
            if result is None and is_property:
                return _genai_types.Schema()
            return result

        _fu._dict_to_genai_schema = _patched_dict

    except ImportError:
        pass  # langchain_google_genai not installed; skip


_patch_gemini_null_properties()


def _patch_unicode_file_editing() -> None:
    """
    Patch deepagents ``perform_string_replacement`` to handle Unicode normalisation.

    Root cause: The agent (LLM) generates Devanagari text in NFD normalisation
    while files on disk are stored in NFC (or vice-versa).  The two forms look
    identical but differ at the byte level, so the bare ``content.count(old_string)``
    inside ``perform_string_replacement`` reports 0 occurrences and the edit fails
    with "String not found in file".

    Fix: normalise both the file content AND the search string to NFC before
    comparing and replacing.  NFC is a canonical normalisation so the resulting
    file content is semantically identical.
    """
    try:
        import unicodedata

        import deepagents.backends.utils as _dbu

        _orig_replace = _dbu.perform_string_replacement

        def _nfc_replace(
            content: str,
            old_string: str,
            new_string: str,
            replace_all: bool = False,
        ):
            # Normalise all three strings to NFC so that visually identical
            # Devanagari (and other Unicode) text matches regardless of how it
            # was generated or stored.
            content_nfc = unicodedata.normalize("NFC", content)
            old_nfc = unicodedata.normalize("NFC", old_string)
            new_nfc = unicodedata.normalize("NFC", new_string)
            return _orig_replace(content_nfc, old_nfc, new_nfc, replace_all)

        _dbu.perform_string_replacement = _nfc_replace

        # The filesystem backend imports perform_string_replacement at call-time
        # via module reference, but patch it there too just in case it was
        # imported directly.
        try:
            import deepagents.backends.filesystem as _dbf

            if hasattr(_dbf, "perform_string_replacement"):
                _dbf.perform_string_replacement = _nfc_replace
        except ImportError:
            pass

    except ImportError:
        pass  # deepagents not installed; skip


_patch_unicode_file_editing()


# ---------------------------------------------------------------------------
# WorkflowStep
# ---------------------------------------------------------------------------


@dataclass
class WorkflowStep:
    """A single step within a workflow template."""

    name: str
    prompt_fn: Callable[[Path], str]
    skills: List[str] = field(default_factory=list)
    tools: List[Any] = field(default_factory=list)
    mcp_servers: dict[str, dict] = field(default_factory=dict)
    mcp_tool_filter: Optional[List[str]] = None
    subagents: List[dict] = field(default_factory=list)
    system_prompt: Optional[str] = None


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
        work_dir = workflow.setup_work_dir(run)
        workflow.execute(run, model="openai:gpt-4o")
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
        """
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

    def on_work_dir_created(self, case_dir: Path) -> None:
        """
        Called after the base work directory is created.

        Override to add template-specific directory structure or files.
        Default is a no-op.
        """

    def on_initialize(self) -> None:
        """
        Called once before execution begins.

        Override to perform any one-time setup. Default is a no-op.
        """

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
        Create the work directory for a run and populate it.

        - If the directory already exists, logs a warning and deletes it
        - Downloads any previously uploaded files tracked in ``run.case_data``
        - Calls ``on_work_dir_created(case_dir)`` for template-specific setup
        - Initialises ``run.case_data`` if empty

        Persists ``run.work_dir`` and returns the directory path.
        """
        import shutil

        case_dir = self.get_work_dir(run)

        if case_dir.is_dir():
            logger.warning(
                "Work directory already exists — deleting and recreating: %s", case_dir
            )
            shutil.rmtree(case_dir)

        case_dir.mkdir(parents=True, exist_ok=True)

        # Initialise state in case_data if this is a fresh run
        if not run.case_data:
            run.case_data = {"is_complete": False, "steps": {}, "files": {}}

        # Download existing tracked files if resuming a previous run
        tracked_files = run.case_data.get("files", {})
        if tracked_files:
            download_workflow_outputs(case_dir, tracked_files)

        # Template-specific extra setup
        self.on_work_dir_created(case_dir)

        run.work_dir = str(case_dir)
        run.save(update_fields=["work_dir", "case_data", "updated_at"])

        logger.info("Work directory created: %s", case_dir)
        return case_dir

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        run: CaseWorkflowRun,
        *,
        model: str = "openai:gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        verbose: bool = False,
        recursion_limit: int = 200,
        printer: Optional[WorkflowPrinter] = None,
    ) -> None:
        """
        Run all pending workflow steps in order using a deepagents agent.

        Each step builds its own agent with the step's tools, MCP servers,
        system prompt, and subagents.  The agent receives filesystem access
        to ``case_dir`` via ``FilesystemBackend``.

        Step completion is stored in ``run.case_data["steps"]`` and
        persisted to the database after every step so that interrupted
        runs can be resumed from the correct point.
        """
        asyncio.run(
            self._execute_async(
                run,
                model=model,
                api_key=api_key,
                base_url=base_url,
                verbose=verbose,
                recursion_limit=recursion_limit,
                printer=printer,
            )
        )

    async def _execute_async(
        self,
        run: CaseWorkflowRun,
        *,
        model: str,
        api_key: Optional[str],
        base_url: Optional[str],
        verbose: bool = False,
        recursion_limit: int = 200,
        printer: Optional[WorkflowPrinter] = None,
    ) -> None:
        import os

        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
        from langchain.chat_models import init_chat_model
        from langchain_core.callbacks import BaseCallbackHandler
        from langchain_mcp_adapters.client import MultiServerMCPClient

        class _UsageCallbackHandler(BaseCallbackHandler):
            """Accumulate LLM token usage across all steps."""

            def __init__(self) -> None:
                super().__init__()
                self.input_tokens: int = 0
                self.output_tokens: int = 0

            @property
            def total_tokens(self) -> int:
                return self.input_tokens + self.output_tokens

            def on_llm_end(self, response: Any, **kwargs: Any) -> None:  # type: ignore[override]
                for row in response.generations:
                    for gen in row:
                        meta = getattr(
                            getattr(gen, "message", None), "usage_metadata", None
                        )
                        if meta:
                            self.input_tokens += meta.get("input_tokens", 0)
                            self.output_tokens += meta.get("output_tokens", 0)

        case_dir = self.get_work_dir(run)
        if not case_dir.is_dir():
            raise RuntimeError(
                f"Work directory does not exist — call setup_work_dir() first: {case_dir}"
            )

        # Initialise or restore state
        state: dict = run.case_data or {}
        if "steps" not in state:
            state.update({"is_complete": False, "steps": {}, "files": {}})

        if state.get("is_complete"):
            await sync_to_async(run.mark_complete)(case_data=state)
            return

        await sync_to_async(run.mark_started)()
        self.on_initialize()

        # Build the chat model (supports any OpenAI-compatible provider)
        model_kwargs: dict[str, Any] = {}
        if api_key:
            model_kwargs["api_key"] = api_key
        if base_url:
            model_kwargs["base_url"] = base_url
        chat_model = init_chat_model(model, **model_kwargs)

        # Build Langfuse callback if credentials are present
        langfuse_callbacks: list[Any] = []
        if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get(
            "LANGFUSE_SECRET_KEY"
        ):
            import uuid

            from langfuse.langchain import CallbackHandler

            trace_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"jawafdehi/{self.workflow_id}/{run.case_id}",
            ).hex  # 32 lowercase hex chars
            langfuse_callbacks = [
                CallbackHandler(
                    trace_context={"trace_id": trace_id},
                )
            ]
            if printer:
                printer.print_tracing_info("Langfuse")
            else:
                logger.info("Langfuse tracing enabled")

        # Pre-connect all unique MCP servers once across all steps so that
        # uvx only resolves/installs each server a single time.
        all_mcp_servers: dict[str, dict] = {}
        for step in self.steps:
            all_mcp_servers.update(step.mcp_servers)

        usage_tracker = _UsageCallbackHandler()

        mcp_tools_by_server: dict[str, list[Any]] = {}
        if all_mcp_servers:
            for server_name, server_config in all_mcp_servers.items():
                client = MultiServerMCPClient({server_name: server_config})
                tools = await client.get_tools()
                for t in tools:
                    t.handle_tool_error = True
                mcp_tools_by_server[server_name] = tools
            if printer:
                printer.print_mcp_info(list(mcp_tools_by_server))
            else:
                logger.info("MCP servers connected: %s", list(mcp_tools_by_server))

        total_steps = len(self.steps)
        try:
            for idx, step in enumerate(self.steps, start=1):
                step_state = state["steps"].get(step.name, {})
                if step_state.get("status") == "complete":
                    if printer:
                        printer.print_step_skipped(step.name)
                    else:
                        logger.info("Skipping completed step: %s", step.name)
                    continue

                if printer:
                    printer.print_step_header(step.name, idx, total_steps)
                else:
                    logger.info("Running step: %s", step.name)

                # Gather pre-connected MCP tools for this step's servers
                mcp_tools: list[Any] = []
                for server_name in step.mcp_servers:
                    mcp_tools.extend(mcp_tools_by_server.get(server_name, []))
                if step.mcp_tool_filter is not None:
                    allowed = set(step.mcp_tool_filter)
                    mcp_tools = [t for t in mcp_tools if t.name in allowed]

                all_tools = mcp_tools + step.tools

                # Pass MEMORY.md as agent memory so it is injected into the
                # system prompt at startup and the agent can write back to it
                # with `edit_file` to record learnings across steps.
                memory_file = case_dir / "MEMORY.md"
                memory_paths = [str(memory_file)] if memory_file.is_file() else None

                agent = create_deep_agent(
                    model=chat_model,
                    tools=all_tools,
                    system_prompt=step.system_prompt,
                    subagents=step.subagents or None,
                    backend=FilesystemBackend(
                        root_dir=str(case_dir), virtual_mode=False
                    ),
                    memory=memory_paths,
                )

                invocation = {
                    "messages": [
                        {
                            "role": "user",
                            "content": step.prompt_fn(case_dir),
                        }
                    ]
                }
                run_config = {
                    "callbacks": langfuse_callbacks + [usage_tracker],
                    "run_name": step.name,
                    "recursion_limit": recursion_limit,
                }

                # Record step start time and persist before running
                step_started_dt = datetime.now(timezone.utc)
                step_started_at = step_started_dt.isoformat()
                state["steps"][step.name] = {
                    "status": "in_progress",
                    "started_at": step_started_at,
                }
                run.case_data = state
                await sync_to_async(run.save)(update_fields=["case_data", "updated_at"])

                if verbose:
                    async for event in agent.astream_events(
                        invocation, config=run_config, version="v2"
                    ):
                        if printer:
                            printer.handle_agent_event(event)
                else:
                    await agent.ainvoke(invocation, config=run_config)

                # Mark step complete and persist
                step_completed_dt = datetime.now(timezone.utc)
                elapsed_seconds = (step_completed_dt - step_started_dt).total_seconds()
                state["steps"][step.name] = {
                    "status": "complete",
                    "started_at": step_started_at,
                    "completed_at": step_completed_dt.isoformat(),
                    "duration_seconds": round(elapsed_seconds, 3),
                }

                previous_files = state.get("files", {})
                uploaded = self._upload_outputs(case_dir, run.case_id, previous_files)
                state.setdefault("files", {}).update(uploaded)

                run.case_data = state
                await sync_to_async(run.save)(update_fields=["case_data", "updated_at"])
                if printer:
                    printer.print_step_done(step.name, elapsed_seconds)
                else:
                    logger.info(
                        "Step completed: %s (%.2fs)", step.name, elapsed_seconds
                    )

            # All steps done
            state["is_complete"] = True
            await sync_to_async(run.mark_complete)(case_data=state)
            logger.info("Workflow completed for %s", run.case_id)

            if printer:
                printer.print_usage_summary(
                    usage_tracker.input_tokens, usage_tracker.output_tokens
                )
            else:
                logger.info(
                    "Token usage — input: %d, output: %d, total: %d",
                    usage_tracker.input_tokens,
                    usage_tracker.output_tokens,
                    usage_tracker.total_tokens,
                )

        except Exception as exc:
            await sync_to_async(run.mark_failed)(error_message=str(exc))
            logger.exception("Workflow execution error for %s", run.case_id)
            raise

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _upload_outputs(
        case_dir: Path, case_id: str, previous_files: dict[str, dict] | None = None
    ) -> dict[str, dict]:
        """Upload all non-excluded files in *case_dir* to ``default_storage``."""
        try:
            return upload_workflow_outputs(case_dir, case_id, previous_files)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to upload workflow outputs for %s: %s", case_id, exc)
            return {}
