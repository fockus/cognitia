"""SummaryGenerator — генерация rolling summary из истории сообщений.

MVP: template-based (без LLM-вызова).
Позже можно заменить на LLM-based реализацию через тот же Protocol.
"""

from __future__ import annotations

from cognitia.memory.types import MemoryMessage


class TemplateSummaryGenerator:
    """Template-based генератор summary (KISS для MVP).

    Берёт последние N сообщений, обрезает длинные, формирует
    краткий текстовый пересказ в формате:
    - [user]: текст
    - [assistant]: текст
    """

    def __init__(
        self,
        max_messages: int = 20,
        max_message_chars: int = 200,
    ) -> None:
        self._max_messages = max_messages
        self._max_message_chars = max_message_chars

    def summarize(self, messages: list[MemoryMessage]) -> str:
        """Сгенерировать summary из списка сообщений.

        Args:
            messages: Список сообщений (от старых к новым).

        Returns:
            Текст summary или пустая строка если сообщений нет.
        """
        if not messages:
            return ""

        # Берём только последние N
        recent = messages[-self._max_messages :]

        lines: list[str] = []
        for msg in recent:
            content = msg.content
            if len(content) > self._max_message_chars:
                content = content[: self._max_message_chars] + "..."
            role_label = "user" if msg.role == "user" else "assistant"
            lines.append(f"- [{role_label}]: {content}")

        return "\n".join(lines)
