"""Config — generic загрузчики конфигурации (YAML loaders, typed configs).

Модуль предоставляет domain-agnostic загрузчики для:
- role → skills маппинга (RoleSkillsLoader, реализует RoleSkillsProvider Protocol)
- role router конфигурации (RoleRouterConfig, load_role_router_config)
"""

from cognitia.config.role_router import RoleRouterConfig, load_role_router_config
from cognitia.config.role_skills import YamlRoleSkillsLoader

__all__ = [
    "RoleRouterConfig",
    "YamlRoleSkillsLoader",
    "load_role_router_config",
]
