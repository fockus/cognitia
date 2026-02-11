"""ModelPolicy — политика выбора модели (Sonnet/Opus) по условиям (секция 3 архитектуры).

Триггеры переключения на Opus (секция 3.2):
- Пользователь просит «план», «стратегию», «пошагово», «дорожную карту»
- 2+ skills одновременно
- Роль из escalate_roles
- N неудачных tool calls
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Ключевые слова, триггерящие Opus (стемы для покрытия словоформ)
_OPUS_KEYWORDS: tuple[str, ...] = (
    "план",
    "стратеги",
    "пошагов",
    "дорожн",
    "разбер",
    "сравни",
)


@dataclass
class ModelPolicy:
    """Политика выбора модели.

    - default_model: модель по умолчанию (быстрая, дешёвая)
    - escalation_model: модель для сложных задач
    - escalate_roles: роли, которые всегда используют escalation_model
    - escalate_on_tool_failures: после N неудачных tool calls → escalate
    - min_skills_for_escalation: >= N одновременных skills → escalate
    """

    default_model: str = "sonnet"
    escalation_model: str = "opus"
    escalate_on_tool_failures: int = 3
    escalate_roles: set[str] = field(default_factory=set)
    min_skills_for_escalation: int = 2

    def select(self, role_id: str, tool_failure_count: int = 0) -> str:
        """Выбрать модель (обратная совместимость). DRY: делегирует в select_for_turn."""
        return self.select_for_turn(
            role_id=role_id,
            user_text="",
            tool_failure_count=tool_failure_count,
        )

    def select_for_turn(
        self,
        role_id: str,
        user_text: str,
        active_skill_count: int = 0,
        tool_failure_count: int = 0,
    ) -> str:
        """Расширенный выбор модели с keyword triggers (секция 3.2).

        Args:
            role_id: текущая роль
            user_text: текст сообщения пользователя
            active_skill_count: количество активных skills
            tool_failure_count: количество ошибок tool calls

        Returns:
            'sonnet' или 'opus'
        """
        # 1. Роль
        if role_id in self.escalate_roles:
            return self.escalation_model

        # 2. Ошибки tools
        if tool_failure_count >= self.escalate_on_tool_failures:
            return self.escalation_model

        # 3. Multi-skill
        if active_skill_count >= self.min_skills_for_escalation:
            return self.escalation_model

        # 4. Keyword triggers
        text_lower = user_text.lower()
        for kw in _OPUS_KEYWORDS:
            if kw in text_lower:
                return self.escalation_model

        return self.default_model
