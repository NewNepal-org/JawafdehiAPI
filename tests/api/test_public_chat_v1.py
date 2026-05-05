from unittest.mock import patch

import pytest
from django.core.cache import caches
from django.test import override_settings
from rest_framework.test import APIClient

from caseworker.models import Prompt, PublicChatConfig, Skill
from config.mcp_servers import build_public_chat_mcp_servers
from knowledge.models import (
    AccessLevel,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeSource,
)
from public_chat.mcp_client import PublicChatMCPClient, PublicChatMCPError
from public_chat.quota import QUOTA_CACHE_NAME, check_and_increment_quota
from public_chat.routing import PUBLIC_CHAT_MCP_TOOLS, route_question

PUBLIC_CHAT_URL = "/api/chat/public/"


@pytest.fixture
def public_chat_config():
    caches["default"].clear()
    caches[QUOTA_CACHE_NAME].clear()
    PublicChatConfig.objects.all().delete()
    prompt = Prompt.objects.create(
        name="public-chat-test",
        display_name="Public Chat Test",
        description="Test prompt",
        prompt="Configured public prompt. Answer only from supplied evidence.",
        model="claude-opus-4-6",
        temperature=0.2,
        max_tokens=1000,
    )
    return PublicChatConfig.objects.create(
        name="default-test",
        is_active=True,
        enabled=True,
        prompt=prompt,
        quota_scope="ip_session",
        quota_limit=10,
        quota_window_seconds=86400,
        max_question_chars=1000,
        max_history_turns=6,
        max_history_chars=4000,
        max_mcp_results=5,
        max_tool_calls=3,
        max_evidence_chars=8000,
    )


def published_case_payload(**overrides):
    payload = {
        "id": 42,
        "case_id": "case-42",
        "slug": "procurement-case",
        "state": "PUBLISHED",
        "title": "Published procurement case",
        "short_description": "Public summary",
        "description": "Public description",
    }
    payload.update(overrides)
    return payload


def test_public_chat_mcp_config_defaults_to_workflow_stdio_shape():
    servers = build_public_chat_mcp_servers(api_base_url="http://127.0.0.1:8000")

    assert servers == {
        "jawafdehi": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/Jawafdehi/jawafdehi-mcp.git",
                "jawafdehi-mcp",
            ],
            "transport": "stdio",
            "env": {"JAWAFDEHI_API_BASE_URL": "http://127.0.0.1:8000"},
        }
    }
    assert "JAWAFDEHI_API_TOKEN" not in servers["jawafdehi"]["env"]


def test_public_chat_mcp_config_supports_full_env_override():
    servers = build_public_chat_mcp_servers(
        api_base_url="http://127.0.0.1:8000",
        servers_json=(
            '{"jawafdehi": {"command": "uv", "args": ["run", "--directory", '
            '"/tmp/jawafdehi-mcp", "jawafdehi-mcp"], "transport": "stdio", '
            '"env": {"JAWAFDEHI_API_BASE_URL": "http://127.0.0.1:8000"}}}'
        ),
    )

    assert servers["jawafdehi"]["command"] == "uv"
    assert servers["jawafdehi"]["args"] == [
        "run",
        "--directory",
        "/tmp/jawafdehi-mcp",
        "jawafdehi-mcp",
    ]
    assert servers["jawafdehi"]["transport"] == "stdio"
    assert servers["jawafdehi"]["env"] == {
        "JAWAFDEHI_API_BASE_URL": "http://127.0.0.1:8000"
    }


def test_public_chat_routing_owns_public_mcp_tool_policy():
    assert PUBLIC_CHAT_MCP_TOOLS == frozenset(
        {
            "public_search_published_cases",
            "public_get_published_case",
            "public_search_jawaf_entities",
        }
    )
    assert (
        route_question("How many procurement cases are published?").tool_name
        == "public_search_published_cases"
    )
    assert (
        route_question("Show person entities related to procurement").tool_name
        == "public_search_jawaf_entities"
    )
    report_route = route_question("What is in the 2078 annual report?")
    assert report_route.route == "knowledge_rag"
    assert report_route.tool_name is None


def test_mcp_client_parses_json_text_content():
    parsed = PublicChatMCPClient()._parse_tool_result(
        [{"type": "text", "text": '{"count": 1, "results": []}'}]
    )

    assert parsed == {"count": 1, "results": []}


def test_mcp_client_plain_text_errors_become_public_errors():
    with pytest.raises(PublicChatMCPError, match="Error accessing public cases API"):
        PublicChatMCPClient()._parse_tool_result(
            [{"type": "text", "text": "Error accessing public cases API: timeout"}]
        )


