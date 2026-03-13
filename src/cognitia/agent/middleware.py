"""Middleware — composable обработка запросов Agent facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cognitia.hooks.registry import HookRegistry

if TYPE_CHECKING:
    from cognitia.agent.config import AgentConfig
    from cognitia.agent.result import Result


class BudgetExceededError(RuntimeError):
    """Превышен бюджет (max_budget_usd)."""


class Middleware:
    """Базовый middleware для Agent facade.

    Все методы — default passthrough (переопределяйте нужные в подклассах).
    """

    async def before_query(self, prompt: str, config: AgentConfig) -> str:
        """Перед запросом. Можно модифицировать prompt. Raise → блокировать."""
        return prompt

    async def after_result(self, result: Result) -> Result:
        """После результата. Можно модифицировать/обогатить Result."""
        return result

    def get_hooks(self) -> HookRegistry | None:
        """Хуки для runtime (optional)."""
        return None


class CostTracker(Middleware):
    """Middleware: аккумуляция стоимости и контроль бюджета."""

    def __init__(self, budget_usd: float) -> None:
        self._budget_usd = budget_usd
        self._total_cost: float = 0.0

    @property
    def total_cost_usd(self) -> float:
        return self._total_cost

    def reset(self) -> None:
        self._total_cost = 0.0

    async def after_result(self, result: Result) -> Result:
        cost = result.total_cost_usd
        if cost is not None:
            self._total_cost += cost
            if self._total_cost > self._budget_usd:
                raise BudgetExceededError(
                    f"Бюджет превышен: ${self._total_cost:.4f} > ${self._budget_usd:.2f}"
                )
        return result


class SecurityGuard(Middleware):
    """Middleware: блокировка опасных паттернов в tool input через PreToolUse hook."""

    def __init__(self, block_patterns: list[str]) -> None:
        self._patterns = block_patterns

    def get_hooks(self) -> HookRegistry:
        registry = HookRegistry()
        registry.on_pre_tool_use(self._check_tool_input)
        return registry

    async def _check_tool_input(self, **kwargs: Any) -> dict[str, Any]:
        tool_input = kwargs.get("tool_input") or {}
        text = " ".join(str(v) for v in tool_input.values())

        for pattern in self._patterns:
            if pattern in text:
                return {
                    "decision": "block",
                    "reason": f"Blocked: pattern '{pattern}' found in tool input",
                }
        return {"continue_": True}
