"""SDK Adapter — обёртка над ClaudeSDKClient для унифицированного stream_reply."""

from __future__ import annotations

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
    """

    def __init__(self, options: ClaudeAgentOptions) -> None:
        self._options = options
        self._client: ClaudeSDKClient | None = None

    async def connect(self) -> None:
        """Подключиться к SDK (запустить subprocess)."""
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.connect()

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

        Yields:
            StreamEvent — унифицированные события для адаптеров интерфейсов.
        """
        if not self._client:
            yield StreamEvent(type="error", text="SDK клиент не подключён")
            return

        await self._client.query(user_text)

        full_text = ""
        async for message in self._client.receive_messages():
            async for event in self._process_message(message):
                if event.type == "text_delta":
                    full_text += event.text
                yield event

        # Финальное событие
        yield StreamEvent(type="done", text=full_text, is_final=True)

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
        elif isinstance(message, ResultMessage) and hasattr(message, "content"):
            # Финальный результат — может содержать итоговый текст
            yield StreamEvent(type="text_delta", text=str(message.content))
