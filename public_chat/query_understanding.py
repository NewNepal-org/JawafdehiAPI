from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from caseworker.services import LLMService

from .routing import RouteDecision, route_question

logger = logging.getLogger(__name__)

INTENT_TO_ROUTE = {
    "case_search": ("case_search", "case", "public_search_published_cases"),
    "case_count": ("case_count", "count", "public_search_published_cases"),
    "entity_search": ("entity_search", "entity", "public_search_jawaf_entities"),
    "knowledge_rag": ("knowledge_rag", "knowledge", None),
}


@dataclass(frozen=True)
class QuestionUnderstanding:
    raw_question: str
    normalized_question: str
    intent: str
    search_query: str
    reason: str
    language: str = "unknown"
    years: list[str] = field(default_factory=list)
    needs_count: bool = False
    needs_type_breakdown: bool = False
    confidence: float = 0.0

    def to_route_decision(self) -> RouteDecision:
        route, reason, tool_name = INTENT_TO_ROUTE[self.intent]
        return RouteDecision(
            route=route,
            search=self.search_query or self.normalized_question or self.raw_question,
            reason=self.reason or reason,
            tool_name=tool_name,
        )


def understand_question(config, question: str) -> RouteDecision:
    """Use semantic query understanding first, with deterministic fallback."""
    try:
        understanding = _semantic_understanding(config, question)
        return understanding.to_route_decision()
    except Exception as exc:  # noqa: BLE001 - fallback is the safety behavior here.
        logger.info("Public chat query understanding fallback used: %s", exc)
        return route_question(question)


def _semantic_understanding(config, question: str) -> QuestionUnderstanding:
    prompt = _build_understanding_prompt(question)
    llm_service = LLMService()
    llm = llm_service.get_llm(config.llm_provider)
    raw = llm_service._call_llm(llm, prompt)
    payload = _extract_json_object(raw)
    return _parse_understanding(question, payload)


def _build_understanding_prompt(question: str) -> str:
    return f"""
You classify one public Jawafdehi chat question into a retrieval plan.

Return ONLY a valid JSON object. No markdown. No prose.

Allowed intents:
- case_search: find published Jawafdehi cases relevant to the question.
- case_count: count or summarize how many published Jawafdehi cases match a topic.
- entity_search: find public Jawafdehi/NES entities such as people, offices, organizations, ministries.
- knowledge_rag: answer from public knowledge documents, reports, annual reports, archives, evidence files, policies, FAQs, methodology, or documentation.

Rules:
- Never output tool names.
- Use knowledge_rag when the user asks about reports, documents, archives, evidence files, methodology, or data that needs document citations.
- Use knowledge_rag for annual-report style questions such as "in year 2079 how many cases were registered and of what type".
- Use case_count only for counts over published Jawafdehi case records, not annual reports or source documents.
- Use entity_search for questions mainly about people, offices, organizations, or ministries.
- Default to case_search only when the question can be answered from published case records.
- search_query should be a concise retrieval query, preserving named entities, years, and important Nepali terms.

JSON shape:
{{
  "intent": "case_search|case_count|entity_search|knowledge_rag",
  "search_query": "concise query",
  "normalized_question": "normalized question",
  "language": "en|ne|mixed|unknown",
  "years": ["2079"],
  "needs_count": true,
  "needs_type_breakdown": false,
  "confidence": 0.0,
  "reason": "short routing reason"
}}

Question: {question}
""".strip()


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("Classifier did not return JSON.")
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("Classifier JSON must be an object.")
    return parsed


def _parse_understanding(
    question: str, payload: dict[str, Any]
) -> QuestionUnderstanding:
    intent = str(payload.get("intent") or "").strip()
    if intent not in INTENT_TO_ROUTE:
        raise ValueError(f"Unsupported classifier intent: {intent}")

    search_query = str(payload.get("search_query") or "").strip()
    normalized_question = str(payload.get("normalized_question") or "").strip()
    if not search_query:
        search_query = normalized_question or route_question(question).search

    years = payload.get("years") or []
    if not isinstance(years, list):
        years = []

    confidence = payload.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    return QuestionUnderstanding(
        raw_question=question,
        normalized_question=normalized_question or question.strip(),
        intent=intent,
        search_query=search_query,
        reason=str(payload.get("reason") or "").strip(),
        language=str(payload.get("language") or "unknown").strip() or "unknown",
        years=[str(year).strip() for year in years if str(year).strip()],
        needs_count=bool(payload.get("needs_count", False)),
        needs_type_breakdown=bool(payload.get("needs_type_breakdown", False)),
        confidence=max(0.0, min(confidence, 1.0)),
    )
