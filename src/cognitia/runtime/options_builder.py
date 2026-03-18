"""ClaudeOptionsBuilder — фабрика для ClaudeAgentOptions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    HookMatcher,
    McpSdkServerConfig,
    PermissionResultAllow,
    PermissionResultDeny,
    PermissionMode,
    SandboxSettings,
    SdkBeta,
    SdkPluginConfig,
    SettingSource,
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
        permission_mode: PermissionMode = "bypassPermissions",
        tool_failure_count: int = 0,
        setting_sources: list[SettingSource] | None = None,
        max_thinking_tokens: int | None = None,
        sandbox: SandboxSettings | None = None,
        agents: dict[str, AgentDefinition] | None = None,
        env: dict[str, str] | None = None,
        output_format: dict[str, Any] | None = None,
        continue_conversation: bool = False,
        resume: str | None = None,
        fork_session: bool = False,
        betas: list[SdkBeta] | None = None,
        plugins: list[SdkPluginConfig] | None = None,
        include_partial_messages: bool = False,
        enable_file_checkpointing: bool = False,
        max_budget_usd: float | None = None,
        fallback_model: str | None = None,
        hooks: dict[str, list[HookMatcher]] | None = None,
    ) -> ClaudeAgentOptions:
        """Собрать ClaudeAgentOptions.

        Args:
            setting_sources: источники настроек SDK.
                По умолчанию [] — не читаем CLAUDE.md и .claude/settings.json.
            max_thinking_tokens: лимит токенов для extended thinking.
            sandbox: настройки sandbox для Bash-команд.
            agents: определения sub-agents (AgentDefinition).
            env: переменные окружения для subprocess.
            output_format: JSON Schema для structured output.
            continue_conversation: продолжить предыдущую сессию.
            resume: session_id для возобновления.
            fork_session: форкнуть сессию при resume (новый session_id).
            betas: список beta-фич (например, 1M context).
            plugins: список SDK plugin конфигураций.
            include_partial_messages: включить partial StreamEvent.
            enable_file_checkpointing: трекинг изменений файлов.
            max_budget_usd: лимит бюджета в USD.
            fallback_model: fallback модель при ошибке.
            hooks: SDK hooks (dict[HookEvent, list[HookMatcher]]).
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

        # По умолчанию НЕ читаем project/user settings (CLAUDE.md, .claude/settings.json).
        sources: list[SettingSource] = setting_sources if setting_sources is not None else []

        opts = ClaudeAgentOptions(
            model=model,
            system_prompt=system_prompt,
            mcp_servers=all_mcp,
            allowed_tools=allowed_tools or [],
            disallowed_tools=disallowed_tools or [],
            can_use_tool=can_use_tool,
            max_turns=max_turns,
            permission_mode=permission_mode,
            cwd=str(self._cwd) if self._cwd else None,
            setting_sources=sources,
            max_thinking_tokens=max_thinking_tokens,
            sandbox=sandbox,
            agents=agents,
            env=env or {},
            output_format=output_format,
            continue_conversation=continue_conversation,
            resume=resume,
            fork_session=fork_session,
            betas=betas or [],
            plugins=plugins or [],
            include_partial_messages=include_partial_messages,
            enable_file_checkpointing=enable_file_checkpointing,
            max_budget_usd=max_budget_usd,
            fallback_model=fallback_model,
            hooks=hooks,  # type: ignore[arg-type]
        )
        return opts


# ---------------------------------------------------------------------------
# OCP: dispatch table вместо if/elif цепочки
# ---------------------------------------------------------------------------


def _build_url_config(spec: McpServerSpec) -> dict[str, Any]:
    """Конфиг для URL транспорта (Streamable HTTP).

    MCP серверы calculado.ru используют Streamable HTTP (MCP 2024-11-05+):
    - POST с Accept: application/json, text/event-stream
    - Сессия через заголовок mcp-session-id
    Claude SDK тип "http" = McpHttpServerConfig (Streamable HTTP).
    """
    return {"type": "http", "url": spec.url or ""}


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
