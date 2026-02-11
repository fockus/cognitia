"""Типы данных для работы с памятью."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryMessage:
    """Сообщение из истории диалога."""

    role: str  # 'user' | 'assistant' | 'system'
    content: str
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class UserProfile:
    """Профиль пользователя с фактами."""

    user_id: str
    facts: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class GoalState:
    """Состояние цели пользователя."""

    goal_id: str
    title: str
    target_amount: int | None = None
    current_amount: int = 0
    phase: str = ""
    plan: dict[str, Any] | None = None
    is_main: bool = False


@dataclass
class PhaseState:
    """Состояние текущей фазы пользователя."""

    user_id: str
    phase: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ToolEvent:
    """Запись о вызове инструмента (§9.1 tool_events)."""

    topic_id: str
    tool_name: str
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    latency_ms: int = 0
