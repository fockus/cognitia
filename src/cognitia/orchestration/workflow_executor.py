"""Workflow executors — runtime adapters для WorkflowGraph.

ThinWorkflowExecutor: запускает ThinRuntime per-node.
ThinRuntimeExecutor: выполняет workflow nodes напрямую (без LLM).
MixedRuntimeExecutor: routing nodes по runtime_map.
compile_to_langgraph_spec: структурная компиляция в LangGraph-совместимый spec.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from cognitia.orchestration.runtime_helpers import collect_runtime_output
from cognitia.orchestration.workflow_graph import State, WorkflowGraph
from cognitia.runtime.thin.runtime import ThinRuntime
from cognitia.runtime.types import Message, RuntimeConfig, ToolSpec


class ThinWorkflowExecutor:
    """Запускает ThinRuntime per-node для workflow execution."""

    def __init__(
        self,
        *,
        llm_call: Callable[..., Any],
        local_tools: dict[str, Callable[..., Any]] | None = None,
        mcp_servers: dict[str, Any] | None = None,
        runtime_config: RuntimeConfig | None = None,
    ) -> None:
        self._llm_call = llm_call
        self._local_tools = local_tools or {}
        self._mcp_servers = mcp_servers
        self._runtime_config = runtime_config or RuntimeConfig(runtime_name="thin")

    async def run_node(
        self,
        system_prompt: str,
        task: str,
        state: dict[str, Any],
    ) -> str:
        """Выполнить один node через ThinRuntime. Возвращает финальный текст."""
        runtime = ThinRuntime(
            config=self._runtime_config,
            llm_call=self._llm_call,
            local_tools=self._local_tools,
            mcp_servers=self._mcp_servers,
        )
        return await collect_runtime_output(
            runtime.run(
                messages=[Message(role="user", content=task)],
                system_prompt=system_prompt,
                active_tools=_build_active_tools(self._local_tools),
                mode_hint="react",
            ),
        )


class ThinRuntimeExecutor:
    """Выполняет WorkflowGraph nodes напрямую через node functions.

    Thin runtime: node functions вызываются как есть, без LLM overhead.
    Используется когда nodes — Python functions, а не LLM prompts.
    """

    async def run(self, wf: WorkflowGraph, initial_state: State) -> State:
        """Выполнить граф, вызывая node functions напрямую."""
        return await wf.execute(initial_state)


class MixedRuntimeExecutor:
    """Выполняет WorkflowGraph с observability metadata по runtime_map.

    Executor не маршрутизирует выполнение между runtime'ами: он исполняет nodes
    обычным механизмом WorkflowGraph и только записывает, какой runtime был
    ассоциирован с node_id для observability.
    """

    def __init__(self, runtime_map: dict[str, str]) -> None:
        self._runtime_map = runtime_map

    async def run(self, wf: WorkflowGraph, initial_state: State) -> State:
        """Выполнить граф с observability metadata per node.

        Uses WorkflowGraph.execute(node_interceptor=...) to wrap each node
        execution and record runtime metadata without changing dispatch.
        """

        async def _observability_interceptor(node_id: str, state: State) -> State:
            runtime_name = self._runtime_map.get(node_id, "thin")
            # Execute node via the graph's default mechanism (no interceptor recursion).
            # This executor only records metadata; it does not route execution.
            state = await wf._execute_node(node_id, state)
            # Record which runtime was associated with this node (for observability).
            executions: dict[str, str] = state.get("__runtime_executions__", {})
            executions[node_id] = runtime_name
            state["__runtime_executions__"] = executions
            return state

        return await wf.execute(initial_state, node_interceptor=_observability_interceptor)


def _build_active_tools(local_tools: dict[str, Callable[..., Any]]) -> list[ToolSpec]:
    """Build ToolSpec list for local tools so runtimes can advertise them."""
    active_tools: list[ToolSpec] = []
    for tool_name, tool in local_tools.items():
        tool_definition = getattr(tool, "__tool_definition__", None)
        if tool_definition is not None:
            active_tools.append(tool_definition.to_tool_spec())
            continue

        description = ""
        doc = inspect.getdoc(tool)
        if doc:
            description = doc.strip().split("\n")[0].strip()

        active_tools.append(
            ToolSpec(
                name=tool_name,
                description=description,
                parameters={},
                is_local=True,
            ),
        )

    return active_tools


def compile_to_langgraph_spec(wf: WorkflowGraph) -> dict[str, Any]:
    """Компилировать WorkflowGraph в LangGraph-совместимый spec.

    Возвращает dict с nodes, edges, entry — достаточно для
    конструирования LangGraph StateGraph (zero overhead pass-through).
    """
    nodes: dict[str, Any] = {}
    for node_id, node_fn in wf._nodes.items():
        nodes[node_id] = node_fn

    edges: list[tuple[str, str]] = []
    for edge in wf._edges:
        edges.append((edge.source, edge.target))

    conditional_edges: dict[str, Any] = {}
    for node_id, cond_edge in wf._conditional_edges.items():
        conditional_edges[node_id] = cond_edge.condition

    return {
        "name": wf.name,
        "entry": wf._entry,
        "nodes": nodes,
        "edges": edges,
        "conditional_edges": conditional_edges,
    }
