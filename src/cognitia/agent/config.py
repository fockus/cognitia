"""AgentConfig — frozen конфигурация для Agent facade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cognitia.runtime.capabilities import (
    VALID_FEATURE_MODES,
    CapabilityRequirements,
    get_runtime_capabilities,
)
from cognitia.runtime.types import VALID_RUNTIME_NAMES

if TYPE_CHECKING:
    from cognitia.agent.middleware import Middleware
    from cognitia.agent.tool import ToolDefinition
    from cognitia.hooks.registry import HookRegistry


@dataclass(frozen=True)
class AgentConfig:
    """Immutable конфигурация Agent facade.

    Минимальный required параметр — system_prompt.
    Все остальные имеют разумные defaults.
    """

    system_prompt: str

    # Модель (alias или полное имя)
    model: str = "sonnet"

    # Runtime: claude_sdk | thin | deepagents
    runtime: str = "claude_sdk"

    # Tools (standalone @tool decorated functions)
    tools: tuple[ToolDefinition, ...] = ()

    # Middleware chain (applied in order)
    middleware: tuple[Middleware, ...] = ()

    # Remote MCP servers
    mcp_servers: dict[str, Any] = field(default_factory=dict)

    # Cognitia hooks
    hooks: HookRegistry | None = None

    # Limits
    max_turns: int | None = None
    max_budget_usd: float | None = None

    # Structured output (JSON Schema)
    output_format: dict[str, Any] | None = None

    # Working directory
    cwd: str | None = None

    # Environment variables
    env: dict[str, str] = field(default_factory=dict)

    # SDK-specific (только для claude_sdk runtime)
    betas: tuple[str, ...] = ()
    sandbox: dict[str, Any] | None = None
    max_thinking_tokens: int | None = None
    fallback_model: str | None = None
    permission_mode: str = "bypassPermissions"
    setting_sources: tuple[str, ...] = ()

    # Runtime convergence / capability negotiation
    feature_mode: str = "portable"
    require_capabilities: CapabilityRequirements | None = None
    allow_native_features: bool = False
    native_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.system_prompt or not self.system_prompt.strip():
            raise ValueError("system_prompt не может быть пустым")
        if self.runtime not in VALID_RUNTIME_NAMES:
            raise ValueError(
                f"Неизвестный runtime: '{self.runtime}'. "
                f"Допустимые: {', '.join(sorted(VALID_RUNTIME_NAMES))}"
            )
        if self.feature_mode not in VALID_FEATURE_MODES:
            raise ValueError(
                f"Неизвестный feature_mode: '{self.feature_mode}'. "
                f"Допустимые: {', '.join(sorted(VALID_FEATURE_MODES))}"
            )
        if self.require_capabilities is not None:
            caps = get_runtime_capabilities(self.runtime)
            missing = caps.missing(self.require_capabilities)
            if missing:
                raise ValueError(
                    f"Runtime '{self.runtime}' не поддерживает требуемые capabilities: "
                    f"{', '.join(missing)}"
                )

    @property
    def resolved_model(self) -> str:
        """Разрешить alias модели в полное имя."""
        from cognitia.runtime.types import resolve_model_name

        return resolve_model_name(self.model)
