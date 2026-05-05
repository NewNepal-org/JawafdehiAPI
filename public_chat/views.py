from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from caseworker.models import PublicChatConfig
from knowledge.models import AccessLevel
from knowledge.retrieval import KnowledgeAccessContext, KnowledgeRetriever

from .citation_validator import filter_public_sources
from .llm import PublicChatLLMError, build_public_chat_prompt, generate_answer
from .mcp_client import PublicChatMCPClient, PublicChatMCPError
from .query_understanding import understand_question
from .quota import check_and_increment_quota
from .response_builder import (
    UNSUPPORTED_RAG_MESSAGE,
    build_case_source,
    build_knowledge_source,
    build_related_case,
    refusal_response,
)
from .routing import PUBLIC_CHAT_MCP_TOOLS, RouteDecision
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
        decision = understand_question(config, question)

        if decision.route == "clarify":
            response_data = refusal_response(
                "I could not confidently choose the right public Jawafdehi source for that question. Please ask a more specific case, entity, or public document question.",
                session_id,
            )
            return Response(response_data)

        if decision.route == "knowledge_rag" and not config.knowledge_rag_enabled:
            response_data = refusal_response(UNSUPPORTED_RAG_MESSAGE, session_id)
            return Response(response_data)

        try:
            if decision.route == "knowledge_rag":
                evidence = self._retrieve_knowledge_evidence(
                    decision, config, question=question
                )
            else:
                evidence = self._retrieve_mcp_evidence(decision, config)
        except PublicChatMCPError as exc:
            return Response(
                {"detail": f"Public chat retrieval failed: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if (
            not evidence.get("cases")
            and not evidence.get("entities")
            and not evidence.get("knowledge_chunks")
        ):
            response_data = refusal_response(
                "I could not find configured public Jawafdehi records or knowledge sources that support an answer to that question.",
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
            PublicChatConfig.objects.select_related(
                "prompt",
                "llm_provider",
                "classifier_llm_provider",
            )
            .prefetch_related("prompt__skills", "knowledge_collections")
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

    def _retrieve_mcp_evidence(self, decision: RouteDecision, config) -> dict[str, Any]:
        if not decision.tool_name:
            raise PublicChatMCPError("No MCP tool is configured for this route")
        if not settings.DEBUG and not settings.PUBLIC_CHAT_MCP_SERVERS:
            raise PublicChatMCPError("Public chat MCP server is not configured.")

        client = PublicChatMCPClient(allowed_tools=PUBLIC_CHAT_MCP_TOOLS)
        if decision.route == "case_get":
            data = client.call_tool(
                decision.tool_name,
                {"case_id": decision.search, "fetch_sources": True},
            )
            cases = [data] if data.get("state") == "PUBLISHED" else []
            sources = [build_case_source(case) for case in cases]
            return {
                "route": decision.route,
                "search": decision.search,
                "routing": self._routing_metadata(decision),
                "cases": cases,
                "entities": [],
                "sources": sources,
            }

        data = client.call_tool(
            decision.tool_name, {"search": decision.search, "page": 1}
        )
        if decision.route == "entity_search":
            entities = list(data.get("results", []))[: config.max_mcp_results]
            return {
                "route": decision.route,
                "search": decision.search,
                "routing": self._routing_metadata(decision),
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
            "routing": self._routing_metadata(decision),
            "cases": cases,
            "entities": [],
            "sources": sources,
        }

    def _retrieve_knowledge_evidence(
        self, decision: RouteDecision, config, *, question: str
    ) -> dict[str, Any]:
        collections = config.knowledge_collections.filter(
            is_active=True,
            access_level=AccessLevel.PUBLIC,
        )
        retrieved = KnowledgeRetriever().retrieve(
            query=question,
            access_context=KnowledgeAccessContext.public_context(),
            collections=collections,
            max_results=config.max_knowledge_results,
        )
        chunks = [item.as_evidence() for item in retrieved]
        sources = [build_knowledge_source(chunk) for chunk in chunks]
        return {
            "route": decision.route,
            "search": decision.search,
            "routing": self._routing_metadata(decision),
            "knowledge_chunks": chunks,
            "cases": [],
            "entities": [],
            "sources": sources,
        }

    @staticmethod
    def _routing_metadata(decision: RouteDecision) -> dict[str, Any]:
        return {
            "route": decision.route,
            "reason": decision.reason,
            "classifier_source": decision.classifier_source,
            "confidence": decision.confidence,
            "classifier_error": decision.classifier_error,
        }
