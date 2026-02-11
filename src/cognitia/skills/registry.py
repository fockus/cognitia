"""SkillRegistry — реестр загруженных скилов (SRP: отдельно от загрузки)."""

from __future__ import annotations

import structlog

from cognitia.skills.types import LoadedSkill, McpServerSpec

_log = structlog.get_logger(component="skill_registry")


class SkillRegistry:
    """Реестр загруженных скилов.

    settings_mcp — MCP-серверы из .claude/settings.json (нижний приоритет).
    При merge: skill.yaml перезаписывает settings.json (§2.1, R-401/R-402).
    """

    def __init__(
        self,
        skills: list[LoadedSkill] | None = None,
        settings_mcp: dict[str, McpServerSpec] | None = None,
    ) -> None:
        self._skills: dict[str, LoadedSkill] = {}
        self._settings_mcp: dict[str, McpServerSpec] = settings_mcp or {}
        if skills:
            for s in skills:
                self._skills[s.spec.skill_id] = s

    def register(self, skill: LoadedSkill) -> None:
        """Зарегистрировать скилл."""
        self._skills[skill.spec.skill_id] = skill

    def get(self, skill_id: str) -> LoadedSkill | None:
        """Получить скилл по id."""
        return self._skills.get(skill_id)

    def list_all(self) -> list[LoadedSkill]:
        """Все загруженные скилы."""
        return list(self._skills.values())

    def list_ids(self) -> list[str]:
        """Все id загруженных скилов."""
        return list(self._skills.keys())

    def get_mcp_servers_for_skills(self, skill_ids: list[str]) -> dict[str, McpServerSpec]:
        """Собрать MCP-серверы для набора скилов (§4.3, R-401/R-402).

        Merge policy: settings.json (нижний приоритет) + skill.yaml (верхний).
        skill.yaml перезаписывает settings.json при совпадении name.
        """
        # Базовый слой — MCP из settings.json
        servers: dict[str, McpServerSpec] = dict(self._settings_mcp)

        # Верхний слой — MCP из skill.yaml (перезаписывает)
        for sid in skill_ids:
            skill = self._skills.get(sid)
            if not skill:
                continue
            for srv in skill.spec.mcp_servers:
                servers[srv.name] = srv
        return servers

    def get_tool_allowlist(self, skill_ids: list[str]) -> set[str]:
        """Собрать allowlist tool ids для набора скилов."""
        tools: set[str] = set()
        for sid in skill_ids:
            skill = self._skills.get(sid)
            if not skill:
                continue
            tools.update(skill.spec.tool_include)
            tools.update(skill.spec.local_tools)
        return tools

    def validate_tools(self, available_tools: set[str]) -> list[str]:
        """Проверить, что tools.include из skill.yaml доступны (§4.4 acceptance).

        Args:
            available_tools: множество реально доступных tool_name от SDK/MCP.

        Returns:
            Список предупреждений о недоступных инструментах.
        """
        warnings: list[str] = []
        for skill in self._skills.values():
            for tool_name in skill.spec.tool_include:
                if tool_name not in available_tools:
                    msg = (
                        f"Skill '{skill.spec.skill_id}': инструмент "
                        f"'{tool_name}' не найден среди доступных MCP tools"
                    )
                    warnings.append(msg)
                    _log.warning(
                        "tool_not_available",
                        skill_id=skill.spec.skill_id,
                        tool_name=tool_name,
                    )
        if not warnings:
            _log.info(
                "tools_validated",
                total_skills=len(self._skills),
                status="all_tools_available",
            )
        return warnings
