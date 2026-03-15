"""Конфигурации code pipeline для multi-agent orchestration.

Все конфиги — frozen dataclass (pure value objects, 0 зависимостей).
Factory methods предоставляют типовые пресеты.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class CodingStandardsConfig:
    """Стандарты кода — все флаги OFF по умолчанию.

    Декларативно задаёт обязательные практики для code task:
    TDD, SOLID, DRY, KISS, Clean Architecture, тесты, coverage.
    """

    tdd_enabled: bool = False
    solid_enabled: bool = False
    dry_enabled: bool = False
    kiss_enabled: bool = False
    clean_arch_enabled: bool = False
    integration_tests_required: bool = False
    e2e_tests_required: bool = False
    min_coverage_pct: int = 0

    @classmethod
    def strict(cls) -> CodingStandardsConfig:
        """All checks ON, 95% coverage."""
        return cls(
            tdd_enabled=True,
            solid_enabled=True,
            dry_enabled=True,
            kiss_enabled=True,
            clean_arch_enabled=True,
            integration_tests_required=True,
            e2e_tests_required=True,
            min_coverage_pct=95,
        )

    @classmethod
    def minimal(cls) -> CodingStandardsConfig:
        """Only TDD + basic coverage (70%)."""
        return cls(tdd_enabled=True, min_coverage_pct=70)

    @classmethod
    def off(cls) -> CodingStandardsConfig:
        """All OFF — exploratory mode."""
        return cls()


@dataclass(slots=True, frozen=True)
class WorkflowAutomationConfig:
    """Автоматизация workflow — какие шаги pipeline автоматические.

    Определяет lint, format, test, commit, review автоматизацию.
    """

    auto_lint: bool = False
    auto_format: bool = False
    auto_test: bool = False
    auto_commit: bool = False
    auto_review: bool = False

    @classmethod
    def full(cls) -> WorkflowAutomationConfig:
        """All automation ON."""
        return cls(
            auto_lint=True,
            auto_format=True,
            auto_test=True,
            auto_commit=True,
            auto_review=True,
        )

    @classmethod
    def light(cls) -> WorkflowAutomationConfig:
        """Only lint + format + test."""
        return cls(auto_lint=True, auto_format=True, auto_test=True)

    @classmethod
    def off(cls) -> WorkflowAutomationConfig:
        """All automation OFF."""
        return cls()


@dataclass(slots=True, frozen=True)
class AutonomousLoopConfig:
    """Параметры автономного цикла выполнения агентом.

    max_cost_credits=0 означает «без ограничения по кредитам».
    """

    max_iterations: int = 10
    max_cost_credits: int = 0
    stop_on_failure: bool = True
    require_approval: bool = True

    @classmethod
    def strict(cls) -> AutonomousLoopConfig:
        """Conservative: low iterations, approval required, stop on failure."""
        return cls(max_iterations=5, stop_on_failure=True, require_approval=True)

    @classmethod
    def light(cls) -> AutonomousLoopConfig:
        """Relaxed: more iterations, no approval, continue on failure."""
        return cls(
            max_iterations=20,
            stop_on_failure=False,
            require_approval=False,
        )


@dataclass(slots=True, frozen=True)
class TeamAgentsConfig:
    """Конфигурация team agents — какие роли активны в команде."""

    use_architect: bool = True
    use_developer: bool = True
    use_tester: bool = True
    use_reviewer: bool = True
    max_parallel_agents: int = 3


@dataclass(slots=True, frozen=True)
class CodePipelineConfig:
    """Агрегат конфигурации code pipeline.

    Объединяет стандарты кода, автоматизацию workflow,
    параметры автономного цикла и team agents.
    """

    standards: CodingStandardsConfig = field(default_factory=CodingStandardsConfig)
    workflow: WorkflowAutomationConfig = field(default_factory=WorkflowAutomationConfig)
    loop: AutonomousLoopConfig = field(default_factory=AutonomousLoopConfig)
    team: TeamAgentsConfig = field(default_factory=TeamAgentsConfig)

    @classmethod
    def production(cls) -> CodePipelineConfig:
        """Production preset: strict standards, full automation, conservative loop."""
        return cls(
            standards=CodingStandardsConfig.strict(),
            workflow=WorkflowAutomationConfig.full(),
            loop=AutonomousLoopConfig.strict(),
        )

    @classmethod
    def development(cls) -> CodePipelineConfig:
        """Development preset: minimal standards, light automation, relaxed loop."""
        return cls(
            standards=CodingStandardsConfig.minimal(),
            workflow=WorkflowAutomationConfig.light(),
            loop=AutonomousLoopConfig.light(),
        )
