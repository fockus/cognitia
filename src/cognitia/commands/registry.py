"""CommandRegistry — реестр команд для CLI и Telegram."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

# Тип обработчика команды
CommandHandler = Callable[..., Awaitable[str]]

_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _validate_params(params_schema: dict[str, Any], kwargs: dict[str, Any]) -> str | None:
    """Валидировать kwargs по JSON Schema (required + properties.type).

    Не использует внешних зависимостей.
    Возвращает сообщение об ошибке или None если всё ок.
    """
    for field_name in params_schema.get("required", []):
        if field_name not in kwargs:
            return f"Error: required parameter '{field_name}' is missing"

    for prop_name, prop_schema in params_schema.get("properties", {}).items():
        if prop_name not in kwargs:
            continue
        expected_type_name: str = prop_schema.get("type", "")
        expected_type = _TYPE_MAP.get(expected_type_name)
        if expected_type is None:
            continue
        # integer is strict: bool is subclass of int but should not match
        value = kwargs[prop_name]
        if expected_type_name == "integer" and isinstance(value, bool):
            return (
                f"Error: parameter '{prop_name}' must be of type 'integer', "
                f"got '{type(value).__name__}'"
            )
        if not isinstance(value, expected_type):
            return (
                f"Error: parameter '{prop_name}' must be of type '{expected_type_name}', "
                f"got '{type(value).__name__}'"
            )

    return None


@dataclass
class CommandDef:
    """Определение команды."""

    name: str
    handler: CommandHandler
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    category: str = ""
    parameters: dict[str, Any] | None = None

    def __getitem__(self, key: str) -> Any:
        """Dict-like доступ для backward compatibility (cmd['name'])."""
        return getattr(self, key)


@dataclass
class ToolDefinition:
    """Tool definition для LLM — поддерживает атрибутный и dict-подобный доступ."""

    name: str
    description: str
    parameters: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        """Dict-like доступ: tool['name'], tool['parameters']."""
        return getattr(self, key)


class CommandRegistry:
    """Реестр команд с поддержкой алиасов.

    Команды регистрируются программно:
        registry.add("topic.new", aliases=["tn"], handler=create_topic)

    Вызов:
        result = await registry.execute("topic.new", args=["my_topic"], ctx=ctx)
    """

    def __init__(self) -> None:
        self._commands: dict[str, CommandDef] = {}
        self._alias_map: dict[str, str] = {}

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Нормализовать имя команды к canonical-форме.

        Пользовательский формат поддерживает `_` (например `/role_set`),
        внутренняя canonical-форма хранится через `.` (`role.set`).
        """
        return name.replace("_", ".")

    def add(
        self,
        name: str,
        handler: CommandHandler,
        aliases: list[str] | None = None,
        description: str = "",
        category: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Зарегистрировать команду."""
        canonical_name = self._normalize_name(name)
        cmd = CommandDef(
            name=canonical_name,
            handler=handler,
            aliases=aliases or [],
            description=description,
            category=category,
            parameters=parameters,
        )
        self._commands[canonical_name] = cmd
        for alias in cmd.aliases:
            self._alias_map[alias] = canonical_name
            self._alias_map[self._normalize_name(alias)] = canonical_name

    def resolve(self, name_or_alias: str) -> CommandDef | None:
        """Найти команду по имени или алиасу."""
        candidates = [name_or_alias, self._normalize_name(name_or_alias)]
        for candidate in candidates:
            # Сначала точное совпадение
            if candidate in self._commands:
                return self._commands[candidate]
            # Потом по алиасу
            resolved = self._alias_map.get(candidate)
            if resolved:
                return self._commands.get(resolved)
        return None

    async def execute(
        self, name_or_alias: str, args: list[str] | None = None, **kwargs: Any
    ) -> str:
        """Выполнить команду по имени/алиасу."""
        cmd = self.resolve(name_or_alias)
        if not cmd:
            return f"Неизвестная команда: {name_or_alias}"
        try:
            return await cmd.handler(*(args or []), **kwargs)
        except Exception as e:
            return f"Ошибка выполнения '{cmd.name}': {e}"

    def is_command(self, text: str) -> bool:
        """Проверить, является ли текст командой (начинается с /)."""
        return text.startswith("/")

    def parse_command(self, text: str) -> tuple[str, list[str]]:
        """Разобрать текст команды на имя и аргументы.

        '/topic.new my_goal' -> ('topic.new', ['my_goal'])
        """
        parts = text.lstrip("/").split(maxsplit=-1)
        name = self._normalize_name(parts[0]) if parts else ""
        # Поддержка обоих форматов:
        # /topic.new -> topic.new
        # /topic_new -> topic.new
        args = parts[1:] if len(parts) > 1 else []
        return name, args

    def list_commands(self, category: str | None = None) -> list[CommandDef]:
        """Все зарегистрированные команды, опционально фильтруя по категории."""
        commands = list(self._commands.values())
        if category is not None:
            commands = [c for c in commands if c.category == category]
        return commands

    async def execute_validated(
        self, name_or_alias: str, params: dict[str, Any] | None = None
    ) -> str:
        """Выполнить команду с JSON Schema валидацией параметров.

        Если у команды определена JSON Schema (parameters), params валидируются
        перед вызовом handler. При ошибке валидации возвращает сообщение об ошибке.
        Не использует внешних зависимостей — встроенная валидация (required + types).
        """
        cmd = self.resolve(name_or_alias)
        if not cmd:
            return f"Неизвестная команда: {name_or_alias}"
        effective_params = params or {}
        if cmd.parameters:
            error = _validate_params(cmd.parameters, effective_params)
            if error:
                return error
        try:
            return await cmd.handler(**effective_params)
        except Exception as e:
            return f"Ошибка выполнения '{cmd.name}': {e}"

    def to_tool_definitions(self) -> list[ToolDefinition]:
        """Конвертировать зарегистрированные команды в tool definitions для LLM."""
        tools: list[ToolDefinition] = []
        for cmd in self._commands.values():
            tools.append(
                ToolDefinition(
                    name=cmd.name,
                    description=cmd.description,
                    parameters=cmd.parameters or {"type": "object", "properties": {}},
                )
            )
        return tools

    def help_text(self) -> str:
        """Сгенерировать текст справки."""
        lines = ["Доступные команды:"]
        for cmd in self._commands.values():
            display_name = cmd.name.replace(".", "_")
            aliases = (
                f" ({', '.join('/' + a.replace('.', '_') for a in cmd.aliases)})"
                if cmd.aliases
                else ""
            )
            desc = f" — {cmd.description}" if cmd.description else ""
            lines.append(f"  /{display_name}{aliases}{desc}")
        return "\n".join(lines)
