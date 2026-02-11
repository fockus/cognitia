"""CognitiaStack — facade для быстрой инициализации library-компонентов.

Одна точка сборки: приложение передаёт пути к config/prompts/skills,
получает готовые компоненты для wiring бизнес-логики.

YAGNI: только необходимые extension points, без "будущих" фич.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cognitia.config.role_router import RoleRouterConfig, load_role_router_config
from cognitia.config.role_skills import YamlRoleSkillsLoader
from cognitia.context import DefaultContextBuilder
from cognitia.policy import DefaultToolIdCodec, DefaultToolPolicy
from cognitia.protocols import LocalToolResolver
from cognitia.routing import KeywordRoleRouter
from cognitia.runtime.factory import RuntimeFactory
from cognitia.runtime.model_policy import ModelPolicy
from cognitia.runtime.types import RuntimeConfig
from cognitia.skills import SkillRegistry
from cognitia.skills.loader import YamlSkillLoader


@dataclass
class CognitiaStack:
    """Готовый набор library-компонентов для приложения.

    Создаётся через CognitiaStack.create() — единая фабрика.
    Все поля read-only (приложение использует, но не меняет).

    Пример использования:
        stack = CognitiaStack.create(
            prompts_dir=Path("prompts"),
            skills_dir=Path("skills"),
            project_root=Path("."),
        )
        # Далее приложение использует stack.skill_registry, stack.context_builder, etc.
    """

    skill_registry: SkillRegistry
    context_builder: DefaultContextBuilder
    role_skills_loader: YamlRoleSkillsLoader
    role_router: KeywordRoleRouter
    role_router_config: RoleRouterConfig
    tool_policy: DefaultToolPolicy
    tool_id_codec: DefaultToolIdCodec
    model_policy: ModelPolicy
    runtime_factory: RuntimeFactory
    runtime_config: RuntimeConfig
    local_tool_resolver: LocalToolResolver | None

    @classmethod
    def create(
        cls,
        *,
        prompts_dir: Path,
        skills_dir: Path,
        project_root: Path,
        escalate_roles: set[str] | None = None,
        runtime_config: RuntimeConfig | None = None,
        local_tool_resolver: LocalToolResolver | None = None,
    ) -> CognitiaStack:
        """Создать все library-компоненты из путей к config.

        Args:
            prompts_dir: Директория с промптами (identity.md, guardrails.md, roles/).
            skills_dir: Директория со скилами (skill.yaml + INSTRUCTION.md).
            project_root: Корень проекта (для .claude/settings.json).
            escalate_roles: Роли для эскалации модели (например, {"strategy_planner"}).
            runtime_config: Конфиг runtime (runtime/model/base_url) из app.
            local_tool_resolver: App-level резолвер локальных инструментов.

        Returns:
            CognitiaStack с готовыми компонентами.
        """
        # Skills
        skill_loader = YamlSkillLoader(skills_dir, project_root=project_root)
        loaded_skills = skill_loader.load_all()
        skill_registry = SkillRegistry(
            loaded_skills,
            settings_mcp=skill_loader.settings_mcp_servers,
        )

        # Context
        context_builder = DefaultContextBuilder(prompts_dir)

        # Role config
        role_skills_loader = YamlRoleSkillsLoader(
            prompts_dir / "role_skills.yaml",
        )
        router_config = load_role_router_config(
            prompts_dir / "role_router.yaml",
        )
        role_router = KeywordRoleRouter(
            default_role=router_config.default_role,
            keyword_map=router_config.keywords,
        )

        # Policy
        tool_id_codec = DefaultToolIdCodec()
        tool_policy = DefaultToolPolicy(
            codec=tool_id_codec,
        )

        # Model policy
        model_policy = ModelPolicy(
            escalate_roles=escalate_roles or set(),
        )

        # Runtime factory
        runtime_factory = RuntimeFactory()
        runtime_cfg = runtime_config or RuntimeConfig()

        return cls(
            skill_registry=skill_registry,
            context_builder=context_builder,
            role_skills_loader=role_skills_loader,
            role_router=role_router,
            role_router_config=router_config,
            tool_policy=tool_policy,
            tool_id_codec=tool_id_codec,
            model_policy=model_policy,
            runtime_factory=runtime_factory,
            runtime_config=runtime_cfg,
            local_tool_resolver=local_tool_resolver,
        )
