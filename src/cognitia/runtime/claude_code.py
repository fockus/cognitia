"""ClaudeCodeRuntime — обёртка claude-agent-sdk под AgentRuntime v1 контракт.

Ownership: runtime НЕ владеет историей. SDK управляет conversation
внутренне (warm handle), но канон — в SessionManager.

Логика:
1. Извлекает последнее user message из messages
2. Делегирует в существующий RuntimeAdapter.stream_reply(user_text)
3. Конвертирует StreamEvent → RuntimeEvent
4. Собирает full_text и формирует new_messages в final event
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from cognitia.runtime.types import (
    Message,
    RuntimeConfig,
    RuntimeErrorData,
    RuntimeEvent,
    ToolSpec,
    TurnMetrics,
)

logger = logging.getLogger(__name__)


class ClaudeCodeRuntime:
    """AgentRuntime обёртка над claude-agent-sdk.

    Использует существующий RuntimeAdapter для связи с SDK.
    SDK управляет своей историей внутренне (warm subprocess handle).
    """

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        adapter: Any = None,
    ) -> None:
        """Инициализировать runtime.

        Args:
            config: Конфигурация runtime (используется model и budgets).
            adapter: Существующий RuntimeAdapter (DIP: передаётся извне).
                     Если None — создаётся при первом использовании.
        """
        self._config = config or RuntimeConfig(runtime_name="claude_sdk")
        self._adapter = adapter

    @property
    def adapter(self) -> Any:
        """Доступ к underlying RuntimeAdapter."""
        return self._adapter

    @adapter.setter
    def adapter(self, value: Any) -> None:
        self._adapter = value

    async def run(
        self,
        *,
        messages: list[Message],
        system_prompt: str,
        active_tools: list[ToolSpec],
        config: RuntimeConfig | None = None,
        mode_hint: str | None = None,
    ) -> AsyncIterator[RuntimeEvent]:
        """Выполнить один turn через claude-agent-sdk.

        Извлекает последнее user message, делегирует в SDK,
        конвертирует StreamEvent → RuntimeEvent.
        """
        logger.info(
            "ClaudeCodeRuntime.run(): начало (adapter=%s)",
            type(self._adapter).__name__ if self._adapter else "None",
        )

        if self._adapter is None:
            logger.error("ClaudeCodeRuntime.run(): adapter is None")
            yield RuntimeEvent.error(
                RuntimeErrorData(
                    kind="runtime_crash",
                    message="RuntimeAdapter не инициализирован. Создайте сессию через SessionFactory.",
                    recoverable=False,
                )
            )
            return

        logger.info("ClaudeCodeRuntime.run(): is_connected=%s", self._adapter.is_connected)
        if not self._adapter.is_connected:
            yield RuntimeEvent.error(
                RuntimeErrorData(
                    kind="runtime_crash",
                    message="SDK клиент не подключён.",
                    recoverable=False,
                )
            )
            return

        # Извлекаем последнее user message
        user_text = self._extract_last_user_text(messages)
        if not user_text:
            logger.error("ClaudeCodeRuntime.run(): нет user message в messages")
            yield RuntimeEvent.error(
                RuntimeErrorData(
                    kind="runtime_crash",
                    message="Нет user message в messages.",
                    recoverable=False,
                )
            )
            return

        logger.info("ClaudeCodeRuntime.run(): передаю в adapter.stream_reply(%r)", user_text[:50])

        # Стримим через SDK
        full_text = ""
        tool_calls_count = 0
        new_messages: list[Message] = []
        result_meta: dict[str, Any] = {}

        try:
            async for stream_event in self._adapter.stream_reply(user_text):
                runtime_event = self._convert_event(stream_event)
                if runtime_event is not None:
                    if runtime_event.type == "error":
                        yield runtime_event
                        return

                    # Собираем текст
                    if runtime_event.type == "assistant_delta":
                        full_text += runtime_event.data.get("text", "")
                    elif runtime_event.type == "tool_call_started":
                        tool_calls_count += 1

                    # Не пробрасываем done — мы сами сформируем final
                    if stream_event.type != "done":
                        yield runtime_event
                if stream_event.type == "done":
                    result_meta = {
                        "session_id": getattr(stream_event, "session_id", None),
                        "total_cost_usd": getattr(stream_event, "total_cost_usd", None),
                        "usage": getattr(stream_event, "usage", None),
                        "structured_output": getattr(stream_event, "structured_output", None),
                    }
        except Exception as e:
            logger.exception("ClaudeCodeRuntime.run(): ошибка стриминга")
            yield RuntimeEvent.error(
                RuntimeErrorData(
                    kind="runtime_crash",
                    message=f"Ошибка SDK стриминга: {e}",
                    recoverable=False,
                )
            )
            return

        # Формируем new_messages
        if full_text:
            new_messages.append(
                Message(
                    role="assistant",
                    content=full_text,
                )
            )

        # Финальное событие
        metrics = TurnMetrics(
            tool_calls_count=tool_calls_count,
            model=self._config.model,
        )
        yield RuntimeEvent.final(
            text=full_text,
            new_messages=new_messages,
            metrics=metrics,
            session_id=result_meta.get("session_id"),
            total_cost_usd=result_meta.get("total_cost_usd"),
            usage=result_meta.get("usage"),
            structured_output=result_meta.get("structured_output"),
        )

    async def cleanup(self) -> None:
        """Отключить SDK adapter."""
        if self._adapter and self._adapter.is_connected:
            await self._adapter.disconnect()

    @staticmethod
    def _extract_last_user_text(messages: list[Message]) -> str:
        """Извлечь текст последнего user message."""
        for msg in reversed(messages):
            if msg.role == "user" and msg.content:
                return msg.content
        return ""

    @staticmethod
    def _convert_event(stream_event: Any) -> RuntimeEvent | None:
        """Конвертировать StreamEvent → RuntimeEvent.

        Маппинг:
        - text_delta → assistant_delta
        - tool_use_start → tool_call_started
        - tool_use_result → tool_call_finished
        - error → error
        - done → None (формируем final сами)
        """
        etype = stream_event.type

        if etype == "text_delta":
            return RuntimeEvent.assistant_delta(stream_event.text)

        if etype == "tool_use_start":
            return RuntimeEvent.tool_call_started(
                name=stream_event.tool_name,
                args=stream_event.tool_input,
                correlation_id=stream_event.correlation_id or None,
            )

        if etype == "tool_use_result":
            return RuntimeEvent.tool_call_finished(
                name=stream_event.tool_name or "",
                correlation_id=stream_event.correlation_id or "",
                ok=not bool(getattr(stream_event, "tool_error", False)),
                result_summary=stream_event.tool_result,
            )

        if etype == "error":
            return RuntimeEvent.error(
                RuntimeErrorData(
                    kind="runtime_crash",
                    message=stream_event.text,
                    recoverable=False,
                )
            )

        if etype == "done":
            return None  # Формируем final сами

        # Неизвестный тип — status
        return RuntimeEvent.status(stream_event.text or etype)
