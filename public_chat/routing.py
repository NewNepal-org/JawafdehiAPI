import re
from dataclasses import dataclass

KNOWLEDGE_RAG_KEYWORDS = [
    "annual report",
    "annual-report",
    "statistical report",
    "yearly report",
    "documentation",
    "document",
    "archive",
    "judicial data",
    "ngm",
    "evidence document",
    "source document",
    "process",
    "verify",
    "verification",
    "methodology",
    "faq",
    "policy",
    "report",
    "बार्षिक प्रतिवेदन",
    "वार्षिक प्रतिवेदन",
    "कागजात",
    "दस्तावेज",
    "प्रतिवेदन",
    "प्रक्रिया",
    "प्रमाण",
]

BS_YEAR_PATTERN = re.compile(r"\b(20[0-9]{2})(?:[/\-.।](?:[0-9]{2,4}))?\b")
CASE_ID_PATTERN = re.compile(
    r"\bcase(?:\s+id)?\s*[:#-]?\s*([A-Za-z0-9][A-Za-z0-9_-]{1,80})\b",
    flags=re.IGNORECASE,
)
CASE_LOOKUP_PREFIX_PATTERN = re.compile(
    r"^\s*case(?:\s+id)?(?:\s+|[:#]\s*)(?P<identifier>.+?)\s*$",
    flags=re.IGNORECASE,
)

COUNT_KEYWORDS = [
    "how many",
    "count",
    "total",
    "number of",
    "कति",
    "जम्मा",
    "संख्या",
]

ENTITY_KEYWORDS = [
    "entity",
    "person",
    "organization",
    "office",
    "ministry",
    "व्यक्ति",
    "संस्था",
    "कार्यालय",
]

STOP_PHRASES = [
    "how many",
    "number of",
    "count",
    "total",
    "cases",
    "case",
    "are there",
    "were there",
    "registered",
    "show me",
    "what are",
    "what is",
    "?",
]

PUBLIC_CHAT_MCP_TOOLS = frozenset(
    {
        "public_search_published_cases",
        "public_get_published_case",
        "public_search_jawaf_entities",
    }
)


@dataclass(frozen=True)
class RouteDecision:
    route: str
    search: str
    reason: str
    tool_name: str | None = None
    classifier_source: str = "deterministic"
    confidence: float | None = None
    classifier_error: str | None = None


def normalize_search(question: str) -> str:
    normalized = question.strip()
    lowered = normalized.lower()
    for phrase in STOP_PHRASES:
        lowered = lowered.replace(phrase, " ")
    return " ".join(lowered.split()) or normalized


def extract_bs_year(question: str) -> str | None:
    match = BS_YEAR_PATTERN.search(question)
    return match.group(1) if match else None


def extract_case_identifier(question: str) -> str | None:
    match = CASE_ID_PATTERN.search(question)
    return match.group(1) if match else None


def normalize_case_lookup_identifier(value: str) -> str:
    """Strip conversational case prefixes without damaging slug-like ids."""
    normalized = value.strip()
    match = CASE_LOOKUP_PREFIX_PATTERN.match(normalized)
    if not match:
        return normalized

    identifier = match.group("identifier").strip()
    return identifier.removeprefix("#").strip() or normalized


def route_question(
    question: str, *, default_to_case_search: bool = True
) -> RouteDecision:
    lowered = question.lower()
    year = extract_bs_year(question)
    case_identifier = extract_case_identifier(question)

    if case_identifier and any(
        keyword in lowered
        for keyword in ["get", "show", "detail", "details", "case", "fetch"]
    ):
        return RouteDecision(
            "case_get",
            case_identifier,
            "case",
            "public_get_published_case",
            classifier_source="deterministic",
            confidence=0.9,
        )

    if any(keyword in lowered for keyword in KNOWLEDGE_RAG_KEYWORDS) or (
        year
        and "registered" in lowered
        and any(word in lowered for word in ["type", "kind"])
    ):
        return RouteDecision(
            "knowledge_rag",
            normalize_search(question),
            "knowledge",
            classifier_source="deterministic",
            confidence=0.9,
        )

    if any(keyword in lowered for keyword in COUNT_KEYWORDS):
        return RouteDecision(
            "case_count",
            normalize_search(question),
            "count",
            "public_search_published_cases",
            classifier_source="deterministic",
            confidence=0.85,
        )

    if any(keyword in lowered for keyword in ENTITY_KEYWORDS):
        return RouteDecision(
            "entity_search",
            normalize_search(question),
            "entity",
            "public_search_jawaf_entities",
            classifier_source="deterministic",
            confidence=0.85,
        )

    if not default_to_case_search:
        return RouteDecision(
            "clarify",
            normalize_search(question),
            "uncertain",
            classifier_source="deterministic",
            confidence=0.0,
        )

    return RouteDecision(
        "case_search",
        normalize_search(question),
        "case",
        "public_search_published_cases",
        classifier_source="deterministic",
        confidence=0.5,
    )
