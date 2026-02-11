"""Pydantic-схемы для structured output ThinRuntime.

ActionEnvelope — ответ LLM (tool_call | final | clarify).
PlanSchema / PlanStep — planner-lite JSON plan.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# ActionEnvelope — ответ LLM в одном из трёх вариантов
# ---------------------------------------------------------------------------


class ToolCallAction(BaseModel):
    """Вариант A: вызов инструмента."""

    name: str = Field(..., description="Полное имя инструмента (mcp__server__tool)")
    args: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = Field(default="")


class FinalAction(BaseModel):
    """Вариант B: финальный ответ."""

    final_message: str = Field(..., description="Полный ответ пользователю")
    citations: list[str] = Field(default_factory=list)
    next_suggestions: list[str] = Field(default_factory=list)


class ClarifyQuestion(BaseModel):
    """Один вопрос для уточнения."""

    id: str
    text: str


class ClarifyAction(BaseModel):
    """Вариант C: уточнение (не хватает данных)."""

    questions: list[ClarifyQuestion] = Field(..., min_length=1)
    assistant_message: str = Field(default="")


class ActionEnvelope(BaseModel):
    """Конверт ответа LLM — ровно один из вариантов.

    type: "tool_call" | "final" | "clarify"
    """

    type: str = Field(..., pattern=r"^(tool_call|final|clarify)$")

    # Вариант A: tool_call
    tool: ToolCallAction | None = None

    # Вариант B: final
    final_message: str | None = None
    citations: list[str] = Field(default_factory=list)
    next_suggestions: list[str] = Field(default_factory=list)

    # Вариант C: clarify
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    assistant_message: str = Field(default="")

    def get_tool_call(self) -> ToolCallAction:
        """Извлечь tool_call. Raises ValueError если type != tool_call."""
        if self.type != "tool_call" or self.tool is None:
            raise ValueError("ActionEnvelope.type != 'tool_call'")
        return self.tool

    def get_final(self) -> FinalAction:
        """Извлечь final. Raises ValueError если type != final."""
        if self.type != "final" or self.final_message is None:
            raise ValueError("ActionEnvelope.type != 'final'")
        return FinalAction(
            final_message=self.final_message,
            citations=self.citations,
            next_suggestions=self.next_suggestions,
        )

    def get_clarify(self) -> ClarifyAction:
        """Извлечь clarify. Raises ValueError если type != clarify."""
        if self.type != "clarify" or not self.questions:
            raise ValueError("ActionEnvelope.type != 'clarify'")
        return ClarifyAction(
            questions=self.questions,
            assistant_message=self.assistant_message,
        )


# ---------------------------------------------------------------------------
# PlanSchema — planner-lite JSON plan
# ---------------------------------------------------------------------------


class PlanStep(BaseModel):
    """Один шаг плана."""

    id: str
    title: str
    mode: str = Field(default="react", pattern=r"^(conversational|react)$")
    tool_hints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=4, ge=1, le=20)


class PlanSchema(BaseModel):
    """JSON-план от LLM для planner-lite режима.

    type: "plan"
    """

    type: str = Field(default="plan", pattern=r"^plan$")
    goal: str
    steps: list[PlanStep] = Field(..., min_length=1)
    final_format: str = Field(default="")
