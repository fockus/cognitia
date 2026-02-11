"""LLM-based SummaryGenerator — генерация rolling summary через вызов LLM.

Использует AgentRuntime.run() для генерации краткого пересказа диалога.
Fallback на TemplateSummaryGenerator при ошибке LLM.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from cognitia.memory.summarizer import TemplateSummaryGenerator
from cognitia.memory.types import MemoryMessage

logger = logging.getLogger(__name__)

_SUMMARIZE_PROMPT = """\
Создай краткий пересказ диалога (~1000-1500 символов).

Обязательно укажи:
- Ключевые факты и цифры (суммы, сроки, проценты)
- Затронутые темы
- Принятые решения и договорённости
- Текущее состояние задач

Формат: сплошной текст, не список. Пиши от третьего лица.
"""


class LlmSummaryGenerator:
    """LLM-based генератор summary.

    Принимает callable для вызова LLM (async str → str).
    Fallback на TemplateSummaryGenerator при ошибке.
    """

    def __init__(
        self,
        llm_call: Callable[..., Any] | None = None,
        fallback_max_messages: int = 10,
    ) -> None:
        """Инициализировать генератор.

        Args:
            llm_call: async callable(prompt: str, messages_text: str) -> str.
                      Если None — сразу fallback на template.
            fallback_max_messages: Макс. сообщений для fallback-суммаризатора.
        """
        self._llm_call = llm_call
        self._fallback = TemplateSummaryGenerator(max_messages=fallback_max_messages)

    def summarize(self, messages: list[MemoryMessage]) -> str:
        """Sync wrapper — для совместимости с Protocol. Делегирует в fallback.

        Для async-вызова с LLM используйте asummarize().
        """
        return self._fallback.summarize(messages)

    async def asummarize(self, messages: list[MemoryMessage]) -> str:
        """Async суммаризация через LLM с fallback.

        Args:
            messages: Список сообщений диалога (от старых к новым).

        Returns:
            Текст summary (~1000-1500 символов) или fallback template.
        """
        if not messages:
            return ""

        if not self._llm_call:
            return self._fallback.summarize(messages)

        # Формируем текст диалога для LLM
        dialog_lines: list[str] = []
        for msg in messages:
            label = "Пользователь" if msg.role == "user" else "Ассистент"
            dialog_lines.append(f"{label}: {msg.content}")
        dialog_text = "\n".join(dialog_lines)

        try:
            result = await self._llm_call(_SUMMARIZE_PROMPT, dialog_text)
            if result and len(result) > 50:
                return str(result)
            # Слишком короткий ответ — fallback
            logger.warning("LLM summary слишком короткий (%d chars), fallback", len(result or ""))
            return str(self._fallback.summarize(messages))
        except Exception:
            logger.warning("Ошибка LLM-суммаризации, fallback на template", exc_info=True)
            return str(self._fallback.summarize(messages))
