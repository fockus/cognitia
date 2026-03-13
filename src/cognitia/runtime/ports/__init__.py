"""Runtime Ports — адаптеры AgentRuntime → RuntimePort (stream_reply).

Ports оборачивают низкоуровневые AgentRuntime реализации в унифицированный
интерфейс RuntimePort с управлением историей, summarization и streaming.
"""

from contextlib import suppress

from cognitia.runtime.ports.base import (
    HISTORY_MAX,
    BaseRuntimePort,
    StreamEvent,
    convert_event,
)

# DeepAgentsRuntimePort requires langchain (optional dep)
DeepAgentsRuntimePort = None
with suppress(ImportError):
    from cognitia.runtime.ports.deepagents import DeepAgentsRuntimePort

# ThinRuntimePort requires anthropic + httpx (optional dep)
ThinRuntimePort = None
with suppress(ImportError):
    from cognitia.runtime.ports.thin import ThinRuntimePort

__all__ = [
    "HISTORY_MAX",
    "BaseRuntimePort",
    "DeepAgentsRuntimePort",
    "StreamEvent",
    "ThinRuntimePort",
    "convert_event",
]
