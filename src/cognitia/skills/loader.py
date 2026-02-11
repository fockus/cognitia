"""YamlSkillLoader — загрузка скилов из skills/*.yaml файлов.

§4.3: Если MCP-серверы уже описаны в .claude/settings.json,
SkillLoader нормализует их и дополняет настройками из skills/*.yaml.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from cognitia.skills.types import LoadedSkill, McpServerSpec, SkillSpec


def load_mcp_from_settings(project_root: Path) -> dict[str, McpServerSpec]:
    """Загрузить MCP-серверы из .claude/settings.json (§4.3, R-401).

    Ищет mcpServers в project-level и user-level settings.
    """
    servers: dict[str, McpServerSpec] = {}

    # Приоритет: project -> user (project перезаписывает)
    paths = [
        Path.home() / ".claude" / "settings.json",
        project_root / ".claude" / "settings.json",
        project_root / ".claude" / "settings.local.json",
    ]

    for settings_path in paths:
        if not settings_path.exists():
            continue
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            mcp_section = data.get("mcpServers", {})
            for name, cfg in mcp_section.items():
                transport = cfg.get("type", "url")
                servers[name] = McpServerSpec(
                    name=name,
                    transport=transport,
                    url=cfg.get("url"),
                    command=cfg.get("command"),
                    args=cfg.get("args"),
                    env=cfg.get("env"),
                )
        except (json.JSONDecodeError, OSError):
            continue

    return servers


class YamlSkillLoader:
    """Загружает скилы из директории skills/.

    §4.3: при наличии .claude/settings.json нормализует MCP серверы
    и дополняет настройками из skills/*.yaml (yaml имеет приоритет §2.1).
    """

    def __init__(
        self,
        skills_dir: str | Path,
        project_root: str | Path | None = None,
    ) -> None:
        self._dir = Path(skills_dir)
        self._project_root = Path(project_root) if project_root else self._dir.parent

    def load_all(self) -> list[LoadedSkill]:
        """Загрузить все скилы из поддиректорий skills/.

        §4.3: также загружает MCP из .claude/settings.json,
        skill.yaml дополняет/перезаписывает (§2.1 приоритет).
        """
        # Загружаем MCP из settings (нижний приоритет)
        self._settings_mcp = load_mcp_from_settings(self._project_root)

        skills: list[LoadedSkill] = []
        if not self._dir.exists():
            return skills

        for skill_dir in sorted(self._dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            yaml_file = skill_dir / "skill.yaml"
            if not yaml_file.exists():
                continue
            skill = self._load_one(skill_dir, yaml_file)
            if skill:
                skills.append(skill)
        return skills

    @property
    def settings_mcp_servers(self) -> dict[str, McpServerSpec]:
        """MCP серверы загруженные из .claude/settings.json."""
        return getattr(self, "_settings_mcp", {})

    def _load_one(self, skill_dir: Path, yaml_file: Path) -> LoadedSkill | None:
        """Загрузить один скилл из YAML + instruction markdown."""
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        skill_id = data.get("id", skill_dir.name)
        title = data.get("title", skill_id)

        # Парсим MCP серверы
        mcp_servers: list[McpServerSpec] = []
        mcp_section = data.get("mcp", {})
        for srv in mcp_section.get("servers", []):
            mcp_servers.append(
                McpServerSpec(
                    name=srv.get("id", srv.get("name", "")),
                    transport=srv.get("transport", "url"),
                    url=srv.get("url"),
                    command=srv.get("command"),
                    args=srv.get("args"),
                    env=srv.get("env"),
                )
            )

        # Tool include list
        tools_section = data.get("tools", {})
        tool_include = tools_section.get("include", [])

        # Local tools
        local_tools = data.get("local_tools", [])

        # Intents (для role routing)
        when_section = data.get("when", {})
        intents = when_section.get("intents", [])

        # Instruction file
        instruction_file = data.get("instruction", f"skills/{skill_id}/INSTRUCTION.md")
        instruction_path = self._dir.parent / instruction_file
        if not instruction_path.exists():
            # Пробуем относительно skill_dir
            instruction_path = skill_dir / "INSTRUCTION.md"

        instruction_md = ""
        if instruction_path.exists():
            instruction_md = instruction_path.read_text(encoding="utf-8")

        spec = SkillSpec(
            skill_id=skill_id,
            title=title,
            instruction_file=instruction_file,
            mcp_servers=mcp_servers,
            tool_include=tool_include,
            local_tools=local_tools,
            intents=intents,
        )
        return LoadedSkill(spec=spec, instruction_md=instruction_md)


# SkillRegistry вынесен в skills/registry.py (SRP)
