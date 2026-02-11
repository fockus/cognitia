"""ClaudeOptionsBuilder — фабрика для ClaudeAgentOptions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    McpSdkServerConfig,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

from cognitia.skills.types import McpServerSpec

if TYPE_CHECKING:
    from cognitia.protocols import ModelSelector


# Тип callback для can_use_tool
CanUseToolFn = Callable[
    [str, dict[str, Any], ToolPermissionContext],
    Awaitable[PermissionResultAllow | PermissionResultDeny],
]


class ClaudeOptionsBuilder:
    """Строитель ClaudeAgentOptions из компонентов Cognitia."""

    def __init__(
        self,
        model_policy: ModelSelector | None = None,
        cwd: str | Path | None = None,
        override_model: str | None = None,
    ) -> None:
        if model_policy is None:
            from cognitia.runtime.model_policy import ModelPolicy

            model_policy = ModelPolicy()
        self._model_policy = model_policy
        self._cwd = cwd
        self._override_model = override_model

    def build(
        self,
        *,
        role_id: str,
        system_prompt: str,
        mcp_servers: dict[str, McpServerSpec] | None = None,
        sdk_mcp_servers: dict[str, McpSdkServerConfig] | None = None,
        allowed_tools: list[str] | None = None,
        disallowed_tools: list[str] | None = None,
        can_use_tool: CanUseToolFn | None = None,
        max_turns: int | None = None,
        tool_failure_count: int = 0,
        setting_sources: list[str] | None = None,
    ) -> ClaudeAgentOptions:
        """Собрать ClaudeAgentOptions.

        Args:
            setting_sources: источники настроек SDK (§2.2, R-401).
                По умолчанию ["project", "user"] — SDK читает .claude/settings.json.
        """
        # override_model имеет приоритет над ModelPolicy
        model = (
            self._override_model
            if self._override_model
            else self._model_policy.select(role_id, tool_failure_count)
        )

        # Сливаем MCP серверы: remote (HTTP) + SDK (in-process)
        all_mcp: dict[str, Any] = {}

        if mcp_servers:
            for name, spec in mcp_servers.items():
                all_mcp[name] = _spec_to_sdk_config(spec)

        if sdk_mcp_servers:
            all_mcp.update(sdk_mcp_servers)

        # §2.2: включаем чтение .claude/settings.json (R-401 acceptance)
        sources = setting_sources if setting_sources is not None else ["project", "user"]

        opts = ClaudeAgentOptions(
            model=model,
            system_prompt=system_prompt,
            mcp_servers=all_mcp,
            allowed_tools=allowed_tools or [],
            disallowed_tools=disallowed_tools or [],
            can_use_tool=can_use_tool,
            max_turns=max_turns,
            permission_mode="bypassPermissions",
            cwd=str(self._cwd) if self._cwd else None,
            setting_sources=sources,  # type: ignore[arg-type]
        )
        return opts


# ---------------------------------------------------------------------------
# OCP: dispatch table вместо if/elif цепочки
# ---------------------------------------------------------------------------


def _build_url_config(spec: McpServerSpec) -> dict[str, Any]:
    """Конфиг для URL транспорта.

    В нашем проекте url/http MCP endpoints — это SSE endpoints.
    Для Claude SDK необходимо явно указать type="sse", иначе connect()
    зависает на initialize timeout.
    """
    return {"type": "sse", "url": spec.url or ""}


def _build_sse_config(spec: McpServerSpec) -> dict[str, Any]:
    """Конфиг для SSE транспорта."""
    return {"type": "sse", "url": spec.url or ""}


def _build_stdio_config(spec: McpServerSpec) -> dict[str, Any]:
    """Конфиг для stdio транспорта."""
    cfg: dict[str, Any] = {
        "type": "stdio",
        "command": spec.command or "",
    }
    if spec.args:
        cfg["args"] = spec.args
    if spec.env:
        cfg["env"] = spec.env
    return cfg


_TRANSPORT_BUILDERS: dict[str, Callable[[McpServerSpec], dict[str, Any]]] = {
    "url": _build_url_config,
    "http": _build_url_config,
    "sse": _build_sse_config,
    "stdio": _build_stdio_config,
}


def _spec_to_sdk_config(spec: McpServerSpec) -> dict[str, Any]:
    """Преобразовать McpServerSpec в SDK-совместимый dict (TypedDict).

    OCP: новый transport → добавить в _TRANSPORT_BUILDERS, не менять эту функцию.
    """
    builder = _TRANSPORT_BUILDERS.get(spec.transport, _build_url_config)
    return builder(spec)
