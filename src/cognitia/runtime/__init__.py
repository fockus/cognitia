"""Модуль runtime — типы, протоколы, фабрика и политика моделей.

AgentRuntime v1 контракт:
- AgentRuntime Protocol (base.py)
- RuntimeEvent, Message, ToolSpec, RuntimeConfig (types.py)
- RuntimeFactory (factory.py)

Legacy:
- StreamEvent, RuntimeAdapter — backward compat (adapter.py)
- ClaudeOptionsBuilder — infrastructure (options_builder.py)
"""

# --- AgentRuntime v1 контракт ---
from cognitia.runtime.base import AgentRuntime
from cognitia.runtime.factory import RuntimeFactory
from cognitia.runtime.model_policy import ModelPolicy
from cognitia.runtime.model_registry import ModelRegistry, get_registry, reset_registry

# --- Runtime Ports (каноничные адаптеры AgentRuntime → RuntimePort) ---
from cognitia.runtime.ports import (
    BaseRuntimePort,
    DeepAgentsRuntimePort,
    ThinRuntimePort,
)
from cognitia.runtime.ports.base import StreamEvent, convert_event
from cognitia.runtime.types import (
    DEFAULT_MODEL,
    RUNTIME_ERROR_KINDS,
    RUNTIME_EVENT_TYPES,
    VALID_MODEL_NAMES,
    VALID_RUNTIME_NAMES,
    Message,
    RuntimeConfig,
    RuntimeErrorData,
    RuntimeEvent,
    ToolSpec,
    TurnMetrics,
    resolve_model_name,
)

# --- Legacy: backward compat re-exports ---
try:
    from cognitia.runtime.adapter import RuntimeAdapter
    from cognitia.runtime.options_builder import ClaudeOptionsBuilder
except ImportError:
    pass

__all__ = [
    "DEFAULT_MODEL",
    "RUNTIME_ERROR_KINDS",
    "RUNTIME_EVENT_TYPES",
    "VALID_MODEL_NAMES",
    "VALID_RUNTIME_NAMES",
    "AgentRuntime",
    "BaseRuntimePort",
    "DeepAgentsRuntimePort",
    "Message",
    "ModelPolicy",
    "ModelRegistry",
    "RuntimeConfig",
    "RuntimeErrorData",
    "RuntimeEvent",
    "RuntimeFactory",
    "StreamEvent",
    "ThinRuntimePort",
    "ToolSpec",
    "TurnMetrics",
    "convert_event",
    "get_registry",
    "reset_registry",
    "resolve_model_name",
]
