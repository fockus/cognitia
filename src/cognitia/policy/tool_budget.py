"""ToolBudget — лимит tool calls per turn (секция 6.3 архитектуры).

Контролирует стоимость и latency:
- max_tool_calls: общий лимит вызовов за turn (по умолчанию 8)
- max_mcp_calls: лимит MCP вызовов за turn (по умолчанию 6)
- timeout_per_call_ms: таймаут на один вызов MCP (по умолчанию 30с)
"""

from __future__ import annotations


class ToolBudget:
    """Счётчик и лимитер tool calls за один turn."""

    def __init__(
        self,
        max_tool_calls: int = 8,
        max_mcp_calls: int = 6,
        timeout_per_call_ms: int = 30_000,
    ) -> None:
        self._max_total = max_tool_calls
        self._max_mcp = max_mcp_calls
        self._timeout_ms = timeout_per_call_ms
        self._total: int = 0
        self._mcp: int = 0

    @property
    def total_calls(self) -> int:
        """Общее количество вызовов за turn."""
        return self._total

    @property
    def mcp_calls(self) -> int:
        """Количество MCP вызовов за turn."""
        return self._mcp

    def record_call(self, is_mcp: bool = False) -> None:
        """Зафиксировать вызов инструмента."""
        self._total += 1
        if is_mcp:
            self._mcp += 1

    def can_call(self, is_mcp: bool = False) -> bool:
        """Проверить, можно ли сделать ещё один вызов."""
        if self._total >= self._max_total:
            return False
        return not (is_mcp and self._mcp >= self._max_mcp)

    def is_exhausted(self) -> bool:
        """Полностью исчерпан ли бюджет (и MCP, и local невозможны)."""
        return self._total >= self._max_total

    @property
    def timeout_per_call_ms(self) -> int:
        """Таймаут на один вызов MCP в мс (§6.3)."""
        return self._timeout_ms

    def reset(self) -> None:
        """Сбросить счётчики (начало нового turn)."""
        self._total = 0
        self._mcp = 0
