"""Utility functions for Agni Django module."""

import os
from pathlib import Path
from typing import Optional, Dict, Any

from .services.agni_models import AgniExtractionSession


ALLOWED_EXTENSIONS = {'.txt', '.md', '.doc', '.docx', '.pdf'}


def validate_file_type(filename: str) -> bool:
    """Validate that a file has an allowed extension."""
    if not filename:
        return False
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS


def get_file_validation_error(filename: str) -> Optional[str]:
    """Get error message for unsupported file formats, or None if valid."""
    if not filename:
        return "No file provided"
    if not validate_file_type(filename):
        _, ext = os.path.splitext(filename)
        if not ext:
            return "File must have an extension"
        return f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    return None


def serialize_session(session: AgniExtractionSession) -> Dict[str, Any]:
    """Serialize AgniExtractionSession to JSON-compatible dict."""
    return session.model_dump(mode='json', exclude_computed_fields=True)


def deserialize_session(data: Dict[str, Any]) -> AgniExtractionSession:
    """Deserialize dict to AgniExtractionSession."""
    return AgniExtractionSession.model_validate(data)
