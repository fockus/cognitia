"""InMemorySessionManager — управление сессиями агента в памяти."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from cognitia.runtime import StreamEvent
from cognitia.runtime.types import Message, RuntimeErrorData, RuntimeEvent, ToolSpec
from cognitia.session.types import SessionKey, SessionState


class InMemorySessionManager:
    """Менеджер сессий (in-memory, для MVP).

    - Хранит активные сессии в dict
    - asyncio.Lock per SessionKey для последовательной обработки
    - TTL eviction пока не реализован (post-MVP)
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _key_str(self, key: SessionKey) -> str:
        return str(key)

    def _get_lock(self, key: SessionKey) -> asyncio.Lock:
        """Получить или создать lock для сессии."""
        ks = self._key_str(key)
        if ks not in self._locks:
            self._locks[ks] = asyncio.Lock()
        return self._locks[ks]

    def get(self, key: SessionKey) -> SessionState | None:
        """Получить существующую сессию."""
        return self._sessions.get(self._key_str(key))

    def register(self, state: SessionState) -> None:
        """Зарегистрировать новую сессию."""
        self._sessions[self._key_str(state.key)] = state

    async def close(self, key: SessionKey) -> None:
        """Закрыть сессию и отключить SDK."""
        ks = self._key_str(key)
        state = self._sessions.pop(ks, None)
        if state:
            if state.runtime is not None:
                await state.runtime.cleanup()
            elif state.adapter and state.adapter.is_connected:
                await state.adapter.disconnect()
        self._locks.pop(ks, None)

    async def close_all(self) -> None:
        """Закрыть все сессии."""
        keys = list(self._sessions.keys())
        for ks in keys:
            state = self._sessions.pop(ks, None)
            if state:
                if state.runtime is not None:
                    await state.runtime.cleanup()
                elif state.adapter and state.adapter.is_connected:
                    await state.adapter.disconnect()
        self._locks.clear()

    async def run_turn(
        self,
        key: SessionKey,
        *,
        messages: list[Message],
        system_prompt: str,
        active_tools: list[ToolSpec],
        mode_hint: str | None = None,
    ) -> AsyncIterator[RuntimeEvent]:
        """Выполнить turn через AgentRuntime v1 (новый контракт)."""
        lock = self._get_lock(key)
        async with lock:
            state = self.get(key)
            if not state:
                yield RuntimeEvent.error(
                    RuntimeErrorData(
                        kind="runtime_crash",
                        message="Сессия не найдена",
                        recoverable=False,
                    )
                )
                return

            if state.runtime is None:
                yield RuntimeEvent.error(
                    RuntimeErrorData(
                        kind="runtime_crash",
                        message="Runtime не инициализирован в сессии",
                        recoverable=False,
                    )
                )
                return

            async for event in state.runtime.run(
                messages=messages,
                system_prompt=system_prompt,
                active_tools=active_tools,
                config=state.runtime_config,
                mode_hint=mode_hint,
            ):
                yield event

    async def stream_reply(self, key: SessionKey, user_text: str) -> AsyncIterator[Any]:
        """Legacy API: отправить сообщение и стримить ответ (RuntimePort/adapter path)."""
        lock = self._get_lock(key)
        async with lock:
            state = self.get(key)
            if not state:
                yield StreamEvent(type="error", text="Сессия не найдена")
                return

            # Новый runtime путь (fallback для мест, где ещё вызывают stream_reply).
            if state.runtime is not None and state.adapter is None:
                state.runtime_messages.append(Message(role="user", content=user_text))
                full_text = ""
                assistant_emitted = False
                async for runtime_event in state.runtime.run(
                    messages=list(state.runtime_messages),
                    system_prompt=state.system_prompt,
                    active_tools=state.active_tools,
                    config=state.runtime_config,
                ):
                    if runtime_event.type == "assistant_delta":
                        text = str(runtime_event.data.get("text", ""))
                        full_text += text
                        assistant_emitted = True
                        yield StreamEvent(type="text_delta", text=text)
                    elif runtime_event.type == "tool_call_started":
                        yield StreamEvent(
                            type="tool_use_start",
                            tool_name=str(runtime_event.data.get("name", "")),
                            tool_input=runtime_event.data.get("args"),
                        )
                    elif runtime_event.type == "tool_call_finished":
                        yield StreamEvent(
                            type="tool_use_result",
                            tool_name=str(runtime_event.data.get("name", "")),
                            tool_result=str(runtime_event.data.get("result_summary", "")),
                        )
                    elif runtime_event.type == "error":
                        yield StreamEvent(
                            type="error",
                            text=str(runtime_event.data.get("message", "Ошибка runtime")),
                        )
                        return
                    elif runtime_event.type == "final":
                        final_text = str(runtime_event.data.get("text", ""))
                        if final_text and not full_text:
                            full_text = final_text
                            yield StreamEvent(type="text_delta", text=final_text)
                            assistant_emitted = True
                        if assistant_emitted and full_text:
                            state.runtime_messages.append(
                                Message(role="assistant", content=full_text),
                            )
                        yield StreamEvent(type="done", text=full_text, is_final=True)
                        return

                if assistant_emitted and full_text:
                    state.runtime_messages.append(
                        Message(role="assistant", content=full_text),
                    )
                yield StreamEvent(type="done", text=full_text, is_final=True)
                return

            if not state.adapter or not state.adapter.is_connected:
                yield StreamEvent(type="error", text="SDK не подключён")
                return

            async for event in state.adapter.stream_reply(user_text):
                yield event

    def list_sessions(self) -> list[SessionKey]:
        """Список активных сессий."""
        return [s.key for s in self._sessions.values()]

    def update_role(self, key: SessionKey, role_id: str, skill_ids: list[str]) -> bool:
        """Обновить роль и скилы сессии. Возвращает True если сессия найдена."""
        state = self.get(key)
        if not state:
            return False
        state.role_id = role_id
        state.active_skill_ids = skill_ids
        return True
