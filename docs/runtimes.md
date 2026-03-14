# Runtimes

Cognitia поддерживает три runtime. Все реализуют единый `AgentRuntime` Protocol — переключение без изменения бизнес-кода.

## Сравнение

| | Claude SDK | ThinRuntime | DeepAgents |
|--|-----------|-------------|------------|
| **LLM** | Claude (через SDK subprocess) | Anthropic + OpenAI-compatible `base_url` | Anthropic baseline; OpenAI/Google через provider package |
| **MCP** | Нативная поддержка | Встроенный MCP client | Не входит в portable baseline |
| **Sandbox** | Нативные Read/Write/Bash | Через SandboxProvider | Через SandboxProvider |
| **Planning** | Нативный plan mode | ThinPlannerMode | DeepAgentsPlannerMode |
| **Subagents** | Нативный Task tool | asyncio.Task | Native `task` / LangGraph |
| **Team mode** | ClaudeTeamOrchestrator | (backlog) | DeepAgentsTeamOrchestrator |
| **Extras** | `cognitia[claude]` | `cognitia[thin]` | `cognitia[deepagents]` |
| **Offline** | Нет | Да (через local/proxy `base_url`) | Зависит от provider/local endpoint, не гарантируется |

## Portable matrix (текущее покрытие)

- Offline portable baseline подтверждён integration-матрицей для `claude_sdk` и `deepagents`:
  - `Agent.query()`
  - `Agent.stream()`
  - `Conversation.say()`
- `deepagents` native built-ins и store/resume surface покрыты offline graph-тестами отдельно от portable matrix.
- `thin` остаётся `light` tier и не считается целью полной parity с `claude_sdk` / `deepagents`.
- Provider-specific risk, зафиксированный живым smoke:
  - `Gemini + DeepAgents built-ins` на tool-heavy prompts пока остаётся нестабильным provider-specific path. Для минимального migration cost используйте `feature_mode="portable"`.

## Claude SDK Runtime

Использует Claude Agent SDK subprocess. Нативная поддержка MCP, tools, subagents.

```python
config = RuntimeConfig(runtime_name="claude_sdk", model="claude-sonnet-4-20250514")
```

### Когда использовать

- Нужна полная интеграция с Claude ecosystem
- Нативные MCP серверы
- Subagents через Task tool

### Особенности

- SDK управляет subprocess'ом — cognitia нормализует events
- `permission_mode` конфигурируемый, default — `bypassPermissions`
- `allowed_system_tools` whitelist разрешает нативные Read/Write для sandbox

## ThinRuntime

Собственная lightweight реализация. Прямые вызовы API без subprocess.

```python
config = RuntimeConfig(runtime_name="thin", model="claude-sonnet-4-20250514")
```

### Когда использовать

- Максимальный контроль над поведением
- Альтернативные LLM (через `base_url`)
- Простые проекты без MCP

### Режимы

- `conversational` — обычный chat (без tools)
- `react` — ReAct loop (tool calls → results → next iteration)
- `planner` — plan-then-execute

### Особенности

- Встроенный MCP client (STDIO)
- ToolExecutor для local/builtin tools
- Streaming через `async for event in runtime.run(...)`

## DeepAgents Runtime

Интеграция через native DeepAgents graph path с portable facade поверх него.

```python
config = RuntimeConfig(runtime_name="deepagents", model="claude-sonnet-4-20250514")
```

### Когда использовать

- Нужны DeepAgents/LangGraph graphs, built-ins и store-backed sessions
- Multi-agent workflows
- Нужен full-tier runtime, но Claude-specific SDK path не подходит

### Особенности

- `feature_mode="portable"` — offline-tested parity baseline для `query/stream/conversation`
- `feature_mode="hybrid"` — portable core + native built-ins/store seams
- `feature_mode="native_first"` — native built-ins и graph semantics как primary path
- Baseline extra `cognitia[deepagents]` покрывает runtime + Anthropic-ready provider path
- OpenAI и Google provider path требуют отдельных bridge packages
- Native metadata и resume surface отдаются приложению явно; native built-ins требуют явный `native_config["backend"]`

## Переключение runtime

Runtime выбирается через конфиг — бизнес-код не меняется:

```python
# Разработка: ThinRuntime (быстрый, без subprocess)
config = RuntimeConfig(runtime_name="thin")

# Продакшен: Claude SDK (полная интеграция)
config = RuntimeConfig(runtime_name="claude_sdk")

# Эксперименты: DeepAgents (LangGraph)
config = RuntimeConfig(runtime_name="deepagents")
```

## AgentRuntime Protocol

```python
class AgentRuntime(Protocol):
    def run(
        self,
        *,
        messages: list[Message],
        system_prompt: str,
        active_tools: list[ToolSpec],
        config: RuntimeConfig | None = None,
    ) -> AsyncIterator[RuntimeEvent]: ...

    async def cleanup(self) -> None: ...
```

Runtime **не хранит состояние** — получает messages каждый turn, возвращает new_messages в final event. SessionManager — source of truth.

## RuntimeEvent types

| Type | Данные | Когда |
|------|--------|-------|
| `assistant_delta` | `{"text": "..."}` | Streaming text |
| `status` | `{"text": "..."}` | Статус (thinking, tool call) |
| `tool_call_started` | `{"name": "...", "args": {...}}` | Начало tool call |
| `tool_call_finished` | `{"name": "...", "result_summary": "..."}` | Конец tool call |
| `final` | `{"text": "...", "new_messages": [...], "metrics": {...}}` | Завершение turn |
| `error` | `{"kind": "...", "message": "..."}` | Ошибка |
