from __future__ import annotations

from typing import Any


def filter_public_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep response sources in the retrieved evidence set shape."""
    safe_sources = []
    seen = set()
    for source in sources:
        key = (
            source.get("type"),
            source.get("url"),
            source.get("title"),
            source.get("source_id"),
        )
        if key in seen:
            continue
        seen.add(key)
        safe_sources.append(source)
    return safe_sources
