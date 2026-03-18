"""AgentRuntime — базовый протокол для всех runtime (v1 контракт).

Runtime НЕ владеет историей: получает messages каждый turn,
возвращает new_messages через финальный RuntimeEvent.

Контракт ownership:
- Вход: messages (от SessionManager/ContextBuilder)
- Выход: AsyncIterator[RuntimeEvent] (стрим) + new_messages в final event
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from cognitia.runtime.types import (
    Message,
    RuntimeConfig,
    RuntimeEvent,
    ToolSpec,
)


@runtime_checkable
class AgentRuntime(Protocol):
    """Единый контракт для всех runtime.

    Реализации:
    - ClaudeCodeRuntime: обёртка над claude-agent-sdk
    - DeepAgentsRuntime: LangChain Deep Agents (optional)
    - ThinRuntime: собственный тонкий агентный loop

    Использование:
        async for event in runtime.run(
            messages=[...], system_prompt="...", active_tools=[...],
        ):
            handle(event)
    """

    def run(
        self,
        *,
        messages: list[Message],
        system_prompt: str,
        active_tools: list[ToolSpec],
        config: RuntimeConfig | None = None,
        mode_hint: str | None = None,
    ) -> AsyncIterator[RuntimeEvent]:
        """Выполнить один turn.

        Реализации — async generators (``async def run(...) → yield``),
        поэтому Protocol декларирует ``def`` возвращающий ``AsyncIterator``
        (иначе mypy интерпретирует как Coroutine, что не совпадает).

        Args:
            messages: История диалога (каноническая, от SessionManager).
            system_prompt: Собранный system prompt (от ContextBuilder).
            active_tools: Разрешённые инструменты (после ToolPolicy).
            config: Конфигурация runtime (budgets, model, etc.).
            mode_hint: Подсказка режима для ThinRuntime (conversational/react/planner).

        Yields:
            RuntimeEvent: события стриминга.
            Финализация: обязательно final или error.
            tool_call_started всегда парный tool_call_finished.
        """
        ...  # pragma: no cover

    async def cleanup(self) -> None:
        """Освободить ресурсы runtime (connections, subprocess, etc.)."""
        ...  # pragma: no cover

    def cancel(self) -> None:
        """Request cooperative cancellation of the current operation."""
        ...  # pragma: no cover

    async def __aenter__(self) -> AgentRuntime:
        """Enter async context manager."""
        return self  # pragma: no cover

    async def __aexit__(self, *exc: Any) -> None:
        """Exit async context manager — calls cleanup()."""
        await self.cleanup()  # pragma: no cover
