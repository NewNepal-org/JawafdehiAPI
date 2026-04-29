from __future__ import annotations

import json
from typing import Any

from asgiref.sync import async_to_sync
from django.conf import settings


class PublicChatMCPError(RuntimeError):
    pass


class PublicChatMCPClient:
    """Small MCP facade for public chat allow-listed tools."""

    allowed_tools = {
        "public_search_published_cases",
        "public_get_published_case",
        "public_search_jawaf_entities",
    }

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self.allowed_tools:
            raise PublicChatMCPError(f"Tool {name} is not allowed for public chat")
        return async_to_sync(self._call_tool)(name, arguments)

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        servers = getattr(settings, "PUBLIC_CHAT_MCP_SERVERS", {})
        if not servers:
            raise PublicChatMCPError("Public chat MCP server is not configured")

        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError as exc:
            raise PublicChatMCPError(
                "langchain-mcp-adapters is required for public chat MCP access"
            ) from exc

        client = MultiServerMCPClient(servers)
        tools = await client.get_tools()
        tool_map = {tool.name: tool for tool in tools}
        tool = tool_map.get(name)
        if tool is None:
            raise PublicChatMCPError(f"MCP tool {name} was not found")

        raw_result = await tool.ainvoke(arguments)
        return self._parse_tool_result(raw_result)

    def _parse_tool_result(self, raw_result: Any) -> dict[str, Any]:
        if isinstance(raw_result, dict):
            if "structuredContent" in raw_result:
                return raw_result["structuredContent"]
            content = raw_result.get("content")
            if content is None:
                return raw_result
            if isinstance(content, str):
                return self._parse_json_text(content)
            if isinstance(content, list):
                raw_result = content
        if isinstance(raw_result, str):
            return self._parse_json_text(raw_result)
        if isinstance(raw_result, list) and raw_result:
            first_item = raw_result[0]
            text = (
                first_item.get("text")
                if isinstance(first_item, dict)
                else getattr(first_item, "text", None)
            )
            if text is not None:
                return self._parse_json_text(text)
        text = getattr(raw_result, "content", None) or getattr(raw_result, "text", None)
        if text:
            return self._parse_json_text(text)
        raise PublicChatMCPError("Unexpected MCP tool response")

    def _parse_json_text(self, text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except (TypeError, ValueError) as exc:
            message = str(text).strip() or "MCP tool returned a non-JSON response"
            raise PublicChatMCPError(message[:500]) from exc