@pytest.mark.django_db
def test_public_chat_uses_configured_prompt_and_active_skills(public_chat_config):
    active_skill = Skill.objects.create(
        name="public-citations",
        display_name="Public Citations",
        description="Citation instruction",
        content="Cite the retrieved public source.",
        is_active=True,
    )
    inactive_skill = Skill.objects.create(
        name="inactive-skill",
        display_name="Inactive Skill",
        description="Inactive",
        content="This must not be loaded.",
        is_active=False,
    )
    public_chat_config.prompt.skills.add(active_skill, inactive_skill)
    captured = {}

    def fake_generate_answer(config, prompt):
        captured["prompt"] = prompt
        return "There is one supported published procurement case."

    with (
        patch(
            "public_chat.views.understand_question",
            return_value=route_question("How many procurement cases are published?"),
        ),
        patch(
            "public_chat.views.PublicChatMCPClient.call_tool",
            return_value={"count": 1, "results": [published_case_payload()]},
        ) as mcp_call,
        patch("public_chat.views.generate_answer", side_effect=fake_generate_answer),
    ):
        response = APIClient().post(
            PUBLIC_CHAT_URL,
            data={
                "question": "How many procurement cases are published?",
                "session_id": "session-a",
                "history": [],
                "language": "en",
            },
            format="json",
        )

    assert response.status_code == 200
    assert "Configured public prompt" in captured["prompt"]
    assert "Cite the retrieved public source" in captured["prompt"]
    assert "This must not be loaded" not in captured["prompt"]
    assert response.data["sources"][0]["type"] == "case"
    assert response.data["related_cases"][0]["case_id"] == "case-42"
    mcp_call.assert_called_once()


