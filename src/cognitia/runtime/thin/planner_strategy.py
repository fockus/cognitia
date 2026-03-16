"""Planner strategy -- plan JSON -> step execution -> final assembly."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from cognitia.runtime.structured_output import (
    append_structured_output_instruction,
    extract_structured_output,
)
from cognitia.runtime.thin.conversational import run_conversational
from cognitia.runtime.thin.executor import ToolExecutor
from cognitia.runtime.thin.helpers import _build_metrics, _messages_to_lm
from cognitia.runtime.thin.parsers import parse_envelope, parse_plan
from cognitia.runtime.thin.prompts import (
    build_final_assembly_prompt,
    build_plan_step_prompt,
    build_planner_prompt,
)
from cognitia.runtime.thin.react_strategy import run_react
from cognitia.runtime.types import (
    Message,
    RuntimeConfig,
    RuntimeErrorData,
    RuntimeEvent,
    ToolSpec,
)


async def run_planner(
    llm_call: Callable[..., Any],
    executor: ToolExecutor,
    messages: list[Message],
    system_prompt: str,
    tools: list[ToolSpec],
    config: RuntimeConfig,
    start_time: float,
) -> AsyncIterator[RuntimeEvent]:
    """Planner-lite: plan -> step execution -> final assembly."""
    # Шаг 1: получить план от LLM
    prompt = build_planner_prompt(system_prompt, tools)
    lm_messages = _messages_to_lm(messages)

    raw = await llm_call(lm_messages, prompt)
    plan = parse_plan(raw)

    if plan is None:
        # Retry
        raw = await llm_call(lm_messages, prompt)
        plan = parse_plan(raw)

    if plan is None:
        yield RuntimeEvent.error(
            RuntimeErrorData(
                kind="bad_model_output",
                message="LLM не вернула валидный план после 2 попыток",
                recoverable=False,
            )
        )
        return

    yield RuntimeEvent.status(f"План: {plan.goal} ({len(plan.steps)} шагов)")
    steps_preview = " -> ".join(
        f"{idx}. {step.title} [{step.mode}]" for idx, step in enumerate(plan.steps, start=1)
    )
    if steps_preview:
        yield RuntimeEvent.status(f"Следующие шаги: {steps_preview}")

    # Шаг 2: выполнить каждый шаг
    step_results: list[str] = []
    new_messages: list[Message] = []
    total_tool_calls = 0

    for idx, step in enumerate(plan.steps, start=1):
        yield RuntimeEvent.status(
            f"Шаг {idx}/{len(plan.steps)}: {step.title} (режим: {step.mode})"
        )

        step_context = "\n".join(step_results) if step_results else "Нет предыдущих шагов."

        # Формируем sub-config с бюджетами шага
        step_config = RuntimeConfig(
            runtime_name="thin",
            max_iterations=step.max_iterations,
            max_tool_calls=config.max_tool_calls - total_tool_calls,
            max_model_retries=config.max_model_retries,
            model=config.model,
        )

        step_text = ""

        if step.mode == "react":
            async for event in run_react(
                llm_call,
                executor,
                messages,
                system_prompt=build_plan_step_prompt(
                    system_prompt,
                    step.title,
                    step_context,
                    tools,
                ),
                tools=tools,
                config=step_config,
                start_time=start_time,
            ):
                # Пробрасываем tool + streaming events
                if event.type in (
                    "tool_call_started",
                    "tool_call_finished",
                    "status",
                    "assistant_delta",
                ):
                    yield event
                elif event.type == "final":
                    step_text = event.data.get("text", "")
                    total_tool_calls += event.data.get("metrics", {}).get(
                        "tool_calls_count", 0
                    )
                elif event.type == "error":
                    yield event
                    return
        else:
            # conversational sub-step
            async for event in run_conversational(
                llm_call,
                messages,
                system_prompt=build_plan_step_prompt(
                    system_prompt,
                    step.title,
                    step_context,
                    [],
                ),
                config=step_config,
                start_time=start_time,
            ):
                if event.type == "assistant_delta":
                    yield event
                elif event.type == "final":
                    step_text = event.data.get("text", "")
                elif event.type == "error":
                    yield event
                    return

        step_results.append(step_text)

    # Шаг 3: финальная сборка
    assembly_prompt = build_final_assembly_prompt(
        append_structured_output_instruction(
            system_prompt,
            config.output_format,
            final_response_field="final_message",
        ),
        plan.goal,
        step_results,
        plan.final_format,
    )
    raw = await llm_call(lm_messages, assembly_prompt)
    envelope = parse_envelope(raw)

    if envelope and envelope.type == "final" and envelope.final_message:
        final_text = envelope.final_message
    else:
        final_text = raw  # fallback

    new_messages.append(Message(role="assistant", content=final_text))
    structured_output = extract_structured_output(final_text, config.output_format)

    yield RuntimeEvent.assistant_delta(final_text)
    yield RuntimeEvent.final(
        text=final_text,
        new_messages=new_messages,
        metrics=_build_metrics(
            start_time,
            config,
            iterations=len(plan.steps) + 2,  # plan + steps + assembly
            tool_calls=total_tool_calls,
        ),
        structured_output=structured_output,
    )
