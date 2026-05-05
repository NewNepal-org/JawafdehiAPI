from unittest.mock import Mock, patch

import pytest

from caseworker.models import Prompt, PublicChatConfig
from public_chat.query_understanding import (
    QuestionUnderstanding,
    _extract_json_object,
    understand_question,
)


@pytest.fixture
def public_chat_config():
    PublicChatConfig.objects.all().delete()
    prompt = Prompt.objects.create(
        name="understanding-test",
        display_name="Understanding Test",
        description="Test prompt",
        prompt="Answer from evidence.",
        model="claude-opus-4-6",
        temperature=0.2,
        max_tokens=1000,
    )
    return PublicChatConfig.objects.create(
        name="understanding-default",
        is_active=True,
        enabled=True,
        prompt=prompt,
    )


def fake_llm_service(return_text: str):
    service = Mock()
    service.get_llm.return_value = object()
    service._call_llm.return_value = return_text
    return service


@pytest.mark.django_db
def test_understand_question_uses_semantic_json_plan(public_chat_config):
    service = fake_llm_service("""
        {
          "intent": "knowledge_rag",
          "search_query": "2079 registered cases by type annual report",
          "normalized_question": "2079 cases registered by type",
          "language": "en",
          "years": ["2079"],
          "needs_count": true,
          "needs_type_breakdown": true,
          "confidence": 0.91,
          "reason": "annual report data requires knowledge retrieval"
        }
        """)

    with patch("public_chat.query_understanding.LLMService", return_value=service):
        decision = understand_question(
            public_chat_config,
            "During FY 2079, registrations by category?",
        )

    assert decision.route == "knowledge_rag"
    assert decision.search == "2079 registered cases by type annual report"
    assert decision.tool_name is None


@pytest.mark.django_db
def test_understand_question_maps_intents_to_allowlisted_tools(public_chat_config):
    service = fake_llm_service("""
        {
          "intent": "case_count",
          "search_query": "procurement",
          "tool_name": "private_delete_cases",
          "confidence": 0.7,
          "reason": "count published cases"
        }
        """)

    with patch("public_chat.query_understanding.LLMService", return_value=service):
        decision = understand_question(
            public_chat_config, "How many procurement cases?"
        )

    assert decision.route == "case_count"
    assert decision.tool_name == "public_search_published_cases"


@pytest.mark.django_db
def test_understand_question_falls_back_when_classifier_fails(public_chat_config):
    service = fake_llm_service("not json")

    with patch("public_chat.query_understanding.LLMService", return_value=service):
        decision = understand_question(
            public_chat_config,
            "Show person entities related to procurement",
        )

    assert decision.route == "entity_search"
    assert decision.tool_name == "public_search_jawaf_entities"


def test_extract_json_object_handles_markdown_fenced_json():
    parsed = _extract_json_object("""```json
        {"intent": "case_search", "search_query": "procurement"}
        ```""")

    assert parsed["intent"] == "case_search"


def test_question_understanding_route_mapping_never_uses_external_tool_names():
    understanding = QuestionUnderstanding(
        raw_question="How many procurement cases?",
        normalized_question="procurement cases count",
        intent="case_count",
        search_query="procurement",
        reason="count cases",
    )

    decision = understanding.to_route_decision()

    assert decision.tool_name == "public_search_published_cases"