@pytest.mark.django_db
def test_quota_blocks_before_mcp_and_llm_even_after_session_reset(public_chat_config):
    public_chat_config.quota_limit = 1
    public_chat_config.save()

    with (
        patch(
            "public_chat.views.understand_question",
            return_value=route_question("procurement cases"),
        ),
        patch(
            "public_chat.views.PublicChatMCPClient.call_tool",
            return_value={"count": 1, "results": [published_case_payload()]},
        ) as mcp_call,
        patch(
            "public_chat.views.generate_answer", return_value="Supported answer"
        ) as llm_call,
    ):
        first = APIClient().post(
            PUBLIC_CHAT_URL,
            data={"question": "procurement cases", "session_id": "session-a"},
            format="json",
            REMOTE_ADDR="203.0.113.10",
        )
        second = APIClient().post(
            PUBLIC_CHAT_URL,
            data={"question": "procurement cases", "session_id": "session-b"},
            format="json",
            REMOTE_ADDR="203.0.113.10",
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.data["error"] == "quota_exceeded"
    assert mcp_call.call_count == 1
    assert llm_call.call_count == 1


@pytest.mark.django_db
def test_rag_disabled_refuses_before_mcp_or_answer_llm(public_chat_config):
    with (
        patch(
            "public_chat.views.understand_question",
            return_value=route_question(
                "In the 2078 annual report, how many cases were registered?"
            ),
        ),
        patch("public_chat.views.PublicChatMCPClient.call_tool") as mcp_call,
        patch("public_chat.views.generate_answer") as llm_call,
    ):
        response = APIClient().post(
            PUBLIC_CHAT_URL,
            data={
                "question": "In the 2078 annual report, how many cases were registered?"
            },
            format="json",
        )

    assert response.status_code == 200
    assert "public knowledge index" in response.data["answer_text"]
    assert response.data["sources"] == []
    mcp_call.assert_not_called()
    llm_call.assert_not_called()


@pytest.mark.django_db
def test_rag_enabled_without_chunks_refuses_before_mcp_or_answer_llm(
    public_chat_config,
):
    public_chat_config.knowledge_rag_enabled = True
    public_chat_config.save()

    with (
        patch(
            "public_chat.views.understand_question",
            return_value=route_question(
                "In the 2079 annual report, how many cases were registered?"
            ),
        ),
        patch("public_chat.views.PublicChatMCPClient.call_tool") as mcp_call,
        patch("public_chat.views.generate_answer") as llm_call,
    ):
        response = APIClient().post(
            PUBLIC_CHAT_URL,
            data={
                "question": "In the 2079 annual report, how many cases were registered?"
            },
            format="json",
        )

    assert response.status_code == 200
    assert (
        "could not find configured public Jawafdehi records"
        in response.data["answer_text"]
    )
    assert response.data["sources"] == []
    mcp_call.assert_not_called()
    llm_call.assert_not_called()


@pytest.mark.django_db
def test_public_chat_knowledge_rag_uses_configured_public_chunks(public_chat_config):
    collection = KnowledgeCollection.objects.create(
        name="annual_reports",
        display_name="Annual Reports",
        access_level=AccessLevel.PUBLIC,
    )
    source = KnowledgeSource.objects.create(
        collection=collection,
        title="Annual Report 2079",
        source_type="annual_report",
        source_url="https://jawafdehi.org/reports/2079.pdf",
        access_level=AccessLevel.PUBLIC,
    )
    KnowledgeChunk.objects.create(
        source=source,
        chunk_index=0,
        text="In fiscal year 2079, the report says 120 cases were registered by type.",
        page_start=21,
        page_end=21,
        section_title="Case registration by type",
        content_hash="knowledge-public-chat-2079",
    )
    public_chat_config.knowledge_rag_enabled = True
    public_chat_config.save()
    public_chat_config.knowledge_collections.add(collection)
    captured = {}

    def fake_generate_answer(config, prompt):
        captured["prompt"] = prompt
        return "The 2079 report says 120 cases were registered by type."

    with (
        patch(
            "public_chat.views.understand_question",
            return_value=route_question(
                "In the 2079 annual report, how many cases were registered by type?"
            ),
        ),
        patch("public_chat.views.PublicChatMCPClient.call_tool") as mcp_call,
        patch("public_chat.views.generate_answer", side_effect=fake_generate_answer),
    ):
        response = APIClient().post(
            PUBLIC_CHAT_URL,
            data={
                "question": "In the 2079 annual report, how many cases were registered by type?",
                "session_id": "session-rag",
            },
            format="json",
        )

    assert response.status_code == 200
    assert "knowledge_chunks" in captured["prompt"]
    assert (
        response.data["sources"][0]["url"] == "https://jawafdehi.org/reports/2079.pdf"
    )
    assert response.data["sources"][0]["page_start"] == 21
    assert response.data["related_cases"] == []
    mcp_call.assert_not_called()


@pytest.mark.django_db
def test_non_published_mcp_output_is_rejected_defensively(public_chat_config):
    with (
        patch(
            "public_chat.views.understand_question",
            return_value=route_question("procurement cases"),
        ),
        patch(
            "public_chat.views.PublicChatMCPClient.call_tool",
            return_value={
                "count": 1,
                "results": [published_case_payload(state="IN_REVIEW")],
            },
        ),
        patch("public_chat.views.generate_answer") as llm_call,
    ):
        response = APIClient().post(
            PUBLIC_CHAT_URL,
            data={"question": "procurement cases", "session_id": "session-a"},
            format="json",
        )

    assert response.status_code == 200
    assert (
        "could not find configured public Jawafdehi records"
        in response.data["answer_text"]
    )
    assert response.data["sources"] == []
    assert response.data["related_cases"] == []
    llm_call.assert_not_called()


@pytest.mark.django_db
def test_mcp_failure_returns_clean_503(public_chat_config):
    with (
        patch(
            "public_chat.views.understand_question",
            return_value=route_question("procurement cases"),
        ),
        patch(
            "public_chat.views.PublicChatMCPClient.call_tool",
            side_effect=PublicChatMCPError("Error accessing public cases API: timeout"),
        ),
        patch("public_chat.views.generate_answer") as llm_call,
    ):
        response = APIClient().post(
            PUBLIC_CHAT_URL,
            data={"question": "procurement cases", "session_id": "session-a"},
            format="json",
        )

    assert response.status_code == 503
    assert "Public chat retrieval failed" in response.data["detail"]
    assert "timeout" in response.data["detail"]
    llm_call.assert_not_called()


@pytest.mark.django_db
@override_settings(DEBUG=False, PUBLIC_CHAT_MCP_SERVERS={})
def test_missing_production_mcp_config_returns_503_before_quota(public_chat_config):
    with (
        patch(
            "public_chat.views.understand_question",
            return_value=route_question("procurement cases"),
        ),
        patch("public_chat.views.PublicChatMCPClient.call_tool") as mcp_call,
    ):
        response = APIClient().post(
            PUBLIC_CHAT_URL,
            data={"question": "procurement cases", "session_id": "session-a"},
            format="json",
            REMOTE_ADDR="203.0.113.30",
        )

    assert response.status_code == 503
    assert "Public chat MCP server is not configured." in response.data["detail"]
    mcp_call.assert_not_called()


@pytest.mark.django_db
@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-default-cache",
        },
        QUOTA_CACHE_NAME: {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-public-chat-quota-cache",
        },
    }
)
def test_quota_uses_named_public_chat_cache(public_chat_config):
    class Request:
        META = {"REMOTE_ADDR": "203.0.113.40"}

    public_chat_config.quota_scope = "ip"
    public_chat_config.save()
    caches["default"].clear()
    caches[QUOTA_CACHE_NAME].clear()

    first = check_and_increment_quota(public_chat_config, Request(), "session-a")
    caches["default"].clear()
    second = check_and_increment_quota(public_chat_config, Request(), "session-a")
    caches[QUOTA_CACHE_NAME].clear()
    reset = check_and_increment_quota(public_chat_config, Request(), "session-a")

    assert first["used"] == 1
    assert second["used"] == 2
    assert reset["used"] == 1
