"""CommandRegistry — реестр команд для CLI и Telegram."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

# Тип обработчика команды
CommandHandler = Callable[..., Awaitable[str]]


@dataclass
class CommandDef:
    """Определение команды."""

    name: str
    handler: CommandHandler
    aliases: list[str] = field(default_factory=list)
    description: str = ""


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
    ) -> None:
        """Зарегистрировать команду."""
        canonical_name = self._normalize_name(name)
        cmd = CommandDef(
            name=canonical_name,
            handler=handler,
            aliases=aliases or [],
            description=description,
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

    def list_commands(self) -> list[CommandDef]:
        """Все зарегистрированные команды."""
        return list(self._commands.values())

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
