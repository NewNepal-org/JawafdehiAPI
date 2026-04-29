from dataclasses import dataclass

DOCUMENT_RAG_KEYWORDS = [
    "annual report",
    "archive",
    "judicial data",
    "ngm",
    "2078",
    "2081",
    "2082",
    "evidence document",
    "source document",
    "process",
    "verify",
    "verification",
    "methodology",
    "report",
    "प्रतिवेदन",
    "प्रक्रिया",
    "प्रमाण",
]

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


@dataclass(frozen=True)
class RouteDecision:
    route: str
    search: str
    reason: str


def normalize_search(question: str) -> str:
    normalized = question.strip()
    lowered = normalized.lower()
    for phrase in STOP_PHRASES:
        lowered = lowered.replace(phrase, " ")
    return " ".join(lowered.split()) or normalized


def route_question(question: str) -> RouteDecision:
    lowered = question.lower()

    if any(keyword in lowered for keyword in DOCUMENT_RAG_KEYWORDS):
        return RouteDecision(
            "unsupported_document_rag", normalize_search(question), "document_rag"
        )

    if any(keyword in lowered for keyword in COUNT_KEYWORDS):
        return RouteDecision("case_count", normalize_search(question), "count")

    if any(keyword in lowered for keyword in ENTITY_KEYWORDS):
        return RouteDecision("entity_search", normalize_search(question), "entity")

    return RouteDecision("case_search", normalize_search(question), "case")
