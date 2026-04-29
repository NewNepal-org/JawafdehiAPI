from __future__ import annotations

import json
from typing import Any

from caseworker.services import LLMService


class PublicChatLLMError(RuntimeError):
    pass


def _bounded_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + "\n[truncated]"


def build_public_chat_prompt(
    *,
    config,
    question: str,
    history: list[dict[str, str]],
    evidence: dict[str, Any],
    language: str,
) -> str:
    skills = [
        skill.content
        for skill in config.prompt.skills.filter(is_active=True).order_by("name")
    ]
    history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history)
    evidence_text = json.dumps(evidence, ensure_ascii=False, indent=2)

    sections = [
        config.prompt.prompt,
        "\nSelected skills/instructions:",
        "\n\n".join(skills) if skills else "(none)",
        "\nConversation history:",
        _bounded_text(history_text or "(none)", config.max_history_chars),
        "\nPublic evidence:",
        _bounded_text(evidence_text, config.max_evidence_chars),
        "\nUser question:",
        question,
        "\nResponse language:",
        language or "auto",
    ]
    return "\n".join(sections)


def generate_answer(config, prompt: str) -> str:
    try:
        llm_service = LLMService()
        llm = llm_service.get_llm(config.llm_provider)
        return llm_service._call_llm(llm, prompt).strip()
    except Exception as exc:
        raise PublicChatLLMError(str(exc)) from exc
