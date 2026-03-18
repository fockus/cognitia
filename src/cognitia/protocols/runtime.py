"""Runtime protocols -- runtime port (deprecated) and AgentRuntime re-export."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from typing import Any, Protocol


class RuntimePort(Protocol):
    """Port: runtime adapter for SDK (DIP instead of concrete RuntimeAdapter).

    .. deprecated::
        Use :class:`AgentRuntime` from ``cognitia.runtime.base`` for new code.
        RuntimePort is kept for backward compatibility with existing SessionManager.
    """

    @property
    def is_connected(self) -> bool: ...

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    def stream_reply(self, user_text: str) -> AsyncIterator[Any]: ...


# Re-export AgentRuntime v1 Protocol
# Defined in cognitia.runtime.base, but accessible via protocols too
with contextlib.suppress(ImportError):
    from cognitia.runtime.base import AgentRuntime  # noqa: F401
