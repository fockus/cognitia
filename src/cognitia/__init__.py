"""Cognitia — переиспользуемая библиотека для AI-агентов на Claude Agent SDK."""

__version__ = "0.2.0"

from cognitia.protocols import (
    ContextBuilder,
    FactStore,
    GoalStore,
    LocalToolResolver,
    MessageStore,
    ModelSelector,
    PhaseStore,
    RoleRouter,
    RoleSkillsProvider,
    RuntimePort,
    SessionFactory,
    SessionManager,
    SessionRehydrator,
    SessionStateStore,
    SummaryStore,
    ToolEventStore,
    ToolIdCodec,
    UserStore,
)
from cognitia.runtime.base import AgentRuntime
from cognitia.runtime.factory import RuntimeFactory
from cognitia.runtime.types import (
    Message,
    RuntimeConfig,
    RuntimeErrorData,
    RuntimeEvent,
    ToolSpec,
    TurnMetrics,
)
from cognitia.types import ContextPack, SkillSet, TurnContext

__all__ = [
    "AgentRuntime",
    "ContextBuilder",
    "ContextPack",
    "FactStore",
    "GoalStore",
    "LocalToolResolver",
    "Message",
    "MessageStore",
    "ModelSelector",
    "PhaseStore",
    "RoleRouter",
    "RoleSkillsProvider",
    "RuntimeConfig",
    "RuntimeErrorData",
    "RuntimeEvent",
    "RuntimeFactory",
    "RuntimePort",
    "SessionFactory",
    "SessionManager",
    "SessionRehydrator",
    "SessionStateStore",
    "SkillSet",
    "SummaryStore",
    "ToolEventStore",
    "ToolIdCodec",
    "ToolSpec",
    "TurnContext",
    "TurnMetrics",
    "UserStore",
]
