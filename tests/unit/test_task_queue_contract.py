"""Contract tests for TaskQueue Protocol (Phase 9B-MVP).

These tests validate the Protocol definition itself:
- runtime_checkable isinstance checks
- method count (ISP: exactly 5)
- works for ANY correct implementation
"""

from __future__ import annotations

import inspect

from cognitia.multi_agent.task_types import TaskFilter, TaskItem
from cognitia.protocols.multi_agent import TaskQueue


class _ValidTaskQueue:
    """Minimal valid implementation for contract testing."""

    async def put(self, item: TaskItem) -> None:
        pass

    async def get(self, filters: TaskFilter | None = None) -> TaskItem | None:
        return None

    async def complete(self, task_id: str) -> bool:
        return False

    async def cancel(self, task_id: str) -> bool:
        return False

    async def list_tasks(
        self, filters: TaskFilter | None = None
    ) -> list[TaskItem]:
        return []


class _InvalidTaskQueue:
    """Missing methods -- should NOT pass isinstance check."""

    async def put(self, item: TaskItem) -> None:
        pass


class TestTaskQueueProtocol:
    """Contract tests for TaskQueue Protocol."""

    def test_task_queue_is_runtime_checkable(self) -> None:
        assert isinstance(_ValidTaskQueue(), TaskQueue)

    def test_task_queue_invalid_impl_fails_isinstance(self) -> None:
        assert not isinstance(_InvalidTaskQueue(), TaskQueue)

    def test_task_queue_has_exactly_five_methods(self) -> None:
        methods = [
            name
            for name, _ in inspect.getmembers(
                TaskQueue, predicate=inspect.isfunction
            )
            if not name.startswith("_")
        ]
        assert len(methods) == 5

    def test_task_queue_method_names(self) -> None:
        expected = {"put", "get", "complete", "cancel", "list_tasks"}
        methods = {
            name
            for name, _ in inspect.getmembers(
                TaskQueue, predicate=inspect.isfunction
            )
            if not name.startswith("_")
        }
        assert methods == expected

    def test_task_queue_all_methods_are_async(self) -> None:
        for name in ("put", "get", "complete", "cancel", "list_tasks"):
            method = getattr(TaskQueue, name)
            assert inspect.iscoroutinefunction(method), (
                f"{name} must be async"
            )
