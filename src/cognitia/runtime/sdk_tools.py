"""SDK Tools — обёртки для in-process MCP tools.

Переэкспортирует SDK @tool и create_sdk_mcp_server с удобными именами
для использования из cognitia.

Пример:
    from cognitia.runtime.sdk_tools import mcp_tool, create_mcp_server

    @mcp_tool("greet", "Greet user", {"name": str})
    async def greet(args):
        return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}

    server = create_mcp_server("greeting", tools=[greet])
"""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import (
    McpSdkServerConfig,
    SdkMcpTool,
    create_sdk_mcp_server,
    tool,
)

# Re-export с удобными именами
mcp_tool = tool


def create_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None,
) -> McpSdkServerConfig:
    """Создать in-process MCP сервер.

    Обёртка над SDK create_sdk_mcp_server() с тем же интерфейсом.

    Args:
        name: уникальное имя сервера.
        version: версия сервера.
        tools: список SdkMcpTool (созданных через @mcp_tool).

    Returns:
        McpSdkServerConfig для передачи в ClaudeAgentOptions.mcp_servers.
    """
    return create_sdk_mcp_server(name=name, version=version, tools=tools)
