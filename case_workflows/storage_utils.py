"""
Storage utilities for case workflow outputs.

After each workflow run, all output files (except ``prd.json`` and
``progress.json``) are uploaded to Django's ``default_storage`` backend.
This works transparently for both local ``FileSystemStorage`` (dev) and
S3/R2 (production).

Downloaded source files are tracked in ``progress.json`` under a ``"files"``
dictionary keyed by local path, with each value recording the backend storage
path, file size in bytes, and a SHA-256 hex checksum.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.files.base import File
from django.core.files.storage import default_storage

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Files that must never be uploaded — they are internal runner state.
_EXCLUDED_FILENAMES = frozenset({"prd.json", "progress.json"})

# Top-level directories that are skipped entirely — they contain template
# files re-copied fresh on every run and do not need to be persisted.
_EXCLUDED_DIRS = frozenset({"instructions", "data"})

# Storage prefix for workflow output files.
_WORKFLOW_OUTPUTS_PREFIX = "workflow-outputs"


# ---------------------------------------------------------------------------
# File checksum helper
# ---------------------------------------------------------------------------


def compute_sha256(file_path: Path) -> str:
    """Compute the SHA-256 hex digest of *file_path* in streaming chunks."""
    with open(file_path, "rb") as fh:
        digest = hashlib.file_digest(fh, "sha256")
    return f"sha256:{digest.hexdigest()}"


# ---------------------------------------------------------------------------
# Upload workflow outputs
# ---------------------------------------------------------------------------


def upload_workflow_outputs(
    case_dir: Path, case_id: str, previous_files: dict[str, dict] | None = None
) -> dict[str, dict]:
    """Upload all files in *case_dir* (except excluded ones) to ``default_storage``.

    Walks *case_dir* recursively and uploads each file to::

        workflow-outputs/<case_id>/<relative_path>

    Files named ``prd.json``, and ``progress.json`` are skipped.
    If *previous_files* is provided, checks the local file's SHA-256 against its
    existing backend record and skips uploading if unchanged.

    Returns a mapping of ``relative_path_str → record dict`` for every file
    that was successfully uploaded.  Failures are logged and skipped rather
    than raising exceptions so that a single bad file does not abort the run.

    Args:
        case_dir:       Absolute path to the workflow run work directory.
        case_id:        Jawafdehi case identifier (e.g. ``"case-abc123"``).
        previous_files: Existing files dictionary from ``progress.json``.

    Returns:
        Dict mapping local relative path strings to the file tracking record.
    """
    uploaded: dict[str, dict] = {}
    previous_files = previous_files or {}

    for abs_path in sorted(case_dir.rglob("*")):
        if not abs_path.is_file():
            continue
        if abs_path.name in _EXCLUDED_FILENAMES:
            logger.debug("Skipping excluded file: %s", abs_path.name)
            continue

        rel_path = abs_path.relative_to(case_dir)
        if rel_path.parts[0] in _EXCLUDED_DIRS:
            logger.debug("Skipping excluded directory: %s", rel_path.parts[0])
            continue
        rel_str = str(rel_path)

        if rel_str in previous_files:
            try:
                local_checksum = compute_sha256(abs_path)
                if local_checksum == previous_files[rel_str].get("checksum"):
                    logger.debug("Skipping upload, unchanged: %s", rel_str)
                    continue
            except OSError:
                pass

        storage_name = f"{_WORKFLOW_OUTPUTS_PREFIX}/{case_id}/{rel_path.as_posix()}"

        try:
            with open(abs_path, "rb") as fh:
                saved_name = default_storage.save(storage_name, File(fh))
            record = build_file_record(abs_path, saved_name)
            uploaded[str(rel_path)] = record
            logger.debug("Uploaded %s → %s", rel_path, saved_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to upload %s: %s", rel_path, exc)

    logger.info(
        "Uploaded %d file(s) for case %s to default_storage", len(uploaded), case_id
    )
    return uploaded


def download_workflow_outputs(case_dir: Path, files_dict: dict[str, dict]) -> None:
    """Download previously uploaded workflow outputs back to the work directory.

    Given the ``files`` tracking dictionary from ``progress.json``, this function
    downloads each tracked file from ``default_storage`` back to its local
    relative path within ``case_dir``. Skips files that exist with a matching checksum.
    """
    for rel_str, record in files_dict.items():
        backend_path = record.get("backend_path")
        if not backend_path or not default_storage.exists(backend_path):
            continue

        local_path = case_dir / rel_str

        # Check if the file already exists and its checksum matches
        if local_path.is_file():
            try:
                local_checksum = compute_sha256(local_path)
                if local_checksum == record.get("checksum"):
                    logger.debug("Skipping download, unchanged: %s", rel_str)
                    continue
            except OSError as exc:
                logger.debug(
                    "Could not verify checksum for %s, re-downloading: %s", rel_str, exc
                )

        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with default_storage.open(backend_path, "rb") as remote_file:
                with open(local_path, "wb") as local_file:
                    for chunk in remote_file.chunks():
                        local_file.write(chunk)
            logger.debug("Downloaded workflow output %s → %s", backend_path, rel_str)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to download workflow output %s: %s", backend_path, exc
            )


# ---------------------------------------------------------------------------
# Track downloaded source files in progress.json
# ---------------------------------------------------------------------------


def build_file_record(local_path: Path, backend_path: str) -> dict:
    """Build a tracking record for a single downloaded file.

    The record is stored in the ``"files"`` dictionary of ``progress.json``
    and is keyed by the *local* path string relative to the work directory.

    Args:
        local_path:   Absolute (or relative) path to the local file.
        backend_path: The storage backend path / URL for the file.

    Returns:
        Dict with keys ``backend_path``, ``size``, and ``checksum``.
    """
    size = os.path.getsize(local_path)
    checksum = compute_sha256(local_path)
    return {
        "backend_path": backend_path,
        "size": size,
        "checksum": checksum,
    }


def record_downloaded_files(
    progress_data: dict,
    case_dir: Path,
    local_paths: list[Path],
) -> dict:
    """Update *progress_data* with file tracking records for *local_paths*.

    For each file in *local_paths* the function:

    1. Uploads the file to ``default_storage`` under
       ``workflow-outputs/<case_id>/sources/<filename>``.
    2. Computes size and SHA-256 checksum.
    3. Adds an entry to ``progress_data["files"]``.

    *progress_data* is mutated in place AND returned so callers can chain
    this call or write back to disk immediately.

    Args:
        progress_data: Current parsed ``progress.json`` dict.
        case_dir:      Work directory for resolving relative paths.
        local_paths:   Absolute paths to freshly downloaded files.

    Returns:
        The mutated *progress_data* dict.
    """
    if "files" not in progress_data:
        progress_data["files"] = {}

    for abs_path in local_paths:
        if not abs_path.is_file():
            logger.warning(
                "record_downloaded_files: not a file, skipping: %s", abs_path
            )
            continue

        try:
            rel_path = abs_path.relative_to(case_dir)
        except ValueError:
            rel_path = abs_path  # type: ignore[assignment]

        rel_str = str(rel_path)
        # Derive a backend path that mirrors the work directory layout.
        # We prefix with a placeholder case_id token; callers who know the
        # case_id can pass it via ``upload_workflow_outputs`` directly.
        storage_name = f"{_WORKFLOW_OUTPUTS_PREFIX}/{rel_path.as_posix()}"

        try:
            with open(abs_path, "rb") as fh:
                saved_name = default_storage.save(storage_name, File(fh))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not upload downloaded file %s: %s", abs_path, exc)
            saved_name = storage_name  # fall back to intended path

        try:
            record = build_file_record(abs_path, saved_name)
        except OSError as exc:
            logger.warning("Could not stat/checksum %s: %s", abs_path, exc)
            continue

        progress_data["files"][rel_str] = record
        logger.debug("Recorded downloaded file: %s → %s", rel_str, saved_name)

    return progress_data
