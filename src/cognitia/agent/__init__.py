"""cognitia.agent — high-level facade для интеграции cognitia в приложения."""

from cognitia.agent.agent import Agent
from cognitia.agent.config import AgentConfig
from cognitia.agent.conversation import Conversation
from cognitia.agent.middleware import (
    BudgetExceededError,
    CostTracker,
    Middleware,
    SecurityGuard,
)
from cognitia.agent.result import Result
from cognitia.agent.tool import ToolDefinition, tool

__all__ = [
    "Agent",
    "AgentConfig",
    "BudgetExceededError",
    "Conversation",
    "CostTracker",
    "Middleware",
    "Result",
    "SecurityGuard",
    "ToolDefinition",
    "tool",
]
