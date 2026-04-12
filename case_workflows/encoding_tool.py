"""
Encoding repair tool for workflow agents.

Provides a tool that allows LLM agents to validate and repair invalid UTF-8
encoding in markdown and text files during workflow execution.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def fix_file_encoding(file_path: str, encoding: str = "utf-8") -> dict[str, Any]:
    """Validate and repair invalid encoding in a text file.

    This tool is callable by workflow agents to fix encoding problems in files
    (especially markdown sources and draft.md). It will:

    1. Attempt to read the file with the specified encoding.
    2. If invalid bytes are found, recover content using error='replace'.
    3. Rewrite the file with valid encoding.
    4. Return a summary of what was fixed.

    Args:
        file_path:  Absolute or case-relative path to the file to fix.
        encoding:   Encoding to validate/repair (default: utf-8).

    Returns:
        A dict with keys:
        - status: "ok" (no issues) or "repaired" (invalid bytes fixed) or "error"
        - file_path: The absolute path that was checked
        - encoding: The encoding that was validated
        - details: Human-readable summary of what happened (if any issues)
        - bytes_invalid: Number of invalid bytes encountered (0 if ok)
    """
    try:
        file_p = Path(file_path)
        if not file_p.is_absolute():
            # If relative, assume it's relative to cwd; resolve to absolute
            file_p = file_p.resolve()

        if not file_p.exists():
            return {
                "status": "error",
                "file_path": str(file_p),
                "encoding": encoding,
                "details": f"File does not exist: {file_p}",
                "bytes_invalid": 0,
            }

        try:
            # Try strict read first
            content = file_p.read_text(encoding=encoding)
            return {
                "status": "ok",
                "file_path": str(file_p),
                "encoding": encoding,
                "details": f"File is valid {encoding}",
                "bytes_invalid": 0,
            }
        except UnicodeDecodeError as exc:
            # Record the position of the first invalid byte
            first_bad_byte = exc.start

            # Recover with replacement
            recovered = file_p.read_text(encoding=encoding, errors="replace")

            # Rewrite with valid encoding
            file_p.write_text(recovered, encoding=encoding)

            logger.info(
                "Fixed invalid %s in %s at byte %s",
                encoding,
                file_p,
                first_bad_byte,
            )

            # Count how many replacement characters were inserted
            num_invalid = recovered.count("\ufffd")

            return {
                "status": "repaired",
                "file_path": str(file_p),
                "encoding": encoding,
                "details": f"Repaired {encoding} encoding errors starting at byte {first_bad_byte}",
                "bytes_invalid": num_invalid,
            }

    except Exception as exc:
        logger.exception("Error fixing encoding in %s", file_path)
        return {
            "status": "error",
            "file_path": str(file_path),
            "encoding": encoding,
            "details": f"Error: {exc}",
            "bytes_invalid": 0,
        }


# Define the tool for deepagents/LangChain integration
TOOL_NAME = "fix_file_encoding"
TOOL_DESCRIPTION = (
    "Validate and repair invalid UTF-8 encoding in text files. "
    "Useful for fixing corrupted markdown sources before processing. "
    "Returns a status report with byte count of invalid characters found."
)


def create_fix_encoding_tool():
    """Create a LangChain-compatible tool for fixing file encoding."""
    from langchain_core.tools import tool

    @tool(description=TOOL_DESCRIPTION)
    def fix_encoding(
        file_path: str,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Validate and repair file encoding.

        Args:
            file_path: Path to the text file to validate/repair.
            encoding: Text encoding (default: utf-8).

        Returns:
            Status report: {status, file_path, encoding, details, bytes_invalid}
        """
        return fix_file_encoding(file_path, encoding)

    return fix_encoding
