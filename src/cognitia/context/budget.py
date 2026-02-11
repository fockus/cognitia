"""ContextBudget — управление размером контекстных пакетов."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBudget:
    """Бюджет токенов для контекстных пакетов.

    Приоритет (от высшего к низшему):
    P0: guardrails   — никогда не отбрасывается
    P1: active_goal  — truncate до goal_max если нужно
    P2: tool hints   — оставляем только для активных skills
    P3: memory recall — уменьшаем top-k
    P4: user_profile  — truncate до ключевых фактов
    P5: summary       — отбрасывается первым
    """

    total_tokens: int = 8000
    guardrails_reserved: int = 1500  # P0: всегда зарезервировано
    goal_max: int = 1000  # P1
    tools_max: int = 2000  # P2
    messages_max: int = 2000  # P2.5: последние сообщения диалога
    memory_max: int = 1500  # P3
    profile_max: int = 1000  # P4
    summary_max: int = 1000  # P5


def estimate_tokens(text: str) -> int:
    """Грубая оценка количества токенов (1 токен ~ 4 символа для русского/англ.)."""
    return len(text) // 4 + 1


def truncate_to_budget(text: str, max_tokens: int) -> str:
    """Обрезать текст до max_tokens (приблизительно)."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [обрезано]"
