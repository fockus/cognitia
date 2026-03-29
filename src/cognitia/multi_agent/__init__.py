"""Multi-agent coordination package.

Re-exports domain types for convenient access:
    from cognitia.multi_agent import AgentToolResult, TaskItem, AgentRecord
"""

from cognitia.multi_agent.agent_registry import InMemoryAgentRegistry
from cognitia.multi_agent.agent_tool import create_agent_tool_spec, execute_agent_tool
from cognitia.multi_agent.registry_types import AgentFilter, AgentRecord, AgentStatus
from cognitia.multi_agent.task_queue import InMemoryTaskQueue, SqliteTaskQueue
from cognitia.multi_agent.task_types import (
    TaskFilter,
    TaskItem,
    TaskPriority,
    TaskStatus,
)
from cognitia.multi_agent.graph_task_types import WorkflowConfig, WorkflowStage
from cognitia.multi_agent.types import AgentToolResult
from cognitia.multi_agent.workspace import ExecutionWorkspace, LocalWorkspace
from cognitia.multi_agent.workspace_types import (
    WorkspaceHandle,
    WorkspaceSpec,
    WorkspaceStrategy,
)

__all__ = [
    "InMemoryAgentRegistry",
    "InMemoryTaskQueue",
    "SqliteTaskQueue",
    "AgentFilter",
    "AgentRecord",
    "AgentStatus",
    "AgentToolResult",
    "TaskFilter",
    "TaskItem",
    "TaskPriority",
    "TaskStatus",
    "WorkflowConfig",
    "WorkflowStage",
    "create_agent_tool_spec",
    "execute_agent_tool",
    "ExecutionWorkspace",
    "LocalWorkspace",
    "WorkspaceHandle",
    "WorkspaceSpec",
    "WorkspaceStrategy",
]
