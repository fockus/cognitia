"""Тесты WorkflowExecutor — runtime adapters для WorkflowGraph.

CRP-4.2: thin executor, LangGraph compiler, mixed runtimes.
"""

from __future__ import annotations

from typing import Any

import pytest
from cognitia.orchestration.workflow_graph import WorkflowGraph


class TestWorkflowThinExecutor:
    """Workflow runs via ThinRuntimeExecutor per node."""

    async def test_workflow_thin_executor_executes_linear_graph(self) -> None:
        """ThinRuntimeExecutor выполняет линейный граф — все nodes вызываются."""
        from cognitia.orchestration.workflow_executor import ThinRuntimeExecutor

        async def step1(state: dict[str, Any]) -> dict[str, Any]:
            state.setdefault("execution_order", []).append("STEP1")
            return state

        async def step2(state: dict[str, Any]) -> dict[str, Any]:
            state.setdefault("execution_order", []).append("STEP2")
            return state

        wf = WorkflowGraph("thin-exec-test")
        wf.add_node("step1", step1)
        wf.add_node("step2", step2)
        wf.add_edge("step1", "step2")
        wf.set_entry("step1")

        executor = ThinRuntimeExecutor()
        result = await executor.run(wf, initial_state={})

        assert result["execution_order"] == ["STEP1", "STEP2"]

    async def test_workflow_thin_executor_propagates_state(self) -> None:
        """ThinRuntimeExecutor передаёт state между nodes — данные не теряются."""
        from cognitia.orchestration.workflow_executor import ThinRuntimeExecutor

        async def producer(state: dict[str, Any]) -> dict[str, Any]:
            state["payload"] = {"key": "value", "count": 42}
            return state

        async def consumer(state: dict[str, Any]) -> dict[str, Any]:
            payload = state.get("payload", {})
            state["consumed"] = payload.get("count", 0) * 2
            return state

        wf = WorkflowGraph("state-propagation")
        wf.add_node("producer", producer)
        wf.add_node("consumer", consumer)
        wf.add_edge("producer", "consumer")
        wf.set_entry("producer")

        executor = ThinRuntimeExecutor()
        result = await executor.run(wf, initial_state={})

        # Данные из producer дошли до consumer
        assert result["consumed"] == 84

    async def test_workflow_thin_executor_with_llm_call(self) -> None:
        """ThinWorkflowExecutor.run_node выполняет ThinRuntime per-node через llm_call."""
        import json

        from cognitia.orchestration.workflow_executor import ThinWorkflowExecutor

        llm_calls: list[str] = []

        async def mock_llm_call(messages, system_prompt, **kwargs):
            llm_calls.append(system_prompt)
            return json.dumps({"type": "final", "final_message": "node done"})

        executor = ThinWorkflowExecutor(llm_call=mock_llm_call)

        wf = WorkflowGraph("thin-llm-test")

        async def node_a(state: dict[str, Any]) -> dict[str, Any]:
            result = await executor.run_node("research agent", "Research topic X", state)
            state["research"] = result
            return state

        async def node_b(state: dict[str, Any]) -> dict[str, Any]:
            result = await executor.run_node("planner agent", "Make a plan", state)
            state["plan"] = result
            return state

        wf.add_node("research", node_a)
        wf.add_node("plan", node_b)
        wf.add_edge("research", "plan")
        wf.set_entry("research")

        result = await wf.execute({})

        # Оба nodes выполнились и записали результат
        assert "research" in result
        assert "plan" in result
        # llm_call вызывался дважды (по одному разу на каждый node)
        assert len(llm_calls) == 2


class TestWorkflowLangGraphCompile:
    """WorkflowGraph → LangGraph StateGraph compile."""

    def test_workflow_langgraph_compile_raises_import_error_if_not_installed(self) -> None:
        """compile_to_langgraph raises ImportError если langgraph не установлен."""
        from cognitia.orchestration.workflow_langgraph import compile_to_langgraph

        async def noop(state: dict[str, Any]) -> dict[str, Any]:
            return state

        wf = WorkflowGraph("lg-test")
        wf.add_node("a", noop)
        wf.add_node("b", noop)
        wf.add_edge("a", "b")
        wf.set_entry("a")

        # Если langgraph установлен — возвращает объект с invoke/ainvoke.
        # Если нет — поднимает ImportError с упоминанием langgraph.
        try:
            compiled = compile_to_langgraph(wf)
            assert hasattr(compiled, "invoke") or hasattr(compiled, "ainvoke")
        except ImportError as exc:
            assert "langgraph" in str(exc).lower()

    def test_workflow_langgraph_spec_has_correct_structure(self) -> None:
        """compile_to_langgraph_spec возвращает dict с nodes, edges, entry."""
        from cognitia.orchestration.workflow_executor import compile_to_langgraph_spec

        async def node_fn(state: dict[str, Any]) -> dict[str, Any]:
            return state

        wf = WorkflowGraph("spec-test")
        wf.add_node("start", node_fn)
        wf.add_node("end", node_fn)
        wf.add_edge("start", "end")
        wf.set_entry("start")

        spec = compile_to_langgraph_spec(wf)

        assert spec["entry"] == "start"
        assert "start" in spec["nodes"]
        assert "end" in spec["nodes"]
        assert ("start", "end") in spec["edges"]


class TestWorkflowMixedRuntimes:
    """Mixed runtimes: MixedRuntimeExecutor routing nodes по runtime_map."""

    async def test_workflow_mixed_runtimes_records_runtime_per_node(self) -> None:
        """MixedRuntimeExecutor записывает __runtime_executions__ в state для observability."""
        from cognitia.orchestration.workflow_executor import MixedRuntimeExecutor

        async def thin_node(state: dict[str, Any]) -> dict[str, Any]:
            state["thin_done"] = True
            return state

        async def deep_node(state: dict[str, Any]) -> dict[str, Any]:
            state["deep_done"] = True
            return state

        wf = WorkflowGraph("mixed-runtimes")
        wf.add_node("thin_step", thin_node)
        wf.add_node("deep_step", deep_node)
        wf.add_edge("thin_step", "deep_step")
        wf.set_entry("thin_step")

        executor = MixedRuntimeExecutor(
            runtime_map={
                "thin_step": "thin",
                "deep_step": "deepagents",
            }
        )
        result = await executor.run(wf, initial_state={})

        # Оба nodes выполнились
        assert result["thin_done"] is True
        assert result["deep_done"] is True
        # Метаданные о runtime routing записаны в state
        assert result["__runtime_executions__"]["thin_step"] == "thin"
        assert result["__runtime_executions__"]["deep_step"] == "deepagents"

    async def test_workflow_mixed_runtimes_unmapped_node_uses_thin_fallback(self) -> None:
        """Node без mapping в runtime_map выполняется с thin runtime (fallback)."""
        from cognitia.orchestration.workflow_executor import MixedRuntimeExecutor

        async def unmapped_node(state: dict[str, Any]) -> dict[str, Any]:
            state["unmapped_done"] = True
            return state

        wf = WorkflowGraph("fallback-test")
        wf.add_node("unmapped", unmapped_node)
        wf.set_entry("unmapped")

        # Пустой runtime_map — node "unmapped" не имеет назначенного runtime
        executor = MixedRuntimeExecutor(runtime_map={})
        result = await executor.run(wf, initial_state={})

        assert result["unmapped_done"] is True
        # Fallback runtime записывается как "thin"
        assert result["__runtime_executions__"]["unmapped"] == "thin"
