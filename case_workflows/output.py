"""
Rich-based output formatting for workflow runs.

``WorkflowPrinter`` owns all terminal output for a workflow execution:
- Structured banners / panels / rules via Rich
- Agent event streaming (tool calls, model thinking)
- A logging handler that routes all ``case_workflows.*`` log records —
  including exceptions with full tracebacks — through the same Rich console
  so they never interleave with structured output.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.rule import Rule
from rich.table import Table

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Colour / style constants — keep them in one place so they're easy to tweak.
_TOOL_COLOR = "cyan"
_STEP_COLOR = "bold blue"
_OK_COLOR = "green"
_SKIP_COLOR = "dim"
_WARN_COLOR = "yellow"
_ERR_COLOR = "red"


def _format_duration(seconds: float) -> str:
    """Return a compact human-readable duration string."""
    total = max(0, int(round(seconds)))
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}h {mins}m {secs}s"
    if mins:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def _compress_paths(text: str, work_dir: Optional[str]) -> str:
    """Replace the work-dir absolute prefix with '…/' for brevity."""
    if not work_dir:
        return text
    # Normalise trailing slash for safe substitution
    prefix = work_dir.rstrip("/") + "/"
    return text.replace(prefix, ".../")


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _TeeConsole:
    """
    Thin proxy that forwards every ``print`` / ``print_exception`` call to
    both a terminal ``Console`` and a plain-text file ``Console``.

    Used by ``WorkflowPrinter.enable_file_logging`` so that all output is
    mirrored to disk without touching individual call-sites.
    """

    def __init__(self, terminal: Console, file: Console) -> None:
        self._terminal = terminal
        self._file = file

    def print(self, *args, **kwargs) -> None:  # noqa: A003
        self._terminal.print(*args, **kwargs)
        self._file.print(*args, **kwargs)

    def print_exception(self, **kwargs) -> None:
        self._terminal.print_exception(**kwargs)
        self._file.print_exception(**kwargs)

    def __getattr__(self, name: str):
        # Fall through to the terminal console for any attribute not defined
        # above (e.g. ``highlight``, ``width``, internal Rich state).
        return getattr(self._terminal, name)


# ---------------------------------------------------------------------------
# WorkflowPrinter
# ---------------------------------------------------------------------------


class WorkflowPrinter:
    """
    Single rich console for all workflow terminal output.

    Create one instance per ``handle()`` invocation and pass it through to
    ``Workflow.execute()``.
    """

    def __init__(self) -> None:
        self._console = Console(highlight=False)
        self._err_console = Console(highlight=False, stderr=True)
        self._work_dir: Optional[str] = None  # set in print_case_header
        # Tracks whether the model is currently mid-stream so we avoid
        # printing duplicate "thinking…" lines for back-to-back start events.
        self._model_active: bool = False
        self._streamed_content: bool = False  # did we output any streaming text?
        self._tool_state: dict = {}  # Store metadata across tool start/end events

    def _with_ts(self, text: str) -> str:
        return f"[dim]{_utc_timestamp()}[/dim] {text}"

    def enable_file_logging(self, path: Path) -> None:
        """
        Mirror all subsequent console output to a plain-text log file.

        Wraps ``_console`` and ``_err_console`` with :class:`_TeeConsole` so
        that every ``print`` call goes to both the terminal and *path*.
        Any :class:`_WorkflowRichHandler` that was already installed via
        :meth:`install_logging_handler` is updated in-place so that log
        records are also captured.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        self._log_fh = open(path, "w", encoding="utf-8")  # noqa: SIM115
        file_console = Console(
            file=self._log_fh,
            force_terminal=False,
            no_color=True,
            highlight=False,
            width=200,
        )
        self._console = _TeeConsole(self._console, file_console)
        self._err_console = _TeeConsole(self._err_console, file_console)
        # Patch already-installed logging handlers so their log records tee too.
        for handler in logging.getLogger("case_workflows").handlers:
            if isinstance(handler, _WorkflowRichHandler):
                handler._console = self._console
                handler._err_console = self._err_console

    # ------------------------------------------------------------------
    # Structured output helpers
    # ------------------------------------------------------------------

    def print_workflow_header(
        self,
        display_name: str,
        workflow_id: str,
        model: str,
        base_url: Optional[str] = None,
    ) -> None:
        self._console.print()
        self._console.print(
            self._with_ts(
                f"[bold]Workflow:[/bold] {display_name} [dim]({workflow_id})[/dim]"
            )
        )
        self._console.print(self._with_ts(f"[bold]Model:   [/bold] {model}"))
        if base_url:
            self._console.print(self._with_ts(f"[bold]Base URL:[/bold] {base_url}"))

    def print_case_header(self, case_id: str, created: bool) -> None:
        status = (
            "[green]✦ New run[/green]" if created else "[yellow]♻ Resuming[/yellow]"
        )
        self._console.print()
        self._console.print(self._with_ts(f"[bold]Case:[/bold] {case_id} {status}"))

    def print_work_dir(self, work_dir: str) -> None:
        self._work_dir = work_dir
        # Show a relative-ish path: strip the cwd prefix if possible
        try:
            rel = Path(work_dir).relative_to(Path.cwd())
            display = str(rel)
        except ValueError:
            display = work_dir
        self._console.print(self._with_ts(f"[dim]📁 {display}[/dim]"))

    def print_mcp_info(self, servers: list[str]) -> None:
        self._console.print(self._with_ts(f"[dim]🔗 MCP: {', '.join(servers)}[/dim]"))

    def print_tracing_info(self, provider: str) -> None:
        self._console.print(self._with_ts(f"[dim]📡 {provider} tracing enabled[/dim]"))

    def print_step_header(self, name: str, index: int, total: int) -> None:
        self._console.print()
        self._console.print(
            self._with_ts(
                f"[{_STEP_COLOR}]Step {index}/{total}: {name}[/{_STEP_COLOR}]"
            )
        )

    def print_step_done(
        self, name: str, elapsed_seconds: Optional[float] = None
    ) -> None:
        if elapsed_seconds is None:
            self._console.print(self._with_ts(f"[{_OK_COLOR}]✓ {name}[/{_OK_COLOR}]"))
            return
        duration = _format_duration(elapsed_seconds)
        self._console.print(
            self._with_ts(
                f"[{_OK_COLOR}]✓ {name} [dim]({duration})[/dim][/{_OK_COLOR}]"
            )
        )

    def print_step_skipped(self, name: str) -> None:
        self._console.print(
            self._with_ts(f"[{_SKIP_COLOR}]⏭ {name} — already complete[/{_SKIP_COLOR}]")
        )

    def print_summary(
        self, total: int, succeeded: int, skipped: int, failed: int
    ) -> None:
        self._console.print()
        self._console.print(Rule("[bold]Summary[/bold]", style="dim"))
        table = Table(box=None, pad_edge=False, show_header=True, header_style="bold")
        table.add_column("Processed", justify="center")
        table.add_column("Succeeded", justify="center", style=_OK_COLOR)
        table.add_column("Skipped", justify="center", style=_SKIP_COLOR)
        table.add_column(
            "Failed", justify="center", style=_ERR_COLOR if failed else _SKIP_COLOR
        )
        table.add_row(str(total), str(succeeded), str(skipped), str(failed))
        self._console.print(table)
        self._console.print()

    def print_usage_summary(self, input_tokens: int, output_tokens: int) -> None:
        self._console.print()
        self._console.print(self._with_ts("[bold]Token Usage[/bold]"))
        total = input_tokens + output_tokens
        if total == 0:
            self._console.print(
                f"  [{_SKIP_COLOR}]No usage data available (model did not report tokens)[/{_SKIP_COLOR}]"
            )
        else:
            table = Table(
                box=None, pad_edge=False, show_header=True, header_style="bold"
            )
            table.add_column("Input Tokens", justify="right")
            table.add_column("Output Tokens", justify="right")
            table.add_column("Total Tokens", justify="right", style="bold")
            table.add_row(
                f"{input_tokens:,}",
                f"{output_tokens:,}",
                f"{total:,}",
            )
            self._console.print(table)
        self._console.print()

    def error(self, msg: str) -> None:
        self._err_console.print(self._with_ts(f"[{_ERR_COLOR}]✗ {msg}[/{_ERR_COLOR}]"))

    def warn(self, msg: str) -> None:
        self._console.print(self._with_ts(f"[{_WARN_COLOR}]⚠ {msg}[/{_WARN_COLOR}]"))

    # ------------------------------------------------------------------
    # Agent event streaming
    # ------------------------------------------------------------------

    def handle_agent_event(self, event: dict) -> None:
        """Drop-in replacement for the old ``_print_agent_event`` function."""
        kind = event.get("event", "")
        name = event.get("name", "")

        if kind == "on_chat_model_start":
            if not self._model_active:
                self._console.print(
                    self._with_ts("[dim italic]🤔 thinking…[/dim italic]")
                )
                self._model_active = True
                self._streamed_content = False

        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            self._console.print(part["text"], end="")
                            self._streamed_content = True
                elif isinstance(content, str):
                    self._console.print(content, end="")
                    self._streamed_content = True

        elif kind == "on_chat_model_end":
            self._model_active = False
            if self._streamed_content:
                self._console.print()
                self._streamed_content = False

        elif kind == "on_tool_start":
            inputs = event.get("data", {}).get("input", {})

            # Tool-specific compact formatters
            if name == "read_file":
                file_path = inputs.get("file_path", "")
                file_path = _compress_paths(file_path, self._work_dir)
                offset = inputs.get("startLine", "")
                limit = inputs.get("endLine", "")
                params = f"[{offset}–{limit}]" if offset and limit else ""
                self._console.print(
                    self._with_ts(
                        f"🔍 [bold {_TOOL_COLOR}]read_file[/bold {_TOOL_COLOR}] {file_path} {params}".strip()
                    )
                )
                return

            elif name == "grep":
                pattern = inputs.get("query", "")
                path = inputs.get("includePattern", inputs.get("path", ""))
                path = _compress_paths(path, self._work_dir) if path else ""
                self._console.print(
                    self._with_ts(
                        f"🔎 [bold {_TOOL_COLOR}]grep[/bold {_TOOL_COLOR}] pattern='{_truncate(pattern, 50)}' {path}".strip()
                    )
                )
                return

            elif name == "ls":
                path = inputs.get("path", "")
                path = _compress_paths(path, self._work_dir)
                self._console.print(
                    self._with_ts(
                        f"📂 [bold {_TOOL_COLOR}]ls[/bold {_TOOL_COLOR}] {path}"
                    )
                )
                return

            elif name == "write_file":
                # For write_file, capture content metadata for later display
                file_path = inputs.get("filePath", "")
                content = inputs.get("content", "")
                char_count = len(content)
                self._tool_state["write_file"] = {
                    "file_path": file_path,
                    "char_count": char_count,
                }
                file_path = _compress_paths(file_path, self._work_dir)
                self._console.print(
                    self._with_ts(
                        f"✏️ [bold {_TOOL_COLOR}]write_file[/bold {_TOOL_COLOR}] {file_path}"
                    )
                )
                return

            elif name == "write_todos":
                # write_todos start is minimal; details in on_tool_end
                self._console.print(
                    self._with_ts(
                        f"📋 [bold {_TOOL_COLOR}]write_todos[/bold {_TOOL_COLOR}]"
                    )
                )
                return

            # Default tool start handler for all other tools
            raw = str(inputs)
            raw = _compress_paths(raw, self._work_dir)
            raw = _truncate(raw, 200)
            self._console.print(
                self._with_ts(f"🔧 [bold {_TOOL_COLOR}]{name}[/bold {_TOOL_COLOR}]")
            )
            self._console.print(self._with_ts(f"[dim]↳ {raw}[/dim]"))

        elif kind == "on_tool_end":
            output = event.get("data", {}).get("output", "")

            # Tool-specific compact formatters for output
            if name == "read_file":
                # Show errors, skip success output
                output_str = str(output)
                if "error" in output_str.lower() or "cannot" in output_str.lower():
                    output_str = _compress_paths(output_str, self._work_dir)
                    self._console.print(
                        self._with_ts(f"[red]  {_truncate(output_str, 220)}[/red]")
                    )
                return

            elif name == "grep":
                # Show errors, skip success output
                output_str = str(output)
                if "error" in output_str.lower() or "no matches" in output_str.lower():
                    output_str = _compress_paths(output_str, self._work_dir)
                    self._console.print(
                        self._with_ts(f"[red]  {_truncate(output_str, 220)}[/red]")
                    )
                return

            elif name == "ls":
                # Show errors inline on one line, skip success output
                output_str = str(output)
                if "error" in output_str.lower() or "cannot" in output_str.lower():
                    output_str = _compress_paths(output_str, self._work_dir)
                    self._console.print(
                        self._with_ts(f"[red]❌ {_truncate(output_str, 220)}[/red]")
                    )
                return

            elif name == "write_file":
                # Display: file name, character count, and summary
                raw = str(output)
                raw = _compress_paths(raw, self._work_dir)
                summary = "updated"
                is_error = False

                # Determine outcome from output
                if "Updated file" in raw:
                    summary = "✓ updated"
                elif "Cannot write" in raw or "error" in raw.lower():
                    summary = "✗ error"
                    is_error = True

                # Get stored metadata
                write_file_state = self._tool_state.get("write_file", {})
                char_count = write_file_state.get("char_count", 0)
                file_path = write_file_state.get("file_path", "")
                file_path = _compress_paths(file_path, self._work_dir)

                # Show success compactly, errors with detail
                if is_error:
                    self._console.print(self._with_ts(f"✏️ {summary} {file_path}"))
                    self._console.print(
                        self._with_ts(f"[red]  {_truncate(raw, 220)}[/red]")
                    )
                else:
                    if char_count > 0:
                        self._console.print(
                            self._with_ts(
                                f"✏️ {summary} {file_path} ({char_count} chars)"
                            )
                        )
                    else:
                        self._console.print(self._with_ts(f"✏️ {summary} {file_path}"))

                # Clean up state
                self._tool_state.pop("write_file", None)
                return

            elif name == "write_todos":
                # Display todos line-by-line
                raw = str(output)
                # Parse JSON if the output is a task JSON, otherwise show as-is
                try:
                    # Try to parse as JSON first
                    if raw.startswith("{") or raw.startswith("["):
                        data = json.loads(raw)
                        if isinstance(data, dict) and "todos" in data:
                            todos = data["todos"]
                            if isinstance(todos, list):
                                for todo in todos:
                                    if isinstance(todo, dict):
                                        status = todo.get("status", "").upper()
                                        content = todo.get("content", "")
                                        self._console.print(
                                            self._with_ts(f"  • [{status}] {content}")
                                        )
                                    else:
                                        self._console.print(
                                            self._with_ts(f"  • {todo}")
                                        )
                                return
                except Exception:
                    pass
                # Fallback: just show the raw output
                self._console.print(
                    self._with_ts(f"[dim]↳ {_truncate(raw, 220)}[/dim]")
                )
                return

            # Default tool end handler for all other tools
            raw = str(output)
            raw = _compress_paths(raw, self._work_dir)
            raw = _truncate(raw, 220)
            self._console.print(self._with_ts(f"[dim]↳ {raw}[/dim]"))

    # ------------------------------------------------------------------
    # Logging integration
    # ------------------------------------------------------------------

    def install_logging_handler(self) -> None:
        """
        Route all ``case_workflows.*`` log records through this Rich console.

        - Sets ``propagate=False`` on the ``case_workflows`` logger so records
          don't also go to the root handler.
        - Also sets the root logger to INFO (with a minimal handler) so
          third-party libraries (LangChain, uvicorn, etc.) are not silenced.
        """
        handler = _WorkflowRichHandler(self._console, self._err_console)
        handler.setLevel(logging.DEBUG)

        wf_logger = logging.getLogger("case_workflows")
        wf_logger.setLevel(logging.DEBUG)
        wf_logger.handlers.clear()
        wf_logger.addHandler(handler)
        wf_logger.propagate = False

        # Ensure the root logger is at INFO so other libs emit their messages
        # through whatever handler Django/basicConfig set up.
        root = logging.getLogger()
        if not root.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s %(name)s %(levelname)s %(message)s",
                datefmt="%H:%M:%S",
            )
        else:
            root.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Custom RichHandler
