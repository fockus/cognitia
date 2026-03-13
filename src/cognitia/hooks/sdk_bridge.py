"""SDK Bridge — конвертация cognitia HookRegistry → SDK HookMatcher формат.

Позволяет использовать cognitia HookRegistry для регистрации хуков,
а затем преобразовать их в формат, который понимает Claude Agent SDK.
"""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import HookMatcher

from cognitia.hooks.registry import HookEntry, HookRegistry


def registry_to_sdk_hooks(
    registry: HookRegistry,
) -> dict[str, list[HookMatcher]] | None:
    """Конвертировать cognitia HookRegistry → SDK hooks dict.

    Returns:
        dict[HookEvent, list[HookMatcher]] для передачи в ClaudeAgentOptions.hooks,
        или None если registry пуст.
    """
    events = registry.list_events()
    if not events:
        return None

    sdk_hooks: dict[str, list[HookMatcher]] = {}

    for event_name in events:
        entries = registry.get_hooks(event_name)
        matchers = [_entry_to_matcher(entry) for entry in entries]
        sdk_hooks[event_name] = matchers

    return sdk_hooks


def _entry_to_matcher(entry: HookEntry) -> HookMatcher:
    """Конвертировать HookEntry → SDK HookMatcher."""
    sdk_callback = _wrap_callback(entry.callback)
    return HookMatcher(
        matcher=entry.matcher or None,
        hooks=[sdk_callback],
    )


def _wrap_callback(cognitia_callback: Any) -> Any:
    """Обернуть cognitia callback в SDK-совместимый HookCallback.

    SDK HookCallback signature: (input: HookInput, tool_use_id: str | None, context: HookContext) -> HookJSONOutput
    Cognitia callback signature: (**kwargs) -> dict | None
    """

    async def sdk_callback(
        hook_input: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        # Передаём все поля hook_input как kwargs в cognitia callback
        result = await cognitia_callback(**hook_input)
        if result is None:
            return {"continue_": True}
        return result

    return sdk_callback
