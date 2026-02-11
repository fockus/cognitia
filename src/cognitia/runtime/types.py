"""Типы для runtime pluggability — AgentRuntime v1 контракт.

Содержит:
- Message: универсальное сообщение для runtime (расширение MemoryMessage)
- ToolSpec: описание инструмента (name, description, parameters)
- RuntimeEvent: унифицированное событие стриминга
- RuntimeErrorData: типизированная ошибка runtime
- RuntimeConfig: конфигурация выбора и параметров runtime
- TurnMetrics: метрики выполнения turn'а
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Message — каноническое сообщение для runtime
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Message:
    """Универсальное сообщение для AgentRuntime.

    Расширяет MemoryMessage: добавлены name (для tool results) и metadata.
    Совместимо с MemoryMessage через from_memory_message().
    """

    role: str  # "user" | "assistant" | "tool" | "system"
    content: str
    name: str | None = None  # имя инструмента (для role="tool")
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_memory_message(cls, mm: Any) -> Message:
        """Создать Message из MemoryMessage (backward compat)."""
        return cls(
            role=mm.role,
            content=mm.content,
            tool_calls=getattr(mm, "tool_calls", None),
        )

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать в dict (для передачи в LLM API)."""
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            d["name"] = self.name
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d


# ---------------------------------------------------------------------------
# ToolSpec — описание инструмента
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolSpec:
    """Описание инструмента для передачи в runtime.

    Runtime использует эту информацию для формирования tool list
    в запросе к LLM (каждый runtime преобразует в свой формат).
    """

    name: str  # "mcp__server__tool_name" или "local_tool_name"
    description: str
    parameters: dict[str, Any]  # JSON Schema
    is_local: bool = False  # True для local tools (вызываются напрямую)

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать в dict."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "is_local": self.is_local,
        }


# ---------------------------------------------------------------------------
# RuntimeErrorData — типизированная ошибка
# ---------------------------------------------------------------------------

# Допустимые виды ошибок
RUNTIME_ERROR_KINDS = frozenset(
    {
        "runtime_crash",  # фатальная ошибка runtime
        "bad_model_output",  # LLM вернула некорректный JSON
        "loop_limit",  # превышен max_iterations
        "budget_exceeded",  # превышен max_tool_calls
        "mcp_timeout",  # таймаут MCP-вызова
        "tool_error",  # ошибка выполнения инструмента
        "dependency_missing",  # отсутствует optional dependency
    }
)


