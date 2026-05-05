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


def normalize_search(question: str) -> str:
    normalized = question.strip()
    lowered = normalized.lower()
    for phrase in STOP_PHRASES:
        lowered = lowered.replace(phrase, " ")
    return " ".join(lowered.split()) or normalized


def extract_bs_year(question: str) -> str | None:
    match = BS_YEAR_PATTERN.search(question)
    return match.group(1) if match else None


def route_question(question: str) -> RouteDecision:
    lowered = question.lower()
    year = extract_bs_year(question)

    if any(keyword in lowered for keyword in KNOWLEDGE_RAG_KEYWORDS) or (
        year
        and "registered" in lowered
        and any(word in lowered for word in ["type", "kind"])
    ):
        return RouteDecision("knowledge_rag", normalize_search(question), "knowledge")

    if any(keyword in lowered for keyword in COUNT_KEYWORDS):
        return RouteDecision(
            "case_count",
            normalize_search(question),
            "count",
            "public_search_published_cases",
        )

    if any(keyword in lowered for keyword in ENTITY_KEYWORDS):
        return RouteDecision(
            "entity_search",
            normalize_search(question),
            "entity",
            "public_search_jawaf_entities",
        )

    return RouteDecision(
        "case_search",
        normalize_search(question),
        "case",
        "public_search_published_cases",
    )
