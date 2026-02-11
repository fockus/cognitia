"""DeepAgentsRuntimePort — адаптер DeepAgentsRuntime под RuntimePort протокол.

Позволяет использовать DeepAgentsRuntime (LangChain) в SessionManager.
В отличие от ThinRuntimePort, передаёт реальные active_tools в runtime.

Наследует BaseRuntimePort (DRY: StreamEvent, convert_event, sliding window).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from cognitia.runtime.deepagents import DeepAgentsRuntime
from cognitia.runtime.ports.base import HISTORY_MAX, BaseRuntimePort
from cognitia.runtime.types import Message, RuntimeConfig, RuntimeEvent, ToolSpec

logger = logging.getLogger(__name__)


class DeepAgentsRuntimePort(BaseRuntimePort):
    """Адаптер DeepAgentsRuntime → RuntimePort.

    Реализует протокол RuntimePort (connect, disconnect, is_connected, stream_reply)
    поверх DeepAgentsRuntime, конвертируя RuntimeEvent → StreamEvent.

    В отличие от ThinRuntimePort:
    - Передаёт active_tools (реальные инструменты) в runtime.run()
    - Использует LangChain для вызова модели

    Args:
        system_prompt: System prompt для LLM.
        config: RuntimeConfig с моделью, budgets.
        active_tools: Список доступных инструментов (ToolSpec).
        tool_executors: Маппинг tool_name → async callable для local tools.
    """

    def __init__(
        self,
        system_prompt: str,
        config: RuntimeConfig | None = None,
        active_tools: list[ToolSpec] | None = None,
        tool_executors: dict[str, Callable] | None = None,
        summarizer: Any | None = None,
    ) -> None:
        super().__init__(
            system_prompt=system_prompt,
            config=config or RuntimeConfig(runtime_name="deepagents"),
            history_max=HISTORY_MAX,
            summarizer=summarizer,
        )
        self._active_tools = active_tools or []
        self._tool_executors = tool_executors or {}
        self._runtime: DeepAgentsRuntime | None = None

    async def connect(self) -> None:
        """Инициализировать DeepAgentsRuntime."""
        self._runtime = DeepAgentsRuntime(
            config=self._config,
            tool_executors=self._tool_executors,
        )
        self._connected = True
        logger.info(
            "DeepAgentsRuntimePort подключён: model=%s, tools=%d",
            self._config.model,
            len(self._active_tools),
        )

    async def disconnect(self) -> None:
        """Освободить ресурсы."""
        if self._runtime:
            await self._runtime.cleanup()
            self._runtime = None
        await super().disconnect()

    async def _run_runtime(
        self, messages: list[Message], system_prompt: str,
    ) -> AsyncIterator[RuntimeEvent]:
        """Вызвать DeepAgentsRuntime.run() с active_tools."""
        if not self._runtime:
            return
        async for event in self._runtime.run(
            messages=messages,
            system_prompt=system_prompt,
            active_tools=self._active_tools,
        ):
            yield event
