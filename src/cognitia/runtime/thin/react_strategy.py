"""React strategy -- loop (LLM -> tool_call | final)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from cognitia.runtime.structured_output import (
    append_structured_output_instruction,
    extract_structured_output,
)
from cognitia.runtime.thin.executor import ToolExecutor
from cognitia.runtime.thin.errors import ThinLlmError
from cognitia.runtime.thin.helpers import _build_metrics, _messages_to_lm
from cognitia.runtime.thin.llm_client import try_stream_llm_call
from cognitia.runtime.thin.parsers import extract_text_fallback, parse_envelope
from cognitia.runtime.thin.prompts import build_react_prompt
from cognitia.runtime.types import (
    Message,
    RuntimeConfig,
    RuntimeErrorData,
    RuntimeEvent,
    ToolSpec,
)


async def run_react(  # noqa: C901
    llm_call: Callable[..., Any],
    executor: ToolExecutor,
    messages: list[Message],
    system_prompt: str,
    tools: list[ToolSpec],
    config: RuntimeConfig,
    start_time: float,
) -> AsyncIterator[RuntimeEvent]:
    """React loop: LLM -> tool_call | final. С поддержкой token streaming."""
    prompt = build_react_prompt(
        append_structured_output_instruction(
            system_prompt,
            config.output_format,
            final_response_field="final_message",
        ),
        tools,
    )
    lm_messages = _messages_to_lm(messages)
    new_messages: list[Message] = []

    iterations = 0
    tool_calls_count = 0
    retries = 0
    last_raw = ""
    stream_chunks: list[str] = []

    while iterations < config.max_iterations:
        iterations += 1

        # Пробуем streaming LLM вызов, fallback на non-streaming
        try:
            stream_result = await try_stream_llm_call(llm_call, lm_messages, prompt)
            if stream_result is not None:
                stream_chunks, raw = stream_result
            else:
                raw = await llm_call(lm_messages, prompt)
                stream_chunks = []
        except ThinLlmError as exc:
            yield RuntimeEvent.error(exc.error)
            return

        last_raw = raw
        envelope = parse_envelope(raw)

        if envelope is None:
            retries += 1
            if retries > config.max_model_retries:
                fallback_text = extract_text_fallback(last_raw)
                if fallback_text:
                    new_messages.append(Message(role="assistant", content=fallback_text))
                    structured_output = extract_structured_output(
                        fallback_text,
                        config.output_format,
                    )
                    yield RuntimeEvent.status(
                        "LLM ответила не в JSON-формате, использую текстовый fallback"
                    )
                    yield RuntimeEvent.assistant_delta(fallback_text)
                    yield RuntimeEvent.final(
                        text=fallback_text,
                        new_messages=new_messages,
                        metrics=_build_metrics(
                            start_time,
                            config,
                            iterations,
                            tool_calls_count,
                        ),
                        structured_output=structured_output,
                    )
                    return
                yield RuntimeEvent.error(
                    RuntimeErrorData(
                        kind="bad_model_output",
                        message=f"LLM вернула некорректный JSON {retries} раз подряд",
                        recoverable=False,
                    )
                )
                return
            continue

        retries = 0  # Сброс при успешном парсинге

        # --- tool_call ---
        if envelope.type == "tool_call" and envelope.tool:
            tc = envelope.tool

            # Budget check
            if tool_calls_count >= config.max_tool_calls:
                yield RuntimeEvent.error(
                    RuntimeErrorData(
                        kind="budget_exceeded",
                        message=f"Превышен лимит tool_calls ({config.max_tool_calls})",
                        recoverable=False,
                    )
                )
                return

            cid = tc.correlation_id or f"c{tool_calls_count + 1}"
            yield RuntimeEvent.tool_call_started(
                name=tc.name,
                args=tc.args,
                correlation_id=cid,
            )

            # Выполняем tool
            result = await executor.execute(tc.name, tc.args)

            # Проверяем ошибку в результате
            tool_ok = True
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict) and "error" in parsed:
                    tool_ok = False
            except (json.JSONDecodeError, TypeError):
                pass

            yield RuntimeEvent.tool_call_finished(
                name=tc.name,
                correlation_id=cid,
                ok=tool_ok,
                result_summary=result[:200],
            )

            tool_calls_count += 1

            # Добавляем tool result в историю LLM
            new_messages.append(
                Message(
                    role="assistant",
                    content=tc.assistant_message if hasattr(tc, "assistant_message") else "",
                    metadata={"tool_call": tc.name},
                )
            )
            new_messages.append(
                Message(
                    role="tool",
                    content=result,
                    name=tc.name,
                )
            )
            lm_messages.append({"role": "assistant", "content": f"Вызываю {tc.name}"})
            lm_messages.append({"role": "user", "content": f"Результат {tc.name}: {result}"})

            if envelope.assistant_message:
                yield RuntimeEvent.status(envelope.assistant_message)

            continue

        # --- final ---
        if envelope.type == "final" and envelope.final_message:
            text = envelope.final_message
            new_messages.append(Message(role="assistant", content=text))
            structured_output = extract_structured_output(text, config.output_format)

            if stream_chunks:
                for chunk in stream_chunks:
                    yield RuntimeEvent.assistant_delta(chunk)
            else:
                yield RuntimeEvent.assistant_delta(text)
            yield RuntimeEvent.final(
                text=text,
                new_messages=new_messages,
                metrics=_build_metrics(
                    start_time,
                    config,
                    iterations,
                    tool_calls_count,
                ),
                structured_output=structured_output,
            )
            return

        # --- clarify ---
        if envelope.type == "clarify":
            text = envelope.assistant_message or "Уточните, пожалуйста."
            if envelope.questions:
                qs = "\n".join(f"- {q.text}" for q in envelope.questions)
                text = f"{text}\n\n{qs}"

            new_messages.append(Message(role="assistant", content=text))
            structured_output = extract_structured_output(text, config.output_format)
            if stream_chunks:
                for chunk in stream_chunks:
                    yield RuntimeEvent.assistant_delta(chunk)
            else:
                yield RuntimeEvent.assistant_delta(text)
            yield RuntimeEvent.final(
                text=text,
                new_messages=new_messages,
                metrics=_build_metrics(
                    start_time,
                    config,
                    iterations,
                    tool_calls_count,
                ),
                structured_output=structured_output,
            )
            return

    # Loop limit reached
    yield RuntimeEvent.error(
        RuntimeErrorData(
            kind="loop_limit",
            message=f"Превышен лимит итераций ({config.max_iterations})",
            recoverable=False,
        )
    )
