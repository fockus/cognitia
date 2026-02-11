"""Тесты для ToolBudget (секция 6.3 архитектуры).

Лимиты: max_tool_calls=8, max_mcp_calls=6 per turn.
"""

import pytest

from cognitia.policy.tool_budget import ToolBudget


class TestToolBudget:
    """ToolBudget — счётчик вызовов инструментов за turn."""

    def test_initial_state(self) -> None:
        """Начальное состояние — 0 вызовов, бюджет не исчерпан."""
        budget = ToolBudget(max_tool_calls=8, max_mcp_calls=6)
        assert budget.total_calls == 0
        assert budget.mcp_calls == 0
        assert budget.is_exhausted() is False

    def test_record_local_tool(self) -> None:
        """Локальный вызов увеличивает total, но не mcp."""
        budget = ToolBudget(max_tool_calls=8, max_mcp_calls=6)
        budget.record_call(is_mcp=False)
        assert budget.total_calls == 1
        assert budget.mcp_calls == 0

    def test_record_mcp_tool(self) -> None:
        """MCP вызов увеличивает и total, и mcp."""
        budget = ToolBudget(max_tool_calls=8, max_mcp_calls=6)
        budget.record_call(is_mcp=True)
        assert budget.total_calls == 1
        assert budget.mcp_calls == 1

    def test_total_limit_exhausted(self) -> None:
        """Лимит 8: после 7 вызовов — ещё можно, после 8 — exhausted."""
        budget = ToolBudget(max_tool_calls=8, max_mcp_calls=6)
        for _ in range(7):
            budget.record_call(is_mcp=False)
        assert budget.is_exhausted() is False  # 7 из 8 — ОК
        assert budget.can_call(is_mcp=False) is True
        budget.record_call(is_mcp=False)  # 8-й
        assert budget.is_exhausted() is True
        assert budget.can_call(is_mcp=False) is False  # 9-й — нет

    def test_mcp_limit_exhausted(self) -> None:
        """7-й MCP вызов → mcp exhausted (но total ещё нет)."""
        budget = ToolBudget(max_tool_calls=8, max_mcp_calls=6)
        for _ in range(6):
            budget.record_call(is_mcp=True)
        assert budget.can_call(is_mcp=True) is False
        # Но локальный ещё можно
        assert budget.can_call(is_mcp=False) is True

    def test_can_call_before_limit(self) -> None:
        """До лимита can_call=True."""
        budget = ToolBudget(max_tool_calls=8, max_mcp_calls=6)
        budget.record_call(is_mcp=True)
        assert budget.can_call(is_mcp=True) is True
        assert budget.can_call(is_mcp=False) is True

    def test_reset(self) -> None:
        """reset() обнуляет счётчики."""
        budget = ToolBudget(max_tool_calls=8, max_mcp_calls=6)
        for _ in range(5):
            budget.record_call(is_mcp=True)
        budget.reset()
        assert budget.total_calls == 0
        assert budget.mcp_calls == 0

    def test_timeout_default(self) -> None:
        """Дефолтный timeout 30s (GAP-3, §6.3)."""
        budget = ToolBudget()
        assert budget.timeout_per_call_ms == 30_000

    def test_timeout_custom(self) -> None:
        """Кастомный timeout."""
        budget = ToolBudget(timeout_per_call_ms=10_000)
        assert budget.timeout_per_call_ms == 10_000
