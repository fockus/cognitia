"""Policy helpers для native built-ins DeepAgents."""

from __future__ import annotations

from dataclasses import dataclass

from cognitia.runtime.types import ToolSpec

DEEPAGENTS_NATIVE_BUILTIN_TOOLS = frozenset(
    {
        "write_todos",
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
        "task",
    }
)

DEEPAGENTS_NATIVE_BUILTIN_ALIASES = {
    "TodoRead": "write_todos",
    "TodoWrite": "write_todos",
    "LS": "ls",
    "Read": "read_file",
    "Write": "write_file",
    "Edit": "edit_file",
    "MultiEdit": "edit_file",
    "Glob": "glob",
    "Grep": "grep",
    "Bash": "execute",
    "Task": "task",
}


@dataclass(frozen=True)
class DeepAgentsBuiltinSelection:
    """Результат выделения native built-ins из списка tools."""

    custom_tools: list[ToolSpec]
    native_tool_names: list[str]
    alias_mappings: list[tuple[str, str]]


def canonicalize_builtin_name(name: str) -> str | None:
    """Вернуть canonical native built-in name или None."""
    if name in DEEPAGENTS_NATIVE_BUILTIN_TOOLS:
        return name
    return DEEPAGENTS_NATIVE_BUILTIN_ALIASES.get(name)


def split_native_builtin_tools(
    tools: list[ToolSpec],
) -> DeepAgentsBuiltinSelection:
    """Отделить native built-ins от custom tools."""
    custom_tools: list[ToolSpec] = []
    native_tool_names: list[str] = []
    alias_mappings: list[tuple[str, str]] = []
    seen_native: set[str] = set()
    seen_aliases: set[tuple[str, str]] = set()

    for tool in tools:
        canonical_name = canonicalize_builtin_name(tool.name)
        if canonical_name is None:
            custom_tools.append(tool)
            continue

        if canonical_name not in seen_native:
            seen_native.add(canonical_name)
            native_tool_names.append(canonical_name)

        if tool.name != canonical_name:
            mapping = (tool.name, canonical_name)
            if mapping not in seen_aliases:
                seen_aliases.add(mapping)
                alias_mappings.append(mapping)

    return DeepAgentsBuiltinSelection(
        custom_tools=custom_tools,
        native_tool_names=native_tool_names,
        alias_mappings=alias_mappings,
    )


def filter_native_builtin_tools(tools: list[ToolSpec]) -> list[ToolSpec]:
    """Убрать native built-ins и их aliases из portable tool list."""
    return split_native_builtin_tools(tools).custom_tools


def build_portable_notice(tools: list[ToolSpec]) -> str | None:
    """Собрать status notice для portable mode, если built-ins были отброшены."""
    selection = split_native_builtin_tools(tools)
    if not selection.native_tool_names:
        return None

    native_list = ", ".join(selection.native_tool_names)
    return f"DeepAgents portable mode пропускает native built-ins: {native_list}"


def build_native_notice(
    tools: list[ToolSpec],
    *,
    feature_mode: str,
) -> str | None:
    """Собрать status notice для native/hybrid path."""
    selection = split_native_builtin_tools(tools)
    if not selection.native_tool_names:
        return None

    prefix = "DeepAgents native built-ins active"
    if feature_mode == "native_first":
        prefix = "DeepAgents native-first mode preferring built-ins"

    parts = [prefix]
    if selection.alias_mappings:
        mapped = ", ".join(f"{source}->{target}" for source, target in selection.alias_mappings)
        parts.append(f"mapped aliases: {mapped}")
    parts.append(f"native tools: {', '.join(selection.native_tool_names)}")
    return "; ".join(parts)
