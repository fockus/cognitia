"""YAML command definitions loader.

Загружает определения команд из YAML файлов для auto-discovery.
Поддерживает: single file, directory scan, single-command и multi-command форматы.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LoadedCommand:
    """Определение команды, загруженное из YAML.

    Поддерживает как атрибутный (cmd.name), так и dict-подобный (cmd['name']) доступ
    для backward compatibility с кодом, ожидающим dict.
    """

    name: str
    description: str = ""
    category: str = ""
    parameters: dict[str, Any] | None = None
    aliases: list[str] = field(default_factory=list)

    def __getitem__(self, key: str) -> Any:
        """Dict-like доступ: cmd['name'], cmd['category']."""
        return getattr(self, key)


def _parse_yaml_data(data: Any) -> list[LoadedCommand]:
    """Парсит YAML data в список LoadedCommand."""
    if not isinstance(data, dict):
        return []

    # Multi-command format: {commands: [{name: ..., ...}, ...]}
    if "commands" in data:
        commands: list[LoadedCommand] = []
        for cmd_def in data["commands"]:
            if not isinstance(cmd_def, dict) or "name" not in cmd_def:
                continue
            commands.append(
                LoadedCommand(
                    name=cmd_def["name"],
                    description=cmd_def.get("description", ""),
                    category=cmd_def.get("category", ""),
                    parameters=cmd_def.get("parameters"),
                    aliases=cmd_def.get("aliases", []),
                )
            )
        return commands

    # Single-command format: {name: ..., description: ..., ...}
    if "name" in data:
        return [
            LoadedCommand(
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category", ""),
                parameters=data.get("parameters"),
                aliases=data.get("aliases", []),
            )
        ]

    return []


def load_commands_from_yaml(
    path: str | Path,
    handler_registry: dict[str, Callable[..., Awaitable[str]]] | None = None,
) -> list[LoadedCommand]:
    """Загрузить определения команд из YAML файла или директории.

    Если path — директория: сканирует все .yaml/.yml файлы (single-command формат).
    Если path — файл: поддерживает multi-command (commands: [...]) и
    single-command (name: ...) форматы.

    Args:
        path: Путь к директории или YAML-файлу (str или Path).
        handler_registry: Зарезервировано для совместимости с auto_discover_commands.

    Returns:
        Список LoadedCommand с атрибутным и dict-подобным (cmd['name']) доступом.
    """
    p = Path(path)

    if p.is_dir():
        results: list[LoadedCommand] = []
        for yaml_file in sorted(p.glob("*.yaml")):
            results.extend(_load_single_file(yaml_file))
        for yml_file in sorted(p.glob("*.yml")):
            results.extend(_load_single_file(yml_file))
        return results

    return _load_single_file(p)


def _load_single_file(path: Path) -> list[LoadedCommand]:
    """Загрузить команды из одного YAML файла. Возвращает [] при ошибке."""
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return []
    return _parse_yaml_data(data)


def auto_discover_commands(
    registry: Any,
    directory: Path,
    handler_registry: dict[str, Callable[..., Awaitable[str]]] | None = None,
) -> int:
    """Discover и зарегистрировать команды из YAML-директории в CommandRegistry.

    Загружает LoadedCommand из каждого .yaml/.yml файла в директории
    и регистрирует их через registry.add().

    Args:
        registry: CommandRegistry для регистрации команд.
        directory: Директория с YAML-файлами (single-command формат).
        handler_registry: Опциональный маппинг имя → handler.

    Returns:
        Количество успешно загруженных и зарегистрированных команд.
    """
    effective_handlers: dict[str, Callable[..., Awaitable[str]]] = handler_registry or {}
    commands = load_commands_from_yaml(directory, effective_handlers)

    for cmd in commands:
        handler = effective_handlers.get(cmd.name)

        if handler is None:
            cmd_name = cmd.name

            async def _noop(*args: Any, _name: str = cmd_name, **kwargs: Any) -> str:
                return f"Command '{_name}' executed (no handler registered)"

            handler = _noop

        registry.add(
            cmd.name,
            handler,
            aliases=cmd.aliases,
            description=cmd.description,
            category=cmd.category,
            parameters=cmd.parameters,
        )

    return len(commands)
