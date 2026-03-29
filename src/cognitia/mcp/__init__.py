"""Cognitia MCP Server -- expose agent framework as MCP tools.

Two modes:
- headless (default): memory, plans, team coordination, code execution (0 LLM calls)
- full (opt-in): + agent creation/querying (requires API key)

Usage:
    cognitia-mcp              # headless mode (auto-detect)
    cognitia-mcp full         # full mode (needs ANTHROPIC_API_KEY or OPENAI_API_KEY)
    python -m cognitia.mcp    # alternative

Configuration for Claude Code (~/.claude/settings.json):
    {"mcpServers": {"cognitia": {"command": "cognitia-mcp"}}}

Configuration for Codex CLI (~/.codex/config.toml):
    [mcp_servers.cognitia]
    command = "cognitia-mcp"
"""

from cognitia.mcp._server import create_server, main
from cognitia.mcp._session import StatefulSession

__all__ = ["create_server", "main", "StatefulSession"]
