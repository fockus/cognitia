"""BaseRuntimePort — базовый класс для runtime-адаптеров (DRY).

Извлекает общую логику ThinRuntimePort и DeepAgentsRuntimePort:
- StreamEvent dataclass
- convert_event (RuntimeEvent → StreamEvent)
- Sliding window для _history + auto-summarization
- connect / disconnect / is_connected
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from cognitia.runtime.types import Message, RuntimeConfig, RuntimeEvent

logger = logging.getLogger(__name__)

HISTORY_MAX = 20
"""Максимальное количество сообщений в in-memory истории runtime-адаптеров."""


@dataclass
class StreamEvent:
    """Унифицированное событие потока (совместимо с RuntimeAdapter.StreamEvent)."""

    type: str  # 'text_delta' | 'tool_use_start' | 'tool_use_result' | 'done' | 'error'
    text: str = ""
    tool_name: str = ""
    tool_input: dict[str, Any] | None = None
    tool_result: str = ""
    allowed_decisions: list[str] | None = None
    interrupt_id: str | None = None
    native_metadata: dict[str, Any] | None = None
    is_final: bool = False


def convert_event(event: RuntimeEvent) -> StreamEvent | None:
    """Конвертировать RuntimeEvent → StreamEvent (общая логика для всех адаптеров)."""
    if event.type == "assistant_delta":
        return StreamEvent(type="text_delta", text=str(event.data.get("text", "")))

    if event.type == "status":
        return None

    if event.type == "tool_call_started":
        return StreamEvent(
            type="tool_use_start",
            tool_name=str(event.data.get("name", "")),
            tool_input=event.data.get("args"),
        )

    if event.type == "tool_call_finished":
        return StreamEvent(
            type="tool_use_result",
            tool_result=str(event.data.get("result_summary", "")),
        )

    if event.type == "approval_required":
        return StreamEvent(
            type="approval_required",
            text=str(event.data.get("description", "")),
            tool_name=str(event.data.get("action_name", "")),
            tool_input=event.data.get("args"),
            allowed_decisions=event.data.get("allowed_decisions"),
            interrupt_id=event.data.get("interrupt_id"),
        )

    if event.type == "user_input_requested":
        return StreamEvent(
            type="user_input_requested",
            text=str(event.data.get("prompt", "")),
            interrupt_id=event.data.get("interrupt_id"),
        )

    if event.type == "native_notice":
        return StreamEvent(
            type="native_notice",
            text=str(event.data.get("text", "")),
            native_metadata=event.data.get("metadata"),
        )

    if event.type == "error":
        return StreamEvent(
            type="error",
            text=str(event.data.get("message", "Неизвестная ошибка runtime")),
        )

    if event.type == "final":
        # Final обрабатывается в stream_reply для корректного fallback.
        return None

    return None


class BaseRuntimePort:
    """Базовый класс для runtime-адаптеров с общей логикой.

    Предоставляет:
    - is_connected / connect / disconnect шаблон
    - Управление in-memory историей со sliding window
    - Auto-summarization при overflow (если summarizer задан)
    - stream_reply шаблон с конвертацией событий
    """

    def __init__(
        self,
        system_prompt: str,
        config: RuntimeConfig | None = None,
        history_max: int = HISTORY_MAX,
        summarizer: Any | None = None,
    ) -> None:
        self._system_prompt = system_prompt
        self._config = config or RuntimeConfig(runtime_name="thin")
        self._connected = False
        self._history: list[Message] = []
        self._history_max = history_max
        self._summarizer = summarizer  # LlmSummaryGenerator или None
        self._rolling_summary: str = ""

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Инициализировать runtime. Переопределяется в подклассах."""
        self._connected = True

    async def disconnect(self) -> None:
        """Освободить ресурсы. Переопределяется в подклассах."""
        self._connected = False
        self._history.clear()

    def _append_to_history(self, role: str, content: str) -> None:
        """Добавить сообщение в историю с sliding window."""
        self._history.append(Message(role=role, content=content))
        if len(self._history) > self._history_max:
            self._history = self._history[-self._history_max :]

    async def _maybe_summarize(self) -> None:
        """Auto-summarize: если history > cap и есть summarizer — обновить rolling_summary."""
        if not self._summarizer or len(self._history) < self._history_max:
            return

        from cognitia.memory.types import MemoryMessage

        # Конвертируем Message → MemoryMessage для summarizer
        mem_messages = [MemoryMessage(role=msg.role, content=msg.content) for msg in self._history]

        try:
            if hasattr(self._summarizer, "asummarize"):
                self._rolling_summary = await self._summarizer.asummarize(mem_messages)
            else:
                self._rolling_summary = self._summarizer.summarize(mem_messages)
        except Exception:
            logger.warning("Ошибка auto-summarization", exc_info=True)

    def _build_system_prompt(self) -> str:
        """Собрать system_prompt с rolling summary (если есть)."""
        if not self._rolling_summary:
            return self._system_prompt
        return f"{self._system_prompt}\n\n## Краткое содержание предыдущего диалога\n{self._rolling_summary}"

    async def _run_runtime(
        self,
        messages: list[Message],
        system_prompt: str,
    ) -> AsyncIterator[RuntimeEvent]:
        """Вызвать runtime. Переопределяется в подклассах."""
        raise NotImplementedError  # pragma: no cover
        yield  # pragma: no cover

    async def stream_reply(self, user_text: str) -> AsyncIterator[StreamEvent]:
        """Отправить сообщение и стримить ответ.

        Общий шаблон:
        1. Добавить user message в историю
        2. Вызвать _run_runtime()
        3. Конвертировать RuntimeEvent → StreamEvent
        4. Добавить assistant message в историю
        5. Yield done event
        """
        if not self._connected:
            yield StreamEvent(type="error", text="Runtime не подключён")
            return

        self._append_to_history("user", user_text)

        # Auto-summarize перед запуском runtime (если history подходит к лимиту)
        await self._maybe_summarize()

        full_text = ""
        final_text = ""  # текст из final event (fallback если нет assistant_delta)

        try:
            async for event in self._run_runtime(
                messages=list(self._history),
                system_prompt=self._build_system_prompt(),
            ):
                # Запоминаем текст из final для fallback
                if event.type == "final":
                    final_text = str(event.data.get("text", ""))
                    continue

                stream_event = convert_event(event)
                if stream_event:
                    if stream_event.type == "text_delta":
                        full_text += stream_event.text
                    yield stream_event

        except Exception as e:
            error_msg = f"Ошибка runtime: {type(e).__name__}: {e}"
            logger.error(error_msg, exc_info=True)
            yield StreamEvent(type="error", text=error_msg)
            return

        # Fallback: если assistant_delta не пришёл, берём текст из final
        if not full_text and final_text:
            full_text = final_text
            yield StreamEvent(type="text_delta", text=full_text)

        if full_text:
            self._append_to_history("assistant", full_text)

        yield StreamEvent(type="done", text=full_text, is_final=True)
