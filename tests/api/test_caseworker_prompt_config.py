from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from caseworker.models import Prompt, PublicChatConfig

User = get_user_model()


@pytest.fixture
def staff_client():
    user = User.objects.create_user(
        username="caseworker-admin",
        email="admin@example.com",
        password="testpass123",
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_caseworker_admin_can_manage_prompts_skills_and_public_chat_config(
    staff_client,
):
    PublicChatConfig.objects.all().delete()

    skill_response = staff_client.post(
        "/api/caseworker/skills/",
        data={
            "name": "public-citation-style",
            "display_name": "Public Citation Style",
            "description": "Citation style guidance",
            "content": "Cite every factual answer.",
            "is_active": True,
        },
        format="json",
    )
    assert skill_response.status_code == 201

    prompt_response = staff_client.post(
        "/api/caseworker/prompts/",
        data={
            "name": "public-chat-admin",
            "display_name": "Public Chat Admin",
            "description": "Public chat prompt",
            "prompt": "Use public evidence only.",
            "skills": [skill_response.data["id"]],
            "model": "claude-opus-4-6",
            "temperature": 0.2,
            "max_tokens": 1000,
        },
        format="json",
    )
    assert prompt_response.status_code == 201
    assert prompt_response.data["skills"] == [skill_response.data["id"]]

    config_response = staff_client.post(
        "/api/caseworker/public-chat-configs/",
        data={
            "name": "public-chat-default",
            "is_active": True,
            "enabled": True,
            "prompt": prompt_response.data["id"],
            "llm_provider": None,
            "quota_scope": "ip_session",
            "quota_limit": 10,
            "quota_window_seconds": 86400,
            "max_question_chars": 1000,
            "max_history_turns": 6,
            "max_history_chars": 4000,
            "max_mcp_results": 5,
            "max_tool_calls": 3,
            "max_evidence_chars": 8000,
        },
        format="json",
    )
    assert config_response.status_code == 201
    assert config_response.data["prompt"] == prompt_response.data["id"]
    assert config_response.data["quota_limit"] == 10


@pytest.mark.django_db
def test_summary_generation_uses_prompt_id_and_returns_prompt_name(staff_client):
    prompt = Prompt.objects.create(
        name="case-summary-prompt",
        display_name="Case Summary Prompt",
        description="Summary",
        prompt="Summarize {case_data}: {query}",
        model="claude-opus-4-6",
        temperature=0.2,
        max_tokens=1000,
    )

    with (
        patch(
            "caseworker.views.MCPService.retrieve_case_data",
            return_value={"case": "data"},
        ),
        patch(
            "caseworker.views.SummaryGenerationService.generate_summary",
            return_value="Generated summary",
        ),
    ):
        response = staff_client.post(
            "/api/caseworker/summaries/generate/",
            data={
                "case_number": "123-CR-2024",
                "prompt_id": prompt.id,
                "query": "summarize",
            },
            format="json",
        )

    assert response.status_code == 201
    assert response.data["prompt"] == prompt.id
    assert response.data["prompt_name"] == "case-summary-prompt"
    assert response.data["content"] == "Generated summary"


@pytest.mark.django_db
def test_draft_create_uses_prompt_field_and_returns_prompt_name(staff_client):
    prompt = Prompt.objects.create(
        name="draft-prompt",
        display_name="Draft Prompt",
        description="Draft",
        prompt="Draft a response",
        model="claude-opus-4-6",
        temperature=0.2,
        max_tokens=1000,
    )

    response = staff_client.post(
        "/api/caseworker/drafts/",
        data={
            "case_number": "123-CR-2024",
            "prompt": prompt.id,
            "content": "Draft content",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["prompt"] == prompt.id
    assert response.data["prompt_name"] == "draft-prompt"
