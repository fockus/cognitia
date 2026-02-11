"""HookRegistry — реестр хуков для перехвата событий агента."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

# Типы хуков
HookCallback = Callable[..., Awaitable[Any]]


@dataclass
class HookEntry:
    """Запись в реестре хуков."""

    event: str  # 'PreToolUse' | 'PostToolUse' | 'Stop' | 'UserPromptSubmit' | etc.
    callback: HookCallback
    matcher: str = ""  # Фильтр по tool name (опционально)


class HookRegistry:
    """Реестр хуков (программная регистрация для MVP).

    Хуки маппятся в SDK HookMatcher при сборке ClaudeAgentOptions.
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[HookEntry]] = {}

    def on_pre_tool_use(self, callback: HookCallback, matcher: str = "") -> None:
        """Зарегистрировать хук перед вызовом инструмента."""
        self._add("PreToolUse", callback, matcher)

    def on_post_tool_use(self, callback: HookCallback, matcher: str = "") -> None:
        """Зарегистрировать хук после вызова инструмента."""
        self._add("PostToolUse", callback, matcher)

    def on_stop(self, callback: HookCallback) -> None:
        """Зарегистрировать хук при остановке."""
        self._add("Stop", callback)

    def on_user_prompt(self, callback: HookCallback) -> None:
        """Зарегистрировать хук при отправке промпта."""
        self._add("UserPromptSubmit", callback)

    def _add(self, event: str, callback: HookCallback, matcher: str = "") -> None:
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(HookEntry(event=event, callback=callback, matcher=matcher))

    def get_hooks(self, event: str) -> list[HookEntry]:
        """Получить хуки для события."""
        return self._hooks.get(event, [])

    def list_events(self) -> list[str]:
        """Все события с зарегистрированными хуками."""
        return list(self._hooks.keys())
