"""cognitia.pipeline — universal pipeline layer for agent graph orchestration.

Provides phase-based execution with quality gates, budget tracking,
circuit breakers, and a fluent builder API.

Quick start::

    from cognitia.pipeline import PipelineBuilder, BudgetPolicy

    pipeline = await (
        PipelineBuilder()
        .with_agents_from_yaml("org.yaml")
        .with_runner(my_llm_runner)
        .add_phase("plan", "Planning", "Decompose the goal into tasks")
        .add_phase("exec", "Execution", "Execute all planned tasks")
        .with_budget(BudgetPolicy(max_total_usd=10.0))
        .build()
    )
    result = await pipeline.run("Build a REST API")
"""

from cognitia.pipeline.budget import BudgetExceededError, BudgetTracker
from cognitia.pipeline.builder import PipelineBuilder
from cognitia.pipeline.gate import CallbackGate, CompositeGate
from cognitia.pipeline.pipeline import Pipeline
from cognitia.pipeline.protocols import CostTracker, GoalDecomposer, QualityGate
from cognitia.pipeline.runner import PipelineRunner
from cognitia.pipeline.types import (
    BudgetPolicy,
    CostRecord,
    GateResult,
    Goal,
    PhaseResult,
    PhaseStatus,
    PipelinePhase,
    PipelineResult,
)

__all__ = [
    "BudgetExceededError",
    "BudgetPolicy",
    "BudgetTracker",
    "CallbackGate",
    "CompositeGate",
    "CostRecord",
    "CostTracker",
    "GateResult",
    "Goal",
    "GoalDecomposer",
    "PhaseResult",
    "PhaseStatus",
    "Pipeline",
    "PipelineBuilder",
    "PipelinePhase",
    "PipelineResult",
    "PipelineRunner",
    "QualityGate",
]
