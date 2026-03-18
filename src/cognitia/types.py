"""Базовые типы Cognitia — контракты из секции 17 архитектуры.

Содержит единые типы, используемые во всех модулях:
TurnContext, ContextPack, SkillSet.
"""

from __future__ import annotations

from dataclasses import dataclass

from cognitia.runtime.types import RuntimeEvent

__all__ = ["ContextPack", "RuntimeEvent", "SkillSet", "TurnContext"]


@dataclass(frozen=True)
class TurnContext:
    """Единый контекст turn'а — передаётся между модулями.

    Содержит всё необходимое для принятия решений:
    выбор модели, политика инструментов, сборка контекста.
    """

    user_id: str
    topic_id: str
    role_id: str
    model: str
    active_skill_ids: tuple[str, ...]


@dataclass(frozen=True)
class ContextPack:
    """Единица контекста с приоритетом и оценкой размера.

    Приоритеты (из секции 10.2 архитектуры):
    0 — Guardrails (никогда не отбрасывается)
    1 — Role instruction
    2 — Active goals
    3 — Phase
    4 — Tool hints
    5 — Memory recall
    6 — User profile
    """

    pack_id: str
    priority: int
    content: str
    tokens_estimate: int


@dataclass(frozen=True)
class SkillSet:
    """Именованный набор скилов (секция 5.1 архитектуры).

    Роль выбирает SkillSet → SkillSet определяет allowlist инструментов.
    """

    set_id: str
    skill_ids: tuple[str, ...] = ()
    local_tool_ids: tuple[str, ...] = ()