@dataclass(frozen=True)
class RuntimeErrorData:
    """Типизированная ошибка runtime.

    Используется внутри RuntimeEvent(type="error").
    """

    kind: str  # одно из RUNTIME_ERROR_KINDS
    message: str
    recoverable: bool = False
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.kind not in RUNTIME_ERROR_KINDS:
            object.__setattr__(
                self,
                "kind",
                "runtime_crash",
            )

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать в dict."""
        d: dict[str, Any] = {
            "kind": self.kind,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.details is not None:
            d["details"] = self.details
        return d


# ---------------------------------------------------------------------------
# TurnMetrics — метрики turn'а
# ---------------------------------------------------------------------------


@dataclass
class TurnMetrics:
    """Метрики выполнения одного turn'а."""

    latency_ms: int = 0
    iterations: int = 0
    tool_calls_count: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать в dict."""
        return {
            "latency_ms": self.latency_ms,
            "iterations": self.iterations,
            "tool_calls_count": self.tool_calls_count,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "model": self.model,
        }


# ---------------------------------------------------------------------------
# RuntimeEvent — унифицированное событие стриминга
# ---------------------------------------------------------------------------

# Допустимые типы событий
RUNTIME_EVENT_TYPES = frozenset(
    {
        "assistant_delta",  # потоковый вывод текста
        "status",  # статусное сообщение ("Выполняю шаг…")
        "tool_call_started",  # начало вызова инструмента
        "tool_call_finished",  # окончание вызова инструмента
        "final",  # финальный ответ (полный текст + new_messages)
        "error",  # ошибка
    }
)


@dataclass
class RuntimeEvent:
    """Унифицированное событие потока от runtime.

    Типы:
    - assistant_delta: data={"text": "..."}
    - status: data={"text": "..."}
    - tool_call_started: data={"name": "...", "correlation_id": "...", "args": {...}}
    - tool_call_finished: data={"name": "...", "correlation_id": "...", "ok": bool, "result_summary": "..."}
    - final: data={"text": "...", "new_messages": [...], "metrics": {...}}
    - error: data=RuntimeErrorData.to_dict()
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def assistant_delta(text: str) -> RuntimeEvent:
        """Потоковый текстовый фрагмент."""
        return RuntimeEvent(type="assistant_delta", data={"text": text})

    @staticmethod
    def status(text: str) -> RuntimeEvent:
        """Статусное сообщение."""
        return RuntimeEvent(type="status", data={"text": text})

    @staticmethod
    def tool_call_started(
        name: str,
        args: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> RuntimeEvent:
        """Начало вызова инструмента."""
        cid = correlation_id or uuid.uuid4().hex[:8]
        return RuntimeEvent(
            type="tool_call_started",
            data={"name": name, "correlation_id": cid, "args": args or {}},
        )

    @staticmethod
    def tool_call_finished(
        name: str,
        correlation_id: str,
        ok: bool = True,
        result_summary: str = "",
    ) -> RuntimeEvent:
        """Окончание вызова инструмента."""
        return RuntimeEvent(
            type="tool_call_finished",
            data={
                "name": name,
                "correlation_id": correlation_id,
                "ok": ok,
                "result_summary": result_summary[:200],
            },
        )

    @staticmethod
    def final(
        text: str,
        new_messages: list[Message] | None = None,
        metrics: TurnMetrics | None = None,
    ) -> RuntimeEvent:
        """Финальный ответ."""
        return RuntimeEvent(
            type="final",
            data={
                "text": text,
                "new_messages": [m.to_dict() for m in (new_messages or [])],
                "metrics": metrics.to_dict() if metrics else {},
            },
        )

    @staticmethod
    def error(error: RuntimeErrorData) -> RuntimeEvent:
        """Ошибка runtime."""
        return RuntimeEvent(type="error", data=error.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать в dict."""
        return {"type": self.type, "data": self.data}


# ---------------------------------------------------------------------------
# RuntimeConfig — конфигурация runtime
# ---------------------------------------------------------------------------

# Допустимые имена runtime
VALID_RUNTIME_NAMES = frozenset({"claude_sdk", "deepagents", "thin"})

# ---------------------------------------------------------------------------
# Модели — делегируем в ModelRegistry (models.yaml)
# ---------------------------------------------------------------------------


def _get_registry():
    """Ленивая загрузка ModelRegistry (избегаем circular imports)."""
    from cognitia.runtime.model_registry import get_registry

    return get_registry()


def _valid_model_names() -> frozenset[str]:
    """Допустимые полные имена моделей (из YAML конфига)."""
    result: frozenset[str] = _get_registry().valid_models
    return result


def _default_model() -> str:
    """Модель по умолчанию (из YAML конфига)."""
    result: str = _get_registry().default_model
    return result


# Backward-compatible constants (ленивые property не подходят для frozenset,
# поэтому экспортируем функции + статические alias для импортов)
VALID_MODEL_NAMES: frozenset[str] = frozenset()  # Заполняется при первом использовании
DEFAULT_MODEL: str = "claude-sonnet-4-20250514"  # Статический fallback


def _ensure_model_constants() -> None:
    """Инициализировать model constants из registry (один раз)."""
    global VALID_MODEL_NAMES, DEFAULT_MODEL
    if not VALID_MODEL_NAMES:
        try:
            reg = _get_registry()
            VALID_MODEL_NAMES = reg.valid_models
            DEFAULT_MODEL = reg.default_model
        except Exception:
            # Fallback если YAML недоступен
            VALID_MODEL_NAMES = frozenset({"claude-sonnet-4-20250514"})
            DEFAULT_MODEL = "claude-sonnet-4-20250514"


def resolve_model_name(raw: str | None) -> str:
    """Разрешить имя модели: alias/prefix/full → полное имя.

    Мультипровайдерная поддержка — модели и alias загружаются из models.yaml.
    Поддерживает: Anthropic, OpenAI, Google, DeepSeek и др.

    Примеры:
    - "sonnet" → "claude-sonnet-4-20250514"
    - "gpt-4o" → "gpt-4o"
    - "gemini" → "gemini-2.5-pro"
    - "r1" → "deepseek-reasoner"
    - None → DEFAULT_MODEL
    """
    _ensure_model_constants()
    result: str = _get_registry().resolve(raw)
    return result


@dataclass
class RuntimeConfig:
    """Конфигурация выбора и параметров runtime.

    Приоритет: runtime_override > runtime_name > env COGNITIA_RUNTIME > default.
    """

    runtime_name: str = "claude_sdk"

    # Budgets для ThinRuntime
    max_iterations: int = 6
    max_tool_calls: int = 8
    max_model_retries: int = 2

    # Модель для ThinRuntime / DeepAgents
    model: str = DEFAULT_MODEL

    # Base URL для LLM API (OpenRouter, proxy, и т.д.)
    # None = стандартный URL провайдера
    base_url: str | None = None

    # Дополнительные параметры (extensible)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.runtime_name not in VALID_RUNTIME_NAMES:
            raise ValueError(
                f"Неизвестный runtime: '{self.runtime_name}'. "
                f"Допустимые: {', '.join(sorted(VALID_RUNTIME_NAMES))}"
            )
