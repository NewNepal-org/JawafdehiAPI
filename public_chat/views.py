from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from caseworker.models import PublicChatConfig

from .citation_validator import filter_public_sources
from .llm import PublicChatLLMError, build_public_chat_prompt, generate_answer
from .mcp_client import PublicChatMCPClient, PublicChatMCPError
from .quota import check_and_increment_quota
from .response_builder import (
    UNSUPPORTED_RAG_MESSAGE,
    build_case_source,
    build_related_case,
    refusal_response,
)
from .routing import PUBLIC_CHAT_MCP_TOOLS, RouteDecision, route_question
from .serializers import PublicChatRequestSerializer, PublicChatResponseSerializer


class PublicChatView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        config = self._get_active_config()
        if config is None or not config.enabled:
            return Response(
                {"detail": "Public chat is not available right now."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not settings.DEBUG and not settings.PUBLIC_CHAT_MCP_SERVERS:
            return Response(
                {"detail": "Public chat MCP server is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = PublicChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        session_id = payload.get("session_id") or uuid.uuid4().hex
        question = payload["question"]
        if len(question) > config.max_question_chars:
            return Response(
                {
                    "detail": (
                        f"Question is too long. Maximum length is "
                        f"{config.max_question_chars} characters."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        quota = check_and_increment_quota(config, request, session_id)
        if not quota["allowed"]:
            return Response(
                {
                    "detail": "Public chat query limit reached.",
                    "error": "quota_exceeded",
                    "limit": quota["limit"],
                    "window_seconds": quota["window_seconds"],
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        history = self._bound_history(payload.get("history", []), config)
        language = payload.get("language") or "auto"
        decision = route_question(question)

        if decision.route == "unsupported_document_rag":
            response_data = refusal_response(UNSUPPORTED_RAG_MESSAGE, session_id)
            return Response(response_data)

        try:
            evidence = self._retrieve_evidence(decision, config)
        except PublicChatMCPError as exc:
            return Response(
                {"detail": f"Public chat retrieval failed: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not evidence.get("cases") and not evidence.get("entities"):
            response_data = refusal_response(
                "I could not find published public Jawafdehi records that support an answer to that question.",
                session_id,
            )
            return Response(response_data)

        prompt = build_public_chat_prompt(
            config=config,
            question=question,
            history=history,
            evidence=evidence,
            language=language,
        )
        try:
            answer_text = generate_answer(config, prompt)
        except PublicChatLLMError as exc:
            return Response(
                {"detail": f"Public chat answer generation failed: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        sources = filter_public_sources(evidence.get("sources", []))
        related_cases = [build_related_case(case) for case in evidence.get("cases", [])]
        response_data = {
            "answer_text": answer_text,
            "session_id": session_id,
            "sources": sources,
            "related_cases": related_cases,
            "follow_up_questions": [],
        }
        PublicChatResponseSerializer(data=response_data).is_valid(raise_exception=True)
        return Response(response_data)

    def _get_active_config(self):
        return (
            PublicChatConfig.objects.select_related("prompt", "llm_provider")
            .prefetch_related("prompt__skills")
            .filter(is_active=True)
            .first()
        )

    def _bound_history(
        self, history: list[dict[str, str]], config
    ) -> list[dict[str, str]]:
        bounded = history[-config.max_history_turns * 2 :]
        total = 0
        result = []
        for item in reversed(bounded):
            content = item.get("content", "")
            total += len(content)
            if total > config.max_history_chars:
                break
            result.append(item)
        return list(reversed(result))

    def _retrieve_evidence(self, decision: RouteDecision, config) -> dict[str, Any]:
        if not decision.tool_name:
            raise PublicChatMCPError("No MCP tool is configured for this route")

        client = PublicChatMCPClient(allowed_tools=PUBLIC_CHAT_MCP_TOOLS)
        data = client.call_tool(
            decision.tool_name, {"search": decision.search, "page": 1}
        )
        if decision.route == "entity_search":
            entities = list(data.get("results", []))[: config.max_mcp_results]
            return {
                "route": decision.route,
                "search": decision.search,
                "entities": entities,
                "cases": [],
                "sources": [],
            }

        cases = [
            case for case in data.get("results", []) if case.get("state") == "PUBLISHED"
        ][: config.max_mcp_results]
        sources = [build_case_source(case) for case in cases]

        return {
            "route": decision.route,
            "search": decision.search,
            "count": data.get("count", len(cases)),
            "cases": cases,
            "entities": [],
            "sources": sources,
        }
