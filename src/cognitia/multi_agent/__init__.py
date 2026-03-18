"""Multi-agent coordination package.

Re-exports domain types for convenient access:
    from cognitia.multi_agent import AgentToolResult, TaskItem, TaskStatus
"""

from cognitia.multi_agent.task_types import (
    TaskFilter,
    TaskItem,
    TaskPriority,
    TaskStatus,
)
from cognitia.multi_agent.types import AgentToolResult

__all__ = [
    "AgentToolResult",
    "TaskFilter",
    "TaskItem",
    "TaskPriority",
    "TaskStatus",
]
