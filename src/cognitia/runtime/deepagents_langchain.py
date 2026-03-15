"""LangChain compatibility helpers для DeepAgents runtime."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from cognitia.runtime.types import Message, RuntimeErrorData, RuntimeEvent


def check_langchain_available() -> RuntimeErrorData | None:
    """Проверить наличие DeepAgents/LangChain baseline deps."""
    try:
        import deepagents  # noqa: F401
        import langchain_core  # noqa: F401

        return None
    except ImportError:
        return RuntimeErrorData(
            kind="dependency_missing",
            message=(
                "deepagents и/или langchain-core не установлены. "
                "Установите: pip install cognitia[deepagents]"
            ),
            recoverable=False,
        )


def build_langchain_messages(
    messages: list[Message],
    system_prompt: str,
    *,
    include_system_prompt: bool = True,
) -> list[Any]:
    """Конвертировать cognitia Message → LangChain messages."""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    lc_messages: list[Any] = []
    if include_system_prompt:
        lc_messages.append(SystemMessage(content=system_prompt))
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            lc_messages.append(SystemMessage(content=msg.content))
    return lc_messages


async def stream_langchain_runtime_events(
    *,
    runnable: Any,
    lc_messages: list[Any],
) -> AsyncIterator[RuntimeEvent]:
    """Стримить через LangChain compatibility path."""
    tool_correlation: dict[str, str] = {}

    async for event in runnable.astream_events(lc_messages, version="v2"):
        kind = event.get("event", "")

        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, str) and content:
                    yield RuntimeEvent.assistant_delta(content)

        elif kind == "on_tool_start":
            tool_name = event.get("name", "")
            tool_input = event.get("data", {}).get("input", {})
            run_id = event.get("run_id", "")
            started_event = RuntimeEvent.tool_call_started(
                name=tool_name,
                args=tool_input if isinstance(tool_input, dict) else {},
            )
            correlation_id = started_event.data.get("correlation_id", "")
            if run_id:
                tool_correlation[run_id] = correlation_id
            yield started_event

        elif kind == "on_tool_end":
            tool_name = event.get("name", "")
            run_id = event.get("run_id", "")
            correlation_id = tool_correlation.pop(run_id, run_id[:8])
            output = event.get("data", {}).get("output", "")
            result_str = str(output) if output else ""
            yield RuntimeEvent.tool_call_finished(
                name=tool_name,
                correlation_id=correlation_id,
                result_summary=result_str[:500],
            )
