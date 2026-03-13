"""Модуль runtime — типы, протоколы, фабрика и политика моделей.

AgentRuntime v1 контракт:
- AgentRuntime Protocol (base.py)
- RuntimeEvent, Message, ToolSpec, RuntimeConfig (types.py)
- RuntimeFactory (factory.py)

Legacy:
- StreamEvent, RuntimeAdapter — backward compat (adapter.py)
- ClaudeOptionsBuilder — infrastructure (options_builder.py)
"""

from contextlib import suppress

# --- AgentRuntime v1 контракт ---
from cognitia.runtime.base import AgentRuntime
from cognitia.runtime.capabilities import (
    RUNTIME_CAPABILITY_FLAGS,
    RUNTIME_TIERS,
    VALID_FEATURE_MODES,
    CapabilityRequirements,
    FeatureMode,
    RuntimeCapabilities,
    RuntimeTier,
    get_runtime_capabilities,
)
from cognitia.runtime.factory import RuntimeFactory
from cognitia.runtime.model_policy import ModelPolicy
from cognitia.runtime.model_registry import ModelRegistry, get_registry, reset_registry

# --- Runtime Ports (каноничные адаптеры AgentRuntime → RuntimePort) ---
from cognitia.runtime.ports import BaseRuntimePort
from cognitia.runtime.ports.base import StreamEvent, convert_event

# Optional ports (require runtime-specific extras)
DeepAgentsRuntimePort = None
with suppress(ImportError):
    from cognitia.runtime.ports import DeepAgentsRuntimePort

ThinRuntimePort = None
with suppress(ImportError):
    from cognitia.runtime.ports import ThinRuntimePort

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
ClaudeOptionsBuilder = None
RuntimeAdapter = None
with suppress(ImportError):
    from cognitia.runtime.adapter import RuntimeAdapter
    from cognitia.runtime.options_builder import ClaudeOptionsBuilder

# --- SDK 0.1.48 wrappers (optional: require claude extra) ---
QueryResult = None
create_mcp_server = None
mcp_tool = None
one_shot_query = None
stream_one_shot_query = None
with suppress(ImportError):
    from cognitia.runtime.sdk_query import (
        QueryResult,
        one_shot_query,
        stream_one_shot_query,
    )
    from cognitia.runtime.sdk_tools import create_mcp_server, mcp_tool

__all__ = [
    "DEFAULT_MODEL",
    "RUNTIME_CAPABILITY_FLAGS",
    "RUNTIME_ERROR_KINDS",
    "RUNTIME_EVENT_TYPES",
    "RUNTIME_TIERS",
    "VALID_FEATURE_MODES",
    "VALID_MODEL_NAMES",
    "VALID_RUNTIME_NAMES",
    "AgentRuntime",
    "BaseRuntimePort",
    "CapabilityRequirements",
    "ClaudeOptionsBuilder",
    "DeepAgentsRuntimePort",
    "FeatureMode",
    "Message",
    "ModelPolicy",
    "ModelRegistry",
    "QueryResult",
    "RuntimeAdapter",
    "RuntimeCapabilities",
    "RuntimeConfig",
    "RuntimeErrorData",
    "RuntimeEvent",
    "RuntimeFactory",
    "RuntimeTier",
    "StreamEvent",
    "ThinRuntimePort",
    "ToolSpec",
    "TurnMetrics",
    "convert_event",
    "create_mcp_server",
    "get_registry",
    "get_runtime_capabilities",
    "mcp_tool",
    "one_shot_query",
    "reset_registry",
    "resolve_model_name",
    "stream_one_shot_query",
]
