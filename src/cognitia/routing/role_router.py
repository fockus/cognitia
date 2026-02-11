"""RoleRouter — маршрутизация пользователя к нужной роли (секция 7 архитектуры).

Стратегия MVP:
1. Явная команда (/role credit) — всегда приоритет
2. Keyword/regex эвристика по тексту пользователя
3. Fallback на default_role
"""

from __future__ import annotations


class KeywordRoleRouter:
    """Keyword-based маршрутизатор ролей.

    Принимает маппинг role_id → список ключевых слов.
    Проверяет текст пользователя на вхождение ключевых слов (case-insensitive).
    """

    def __init__(
        self,
        default_role: str = "default",
        keyword_map: dict[str, list[str]] | None = None,
    ) -> None:
        self._default = default_role
        # Нормализуем: все keywords в lowercase
        self._map: list[tuple[str, list[str]]] = []
        if keyword_map:
            for role_id, keywords in keyword_map.items():
                self._map.append((role_id, [kw.lower() for kw in keywords]))

    def resolve(
        self,
        user_text: str,
        explicit_role: str | None = None,
    ) -> str:
        """Определить роль по тексту пользователя.

        Args:
            user_text: текст сообщения пользователя
            explicit_role: явно указанная роль (из /role команды) — приоритет

        Returns:
            role_id для использования в текущем turn
        """
        # Шаг 1: явная команда побеждает всё
        if explicit_role:
            return explicit_role

        # Шаг 2: keyword match
        text_lower = user_text.lower()
        if not text_lower.strip():
            return self._default

        for role_id, keywords in self._map:
            for kw in keywords:
                if kw in text_lower:
                    return role_id

        # Шаг 3: fallback
        return self._default
