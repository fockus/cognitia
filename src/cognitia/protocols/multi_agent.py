"""Multi-agent protocols -- agent-as-tool contract.

ISP-compliant: AgentTool has exactly 1 method.
Dependencies: only cognitia.runtime.types (ToolSpec).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cognitia.runtime.types import ToolSpec


@runtime_checkable
class AgentTool(Protocol):
    """Port: agent exposable as a tool for other agents.

    Any runtime or agent wrapper implementing this Protocol
    can be used as a sub-agent tool in another agent's tool list.
    """

    def as_tool(self, name: str, description: str) -> ToolSpec: ...
