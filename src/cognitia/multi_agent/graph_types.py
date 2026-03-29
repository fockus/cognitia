"""Agent graph domain types — nodes, edges, snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cognitia.multi_agent.registry_types import AgentStatus


class EdgeType(str, Enum):
    """Type of relationship between agent nodes."""

    REPORTS_TO = "reports_to"
    COLLABORATES = "collaborates"


@dataclass(frozen=True)
class AgentNode:
    """A node in the agent graph — an agent with identity, capabilities, and position."""

    id: str
    name: str
    role: str
    system_prompt: str = ""
    parent_id: str | None = None
    allowed_tools: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    runtime_config: dict[str, Any] | None = None  # None = inherit from parent
    budget_limit_usd: float | None = None
    status: AgentStatus = AgentStatus.IDLE
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    """A directed edge between two agent nodes."""

    source_id: str
    target_id: str
    edge_type: EdgeType = EdgeType.REPORTS_TO


@dataclass(frozen=True)
class GraphSnapshot:
    """Immutable snapshot of the entire agent graph."""

    nodes: tuple[AgentNode, ...]
    edges: tuple[GraphEdge, ...]
    root_id: str | None = None
