"""Провайдер памяти — ISP-совместимые протоколы.

ISP из RULES.MD: каждый Protocol ≤5 методов.
Мелкие протоколы определены в cognitia.protocols.

Этот модуль реэкспортирует их для удобства импорта
и предоставляет тип-подсказку MemoryProvider для composition root.
"""

from __future__ import annotations

# ISP: все протоколы хранилища ≤5 методов.
# Каждый потребитель зависит только от нужного подмножества (ISP/DIP).
# Конкретные классы (PostgresMemoryProvider, InMemoryMemoryProvider)
# реализуют все протоколы, но это деталь реализации, не контракт.
from cognitia.protocols import (
    FactStore,
    GoalStore,
    MessageStore,
    PhaseStore,
    SessionStateStore,
    SummaryStore,
    ToolEventStore,
    UserStore,
)

__all__ = [
    "FactStore",
    "GoalStore",
    "MessageStore",
    "PhaseStore",
    "SessionStateStore",
    "SummaryStore",
    "ToolEventStore",
    "UserStore",
]
