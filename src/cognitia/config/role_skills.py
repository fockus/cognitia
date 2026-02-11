"""YamlRoleSkillsLoader — загрузка маппинга роль→скилы из YAML.

Реализует RoleSkillsProvider Protocol (ISP: get_skills, get_local_tools).
Принимает yaml_path через DI — не привязан к конкретной структуре проекта.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class YamlRoleSkillsLoader:
    """Загрузчик маппинга role_id → skills из role_skills.yaml.

    Реализует RoleSkillsProvider Protocol.

    Args:
        yaml_path: Путь к YAML-файлу с маппингом ролей.
    """

    def __init__(self, yaml_path: Path) -> None:
        self._path = yaml_path
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Загрузить YAML-файл."""
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}

    def get_skills(self, role_id: str) -> list[str]:
        """Получить список skill_id для роли."""
        role_data = self._data.get(role_id, {})
        result: list[str] = role_data.get("skills", [])
        return result

    def get_local_tools(self, role_id: str) -> list[str]:
        """Получить список local tools для роли."""
        role_data = self._data.get(role_id, {})
        result: list[str] = role_data.get("local_tools", [])
        return result

    def list_roles(self) -> list[str]:
        """Список всех доступных ролей."""
        return list(self._data.keys())
