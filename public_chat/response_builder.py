from __future__ import annotations

from typing import Any

UNSUPPORTED_RAG_MESSAGE = (
    "I cannot verify that from the public knowledge index yet. Public document "
    "questions need an enabled, admin-configured knowledge collection before I can "
    "answer them with citations."
)


def refusal_response(message: str, session_id: str = "") -> dict[str, Any]:
    return {
        "answer_text": message,
        "session_id": session_id,
        "sources": [],
        "related_cases": [],
        "follow_up_questions": [],
    }


def case_url(case: dict[str, Any]) -> str:
    slug = case.get("slug")
    if slug:
        return f"/case/{slug}"
    return f"/case/{case.get('id')}"


def build_related_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(case["id"]),
        "title": case.get("title") or "Untitled case",
        "url": case_url(case),
        "slug": case.get("slug"),
        "case_id": case.get("case_id"),
        "short_description": case.get("short_description") or "",
    }


def build_source(source: dict[str, Any], source_type: str = "source") -> dict[str, Any]:
    urls = source.get("url") or []
    if isinstance(urls, str):
        urls = [urls]
    url = urls[0] if urls else ""
    return {
        "title": source.get("title") or source.get("source_id") or "Public source",
        "url": url,
        "type": source_type,
        "snippet": source.get("description") or "",
        "source_id": source.get("source_id"),
        "document_id": None,
        "chunk_id": None,
        "page_start": None,
        "page_end": None,
        "score": None,
    }


def build_case_source(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": case.get("title") or "Published case",
        "url": case_url(case),
        "type": "case",
        "snippet": case.get("short_description") or "",
        "source_id": None,
        "document_id": None,
        "chunk_id": None,
        "page_start": None,
        "page_end": None,
        "score": None,
    }


def build_knowledge_source(chunk: dict[str, Any]) -> dict[str, Any]:
    title = (
        chunk.get("source_title") or chunk.get("section_title") or "Knowledge source"
    )
    section = chunk.get("section_title") or chunk.get("table_title") or ""
    snippet = chunk.get("text") or ""
    if section:
        snippet = f"{section}\n{snippet}".strip()
    return {
        "title": title,
        "url": chunk.get("source_url") or chunk.get("storage_path") or "",
        "type": chunk.get("source_type") or "knowledge",
        "snippet": snippet,
        "source_id": str(chunk.get("source_id") or ""),
        "document_id": str(chunk.get("document_id") or ""),
        "chunk_id": str(chunk.get("chunk_id") or ""),
        "page_start": chunk.get("page_start"),
        "page_end": chunk.get("page_end"),
        "score": chunk.get("score"),
    }
