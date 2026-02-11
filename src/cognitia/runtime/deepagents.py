"""DeepAgentsRuntime — LangChain Deep Agents runtime под AgentRuntime v1 контракт.

Особенности:
- Optional dependency: langchain-core, langchain-anthropic
- НЕ использует built-in tools DeepAgents (file/todo/execute/task)
- Только наши tools (после ToolPolicy): active_tools → LangChain BaseTool wrappers
- История не хранится внутри LangGraph: messages приходят извне
- Стриминг нормализуется в RuntimeEvent
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from cognitia.runtime.types import (
    Message,
    RuntimeConfig,
    RuntimeErrorData,
    RuntimeEvent,
    ToolSpec,
    TurnMetrics,
)

# Built-in tools DeepAgents, которые ЯВНО НЕ ДОБАВЛЯЕМ
_DEEPAGENTS_BUILTIN_TOOLS = frozenset(
    {
        "Read",
        "Write",
        "Edit",
        "MultiEdit",
        "Bash",
        "Glob",
        "Grep",
        "LS",
        "TodoRead",
        "TodoWrite",
        "WebFetch",
        "WebSearch",
        "Task",
        "AskQuestion",
    }
)


def _check_langchain_available() -> RuntimeErrorData | None:
    """Проверить наличие langchain deps. None = всё ок."""
    try:
        import langchain_anthropic  # noqa: F401
        import langchain_core  # noqa: F401

        return None
    except ImportError:
        return RuntimeErrorData(
            kind="dependency_missing",
            message=(
                "langchain-core и/или langchain-anthropic не установлены. "
                "Установите: pip install cognitia[deepagents]"
            ),
            recoverable=False,
        )


def create_langchain_tool(spec: ToolSpec, executor: Callable | None = None) -> Any:
    """Обернуть ToolSpec в LangChain StructuredTool.

    Args:
        spec: Описание инструмента.
        executor: Функция-исполнитель (для local tools).
                  Если None — заглушка (для MCP tools обработка идёт отдельно).

    Returns:
        langchain_core.tools.StructuredTool
    """
    from langchain_core.tools import StructuredTool

    async def _noop(**kwargs: Any) -> str:
        return json.dumps({"error": f"Tool {spec.name} не имеет executor"})

    async def _call_executor(**kwargs: Any) -> str:
        if executor is None:
            return await _noop(**kwargs)

        try:
            # Предпочтительный путь: executor(**kwargs)
            result = executor(**kwargs)
        except TypeError:
            # Backward compat: часть local tools имеет сигнатуру executor(args: dict)
            result = executor(kwargs)

        if hasattr(result, "__await__"):
            result = await result

        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, default=str)

    return StructuredTool.from_function(
        coroutine=_call_executor,
        name=spec.name,
        description=spec.description,
        args_schema=None,  # используем raw dict
    )


class DeepAgentsRuntime:
    """AgentRuntime обёртка над LangChain для Deep Agents.

    НЕ использует built-in tools DeepAgents.
    Только наши tools из active_tools (после ToolPolicy).
    """

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        tool_executors: dict[str, Callable] | None = None,
    ) -> None:
        """Инициализировать runtime.

        Args:
            config: Конфигурация runtime.
            tool_executors: Маппинг tool_name → async callable для local tools.
        """
        self._config = config or RuntimeConfig(runtime_name="deepagents")
        self._tool_executors = tool_executors or {}

    async def run(
        self,
        *,
        messages: list[Message],
        system_prompt: str,
        active_tools: list[ToolSpec],
        config: RuntimeConfig | None = None,
        mode_hint: str | None = None,
    ) -> AsyncIterator[RuntimeEvent]:
        """Выполнить turn через LangChain.

        Фильтрует built-in tools, конвертирует в LangChain формат,
        вызывает модель, нормализует стрим в RuntimeEvent.
        """
        # Проверяем deps
        dep_error = _check_langchain_available()
        if dep_error:
            yield RuntimeEvent.error(dep_error)
            return

        effective_config = config or self._config

        # Фильтруем built-in tools — ТОЛЬКО наши
        safe_tools = [t for t in active_tools if t.name not in _DEEPAGENTS_BUILTIN_TOOLS]

        full_text = ""
        tool_calls: list[dict[str, Any]] = []

        try:
            async for event in self._stream_langchain(
                messages=messages,
                system_prompt=system_prompt,
                tools=safe_tools,
                model=effective_config.model,
                base_url=effective_config.base_url,
            ):
                # Пробрасываем tool events и assistant_delta напрямую
                yield event
                if event.type == "assistant_delta":
                    full_text += str(event.data.get("text", ""))
                elif event.type == "tool_call_finished":
                    tool_calls.append(event.data)

        except Exception as e:
            yield RuntimeEvent.error(
                RuntimeErrorData(
                    kind="runtime_crash",
                    message=f"Ошибка LangChain: {e}",
                    recoverable=False,
                )
            )
            return

        # Формируем new_messages
        new_messages = [Message(role="assistant", content=full_text)]

        yield RuntimeEvent.final(
            text=full_text,
            new_messages=new_messages,
            metrics=TurnMetrics(
                model=effective_config.model,
                tool_calls_count=len(tool_calls),
            ),
        )

    def _build_lc_messages(
        self,
        messages: list[Message],
        system_prompt: str,
    ) -> list[Any]:
        """Конвертировать cognitia Message → LangChain messages."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        lc_messages: list[Any] = [SystemMessage(content=system_prompt)]
        for msg in messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                lc_messages.append(SystemMessage(content=msg.content))
        return lc_messages

    def _build_llm(self, model: str, base_url: str | None = None) -> Any:
        """Создать ChatAnthropic с поддержкой base_url."""
        from langchain_anthropic import ChatAnthropic

        llm_kwargs: dict[str, Any] = {"model": model}
        if base_url:
            llm_kwargs["base_url"] = base_url
        return ChatAnthropic(**llm_kwargs)

    async def _stream_langchain(
        self,
        messages: list[Message],
        system_prompt: str,
        tools: list[ToolSpec],
        model: str,
        base_url: str | None = None,
    ) -> AsyncIterator[RuntimeEvent]:
        """Стримить через LangChain astream_events.

        Yield'ит RuntimeEvent: assistant_delta, tool_call_started, tool_call_finished.
        """
        lc_messages = self._build_lc_messages(messages, system_prompt)

        # Создаём LangChain tools
        lc_tools = []
        for spec in tools:
            executor = self._tool_executors.get(spec.name)
            lc_tools.append(create_langchain_tool(spec, executor))

        llm = self._build_llm(model, base_url)

        if lc_tools:
            runnable = llm.bind_tools(lc_tools)
        else:
            runnable = llm

        # Маппинг run_id → correlation_id для связки started/finished events
        tool_correlation: dict[str, str] = {}

        # astream_events v2 для получения tool events + text streaming
        async for event in runnable.astream_events(lc_messages, version="v2"):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                # Текстовый chunk от модели
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
                # Сохраняем correlation_id для finished event
                cid = started_event.data.get("correlation_id", "")
                if run_id:
                    tool_correlation[run_id] = cid
                yield started_event

            elif kind == "on_tool_end":
                tool_name = event.get("name", "")
                run_id = event.get("run_id", "")
                cid = tool_correlation.pop(run_id, run_id[:8])
                output = event.get("data", {}).get("output", "")
                result_str = str(output) if output else ""
                yield RuntimeEvent.tool_call_finished(
                    name=tool_name,
                    correlation_id=cid,
                    result_summary=result_str[:500],
                )

    async def cleanup(self) -> None:
        """Нечего очищать — LangChain stateless."""

    @staticmethod
    def filter_builtin_tools(tools: list[ToolSpec]) -> list[ToolSpec]:
        """Отфильтровать built-in tools DeepAgents. Public для тестирования."""
        return [t for t in tools if t.name not in _DEEPAGENTS_BUILTIN_TOOLS]
