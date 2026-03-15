"""CodeWorkflowEngine — structured code pipeline with DoD verification loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cognitia.orchestration.code_verifier import CodeVerifier
from cognitia.orchestration.dod_state_machine import DoDStateMachine, DoDStatus


class WorkflowStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    DOD_NOT_MET = "dod_not_met"


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    """Result of a full code workflow run."""

    status: WorkflowStatus
    output: str = ""
    dod_log: str = ""
    loop_count: int = 0


class PlannerMode:
    """Pluggable planner — generates execution plan from goal."""

    async def create_plan(self, goal: str) -> str:
        return f"Plan for: {goal}"

    async def execute_plan(self, plan: str) -> str:
        return f"Executed: {plan}"


class CodeWorkflowEngine:
    """Structured code pipeline: plan → execute_tdd → verify_dod → loop.

    Integrates CodeVerifier and DoDStateMachine for criteria-driven development.
    """

    def __init__(
        self,
        verifier: CodeVerifier,
        dod: DoDStateMachine,
        planner: PlannerMode,
    ) -> None:
        self._verifier = verifier
        self._dod = dod
        self._planner = planner

    async def run(self, goal: str, dod_criteria: tuple[str, ...] = ()) -> WorkflowResult:
        """Execute full workflow: plan → execute → verify DoD."""
        plan = await self._planner.create_plan(goal)
        output = await self._planner.execute_plan(plan)

        if not dod_criteria:
            return WorkflowResult(
                status=WorkflowStatus.SUCCESS,
                output=output,
            )

        dod_result = await self._dod.verify_dod(dod_criteria, self._verifier)

        if dod_result.status == DoDStatus.PASSED:
            return WorkflowResult(
                status=WorkflowStatus.SUCCESS,
                output=output,
                dod_log=dod_result.verification_log,
                loop_count=dod_result.loop_count,
            )

        return WorkflowResult(
            status=WorkflowStatus.DOD_NOT_MET,
            output=output,
            dod_log=dod_result.verification_log,
            loop_count=dod_result.loop_count,
        )
