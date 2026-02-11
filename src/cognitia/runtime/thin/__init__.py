"""ThinRuntime — собственный тонкий агентный loop.

Режимы: conversational | react | planner-lite.
Bounded loops с budgets, typed errors, streaming RuntimeEvent.
"""

from cognitia.runtime.thin.mcp_client import McpClient
from cognitia.runtime.thin.runtime import ThinRuntime

__all__ = ["McpClient", "ThinRuntime"]
