"""Модуль хуков — перехват событий агента."""

from contextlib import suppress

from cognitia.hooks.registry import HookCallback, HookEntry, HookRegistry

# sdk_bridge requires claude_agent_sdk (optional dependency)
registry_to_sdk_hooks = None
with suppress(ImportError):
    from cognitia.hooks.sdk_bridge import registry_to_sdk_hooks

__all__ = ["HookCallback", "HookEntry", "HookRegistry", "registry_to_sdk_hooks"]
