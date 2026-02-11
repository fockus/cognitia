"""Модуль скилов — SkillRegistry + типы.

YamlSkillLoader перенесён в infrastructure layer приложения.
Здесь — чистый registry без IO.
"""

import contextlib

from cognitia.skills.registry import SkillRegistry
from cognitia.skills.types import LoadedSkill, McpServerSpec, SkillSpec

# Backward-compatible re-export (deprecated — используйте loader из app layer)
with contextlib.suppress(ImportError):
    from cognitia.skills.loader import YamlSkillLoader, load_mcp_from_settings

__all__ = [
    "LoadedSkill",
    "McpServerSpec",
    "SkillRegistry",
    "SkillSpec",
]
