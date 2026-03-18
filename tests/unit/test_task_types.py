"""Unit tests for TaskQueue domain types (Phase 9B-MVP).

Contract tests: validate frozen dataclasses, enum values, defaults.
Must pass for ANY correct implementation of task_types.
"""

from __future__ import annotations

import dataclasses

import pytest

from cognitia.multi_agent.task_types import (
    TaskFilter,
    TaskItem,
    TaskPriority,
    TaskStatus,
)


class TestTaskStatus:
    """TaskStatus enum: exactly 4 str values."""

    def test_task_status_has_exactly_four_values(self) -> None:
        assert len(TaskStatus) == 4

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (TaskStatus.TODO, "todo"),
            (TaskStatus.IN_PROGRESS, "in_progress"),
            (TaskStatus.DONE, "done"),
            (TaskStatus.CANCELLED, "cancelled"),
        ],
    )
    def test_task_status_values(self, member: TaskStatus, value: str) -> None:
        assert member.value == value

    def test_task_status_is_str_enum(self) -> None:
        assert isinstance(TaskStatus.TODO, str)


class TestTaskPriority:
    """TaskPriority enum: exactly 4 str values, ordered semantically."""

    def test_task_priority_has_exactly_four_values(self) -> None:
        assert len(TaskPriority) == 4

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (TaskPriority.LOW, "low"),
            (TaskPriority.MEDIUM, "medium"),
            (TaskPriority.HIGH, "high"),
            (TaskPriority.CRITICAL, "critical"),
        ],
    )
    def test_task_priority_values(
        self, member: TaskPriority, value: str
    ) -> None:
        assert member.value == value

    def test_task_priority_is_str_enum(self) -> None:
        assert isinstance(TaskPriority.LOW, str)


class TestTaskItem:
    """TaskItem: frozen dataclass with 8 fields."""

    def test_task_item_is_frozen_raises_on_mutation(self) -> None:
        item = TaskItem(id="t1", title="Do stuff")
        with pytest.raises(dataclasses.FrozenInstanceError):
            item.title = "Changed"  # type: ignore[misc]

    def test_task_item_default_values(self) -> None:
        item = TaskItem(id="t1", title="Title")
        assert item.description == ""
        assert item.status == TaskStatus.TODO
        assert item.priority == TaskPriority.MEDIUM
        assert item.assignee_agent_id is None
        assert item.metadata == {}
        assert item.created_at == 0.0

    def test_task_item_has_exactly_eight_fields(self) -> None:
        fields = dataclasses.fields(TaskItem)
        assert len(fields) == 8

    def test_task_item_custom_values(self) -> None:
        item = TaskItem(
            id="t2",
            title="Deploy",
            description="Deploy to prod",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.CRITICAL,
            assignee_agent_id="agent-1",
            metadata={"env": "prod"},
            created_at=1234567890.0,
        )
        assert item.id == "t2"
        assert item.assignee_agent_id == "agent-1"
        assert item.metadata == {"env": "prod"}

    def test_task_item_metadata_default_not_shared(self) -> None:
        """Each TaskItem gets its own metadata dict (no mutable default sharing)."""
        a = TaskItem(id="a", title="A")
        b = TaskItem(id="b", title="B")
        assert a.metadata is not b.metadata


class TestTaskFilter:
    """TaskFilter: frozen dataclass, all fields optional."""

    def test_task_filter_is_frozen_raises_on_mutation(self) -> None:
        f = TaskFilter()
        with pytest.raises(dataclasses.FrozenInstanceError):
            f.status = TaskStatus.DONE  # type: ignore[misc]

    def test_task_filter_all_defaults_none(self) -> None:
        f = TaskFilter()
        assert f.status is None
        assert f.priority is None
        assert f.assignee_agent_id is None

    def test_task_filter_with_values(self) -> None:
        f = TaskFilter(
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee_agent_id="agent-x",
        )
        assert f.status == TaskStatus.TODO
        assert f.priority == TaskPriority.HIGH
        assert f.assignee_agent_id == "agent-x"