# ---------------------------------------------------------------------------


class _WorkflowRichHandler(logging.Handler):
    """
    Compact Rich logging handler for ``case_workflows.*`` records.

    Levels:
    - DEBUG / INFO  → dim
    - WARNING       → yellow
    - ERROR         → red
    - CRITICAL      → bold red
    Exception records print a Rich traceback via ``console.print_exception()``.
    """

    _LEVEL_STYLE: dict[int, str] = {
        logging.DEBUG: "dim",
        logging.INFO: "dim",
        logging.WARNING: "yellow",
        logging.ERROR: "red",
        logging.CRITICAL: "bold red",
    }

    def __init__(self, console: Console, err_console: Console) -> None:
        super().__init__()
        self._console = console
        self._err_console = err_console

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Strip the default timestamp/level/name prefix that formatters add —
            # we only want the raw message since Rich gives us context already.
            # (We set no formatter, so msg == record.getMessage().)
            style = self._LEVEL_STYLE.get(record.levelno, "")
            short_name = record.name.removeprefix("case_workflows.")
            level_tag = record.levelname[0]  # D / I / W / E / C
            is_err = record.levelno >= logging.ERROR
            target = self._err_console if is_err else self._console
            ts = _utc_timestamp()

            if style:
                target.print(
                    f"[dim]{ts}[/dim] [dim]{level_tag}[/dim] [{style}][dim]{short_name}[/dim] {msg}[/{style}]"
                )
            else:
                target.print(
                    f"[dim]{ts}[/dim] {level_tag} [dim]{short_name}[/dim] {msg}"
                )

            if record.exc_info:
                target.print_exception(show_locals=False)
        except Exception:  # noqa: BLE001
            self.handleError(record)
