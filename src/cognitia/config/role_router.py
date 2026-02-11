"""Загрузчик конфигурации KeywordRoleRouter из YAML.

Возвращает typed dataclass RoleRouterConfig вместо raw dict.
Принимает yaml_path через DI — не привязан к конкретной структуре проекта.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RoleRouterConfig:
    """Typed конфигурация для KeywordRoleRouter.

    Attributes:
        default_role: Роль по умолчанию (если ни одно ключевое слово не совпало).
        keywords: Маппинг role_id → список ключевых слов для автоматического переключения.
    """

    default_role: str = "default"
    keywords: dict[str, list[str]] = field(default_factory=dict)


def load_role_router_config(yaml_path: Path) -> RoleRouterConfig:
    """Загрузить конфигурацию роутера из YAML.

    Args:
        yaml_path: Путь к YAML-файлу role_router.yaml.

    Returns:
        RoleRouterConfig с default_role и keywords.
    """
    if not yaml_path.exists():
        return RoleRouterConfig()

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return RoleRouterConfig(
        default_role=data.get("default_role", "default"),
        keywords=data.get("keywords", {}),
    )
