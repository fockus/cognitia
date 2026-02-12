"""SDK Adapter — обёртка над ClaudeSDKClient для унифицированного stream_reply.

Ключевой контракт:
- connect() запускает subprocess ОДИН раз (с таймаутом).
- stream_reply() использует receive_response() (не receive_messages()!),
  чтобы subprocess оставался живым между запросами.
- При падении subprocess — автоматический reconnect.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    Message,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """Унифицированное событие потока для CLI/Telegram."""

    type: str  # 'text_delta' | 'tool_use_start' | 'tool_use_result' | 'done' | 'error'
    text: str = ""
    tool_name: str = ""
    tool_input: dict[str, Any] | None = None
    tool_result: str = ""
    is_final: bool = False


class RuntimeAdapter:
    """Адаптер для работы с Claude Agent SDK.

    Управляет жизненным циклом ClaudeSDKClient и предоставляет
    унифицированный streaming интерфейс.

    ВАЖНО: используем receive_response() вместо receive_messages().
    receive_messages() дренажит весь stdout до завершения subprocess,
    после чего subprocess мёртв и следующий query() даёт BrokenPipeError.
    receive_response() останавливается на ResultMessage, сохраняя
    subprocess живым для следующих запросов.
    """

    # Таймаут на подключение subprocess (включая инициализацию MCP серверов).
    CONNECT_TIMEOUT_SECONDS = 60.0

    def __init__(self, options: ClaudeAgentOptions) -> None:
        self._options = options
        self._client: ClaudeSDKClient | None = None

    async def connect(self) -> None:
        """Подключиться к SDK (запустить subprocess).

        Raises:
            TimeoutError: если subprocess не инициализировался за CONNECT_TIMEOUT_SECONDS.
            Exception: любая ошибка при подключении.
        """
        from dataclasses import replace

        # Добавляем stderr callback для диагностики (если не задан явно)
        if self._options.stderr is None:
            self._options = replace(self._options, stderr=self._on_stderr)

        t0 = time.monotonic()
        self._client = ClaudeSDKClient(options=self._options)
        try:
            await asyncio.wait_for(
                self._client.connect(),
                timeout=self.CONNECT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - t0
            logger.error(
                "Таймаут подключения Claude SDK (%.1fs > %.1fs). "
                "Возможно, MCP серверы недоступны или медленно инициализируются.",
                elapsed, self.CONNECT_TIMEOUT_SECONDS,
            )
            # Убиваем зависший subprocess
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
            raise TimeoutError(
                f"Claude SDK subprocess не инициализировался за {self.CONNECT_TIMEOUT_SECONDS}s"
            ) from None

        elapsed = time.monotonic() - t0
        logger.info("Claude SDK subprocess запущен за %.2fs", elapsed)

    async def _reconnect(self) -> None:
        """Переподключиться при падении subprocess."""
        logger.warning("Переподключение Claude SDK subprocess...")
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None

        t0 = time.monotonic()
        self._client = ClaudeSDKClient(options=self._options)
        try:
            await asyncio.wait_for(
                self._client.connect(),
                timeout=self.CONNECT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - t0
            logger.error("Таймаут reconnect (%.1fs)", elapsed)
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
            raise TimeoutError("Claude SDK reconnect timeout") from None

        elapsed = time.monotonic() - t0
        logger.info("Claude SDK subprocess переподключён за %.2fs", elapsed)

    async def disconnect(self) -> None:
        """Отключиться от SDK."""
        if self._client:
            await self._client.disconnect()
            self._client = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    async def stream_reply(self, user_text: str) -> AsyncIterator[StreamEvent]:
        """Отправить сообщение и стримить ответ.

        Использует receive_response() — останавливается на ResultMessage,
        сохраняя subprocess живым для следующих запросов.
        При BrokenPipeError / ConnectionError — автоматический reconnect и повтор.

        Yields:
            StreamEvent — унифицированные события для адаптеров интерфейсов.
        """
        if not self._client:
            yield StreamEvent(type="error", text="SDK клиент не подключён")
            return

        # Попытка отправить query; при BrokenPipe — reconnect + retry (1 раз).
        logger.info("stream_reply: отправка query (len=%d)", len(user_text))
        for attempt in range(2):
            try:
                await self._client.query(user_text)
                logger.info("stream_reply: query отправлен")
                break
            except (BrokenPipeError, OSError, ConnectionError) as exc:
                if attempt == 0:
                    logger.warning(
                        "BrokenPipe при query (attempt=%d): %s. Reconnect...",
                        attempt, exc,
                    )
                    await self._reconnect()
                else:
                    logger.error("BrokenPipe при query после reconnect: %s", exc)
                    yield StreamEvent(
                        type="error",
                        text=f"SDK subprocess упал: {exc}",
                    )
                    return
            except Exception as exc:
                logger.error("Ошибка query: %s", exc)
                yield StreamEvent(type="error", text=f"Ошибка SDK query: {exc}")
                return

        # Читаем ответ через receive_response() — останавливается на ResultMessage.
        logger.info("stream_reply: ожидание receive_response()")
        full_text = ""
        msg_count = 0
        try:
            async for message in self._client.receive_response():
                msg_count += 1
                msg_type = type(message).__name__
                logger.info("stream_reply: msg #%d type=%s", msg_count, msg_type)
                async for event in self._process_message(message):
                    if event.type == "text_delta":
                        full_text += event.text
                    yield event
        except (BrokenPipeError, OSError, ConnectionError) as exc:
            logger.error("BrokenPipe при чтении ответа: %s", exc)
            yield StreamEvent(
                type="error",
                text=f"SDK subprocess упал при чтении: {exc}",
            )
            # Пробуем reconnect для будущих запросов
            try:
                await self._reconnect()
            except Exception:
                pass
            return
        except Exception as exc:
            logger.error("Ошибка чтения ответа SDK: %s", exc)
            yield StreamEvent(type="error", text=f"Ошибка SDK: {exc}")
            return

        # Финальное событие
        yield StreamEvent(type="done", text=full_text, is_final=True)

    @staticmethod
    def _on_stderr(line: str) -> None:
        """Callback для stderr subprocess — логируем для диагностики."""
        stripped = line.strip()
        if not stripped:
            return
        # Ошибки и предупреждения выводим как warning, остальное как info
        low = stripped.lower()
        if any(kw in low for kw in ("error", "fail", "timeout", "refused", "broken", "exception")):
            logger.warning("claude-cli stderr: %s", stripped)
        else:
            logger.info("claude-cli stderr: %s", stripped)

    async def _process_message(self, message: Message) -> AsyncIterator[StreamEvent]:
        """Преобразовать SDK Message в поток StreamEvent."""
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    yield StreamEvent(type="text_delta", text=block.text)
                elif isinstance(block, ToolUseBlock):
                    yield StreamEvent(
                        type="tool_use_start",
                        tool_name=block.name,
                        tool_input=block.input,
                    )
                elif isinstance(block, ToolResultBlock):
                    result_text = str(block.content) if hasattr(block, "content") else ""
                    yield StreamEvent(
                        type="tool_use_result",
                        tool_result=result_text,
                    )
        elif isinstance(message, ResultMessage):
            # ResultMessage — финальный итог turn'а (cost, duration и т.д.).
            # Текст из content не дублируем — он уже был в AssistantMessage.
            pass
