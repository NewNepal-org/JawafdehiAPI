from __future__ import annotations

import json
from typing import Any, Iterable

JAWAFDEHI_MCP_SERVER_NAME = "jawafdehi"
JAWAFDEHI_MCP_PACKAGE = "git+https://github.com/Jawafdehi/jawafdehi-mcp.git"
JAWAFDEHI_MCP_ENTRYPOINT = "jawafdehi-mcp"


def build_jawafdehi_mcp_stdio_server(
    *,
    env: dict[str, str] | None = None,
    command: str = "uvx",
    args: Iterable[str] | None = None,
) -> dict[str, dict]:
    """Build the same stdio MCP server shape used by case workflows."""

    return {
        JAWAFDEHI_MCP_SERVER_NAME: {
            "command": command,
            "args": list(
                args
                or [
                    "--from",
                    JAWAFDEHI_MCP_PACKAGE,
                    JAWAFDEHI_MCP_ENTRYPOINT,
                ]
            ),
            "transport": "stdio",
            "env": dict(env or {}),
        }
    }


def build_public_chat_mcp_servers(
    *,
    api_base_url: str,
    servers_json: str | None = None,
) -> dict[str, dict]:
    if servers_json:
        return _parse_mcp_servers_json(servers_json)

    env = {"JAWAFDEHI_API_BASE_URL": api_base_url}
    return build_jawafdehi_mcp_stdio_server(env=env)


def _parse_mcp_servers_json(raw_value: str) -> dict[str, dict]:
    parsed: Any = json.loads(raw_value)
    if not isinstance(parsed, dict):
        raise ValueError("PUBLIC_CHAT_MCP_SERVERS_JSON must be a JSON object.")

    for server_name, server_config in parsed.items():
        if not isinstance(server_name, str) or not server_name:
            raise ValueError(
                "PUBLIC_CHAT_MCP_SERVERS_JSON server names must be strings."
            )
        if not isinstance(server_config, dict):
            raise ValueError(
                "PUBLIC_CHAT_MCP_SERVERS_JSON server configs must be JSON objects."
            )
        if "transport" not in server_config:
            raise ValueError(
                "PUBLIC_CHAT_MCP_SERVERS_JSON server configs must include transport."
            )

    return parsed
