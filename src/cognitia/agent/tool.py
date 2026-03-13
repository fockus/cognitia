"""@tool decorator + ToolDefinition — standalone tool registration."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, get_args, get_origin

from cognitia.runtime.types import ToolSpec

# Маппинг Python types → JSON Schema types
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


@dataclass(frozen=True)
class ToolDefinition:
    """Описание инструмента, созданного через @tool."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Awaitable[Any]]

    def to_tool_spec(self) -> ToolSpec:
        """Конвертировать в cognitia ToolSpec (для thin/deepagents runtime)."""
        return ToolSpec(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            is_local=True,
        )


def tool(
    name: str,
    description: str,
    *,
    schema: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Standalone decorator для определения tools.

    Args:
        name: уникальное имя инструмента.
        description: описание для LLM.
        schema: явная JSON Schema (если None — auto-infer из type hints).

    Returns:
        Decorator, который добавляет __tool_definition__ к функции.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        params = schema if schema is not None else _infer_schema(fn)
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=params,
            handler=fn,
        )
        fn.__tool_definition__ = tool_def  # type: ignore[attr-defined]
        return fn

    return decorator


def _infer_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """Auto-infer JSON Schema из type hints функции.

    Поддерживает: str, int, float, bool, Optional[T], T | None.
    Использует get_type_hints() для корректной работы с `from __future__ import annotations`.
    """
    sig = inspect.signature(fn)
    hints = _get_resolved_hints(fn)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls", "return"):
            continue

        annotation = hints.get(param_name, inspect.Parameter.empty)
        if annotation is inspect.Parameter.empty:
            continue

        json_type = _resolve_type(annotation)
        is_optional = _is_optional(annotation)

        if json_type:
            properties[param_name] = {"type": json_type}
            if not is_optional and param.default is inspect.Parameter.empty:
                required.append(param_name)

    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        result["required"] = required
    return result


def _get_resolved_hints(fn: Callable[..., Any]) -> dict[str, Any]:
    """Получить resolved type hints (строки → реальные типы)."""
    try:
        import typing

        return typing.get_type_hints(fn)
    except Exception:
        return getattr(fn, "__annotations__", {})


def _resolve_type(annotation: Any) -> str | None:
    """Разрешить Python type → JSON Schema type string."""
    # Прямой маппинг
    if annotation in _TYPE_MAP:
        return _TYPE_MAP[annotation]

    # Optional[T] = Union[T, None]
    if _is_optional(annotation):
        args = get_args(annotation)
        for arg in args:
            if arg is not type(None):
                return _resolve_type(arg)

    return "string"  # fallback


def _is_optional(annotation: Any) -> bool:
    """Проверить, является ли тип Optional (Union[T, None] или T | None)."""
    origin = get_origin(annotation)

    # typing.Union или types.UnionType (Python 3.10+ X | Y)
    if origin is not None:
        import types

        if origin is getattr(types, "UnionType", None) or str(origin) == "typing.Union":
            args = get_args(annotation)
            return type(None) in args

    return False
