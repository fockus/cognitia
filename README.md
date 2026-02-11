# Cognitia

LLM-агностичная библиотека для построения AI-агентов. Предоставляет инфраструктуру: сессии, память, политики инструментов, контекст-инжиниринг, skills/MCP, observability.

**Cognitia ничего не знает о предметной области.** Финансы, медицина, образование — любой домен подключается через приложение.

```
pip install -e packages/cognitia
```

## Quickstart (Bootstrap API)

```python
from pathlib import Path

from cognitia.bootstrap import CognitiaStack
from cognitia.runtime.types import RuntimeConfig

root = Path(".").resolve()
stack = CognitiaStack.create(
    prompts_dir=root / "prompts",
    skills_dir=root / "skills",
    project_root=root,
    runtime_config=RuntimeConfig(runtime_name="claude_sdk"),
)
```

Дальше приложение использует `stack.skill_registry`, `stack.context_builder`,
`stack.role_skills_loader`, `stack.role_router`, `stack.tool_policy`, `stack.runtime_factory`.

Полный пример wiring: `docs/integration-guide.md`.

## Пример: один turn через CognitiaStack

```python
from __future__ import annotations

import asyncio
from pathlib import Path

from cognitia.bootstrap import CognitiaStack
from cognitia.context.builder import ContextInput
from cognitia.runtime.types import Message, RuntimeConfig, ToolSpec


async def main() -> None:
    root = Path(".").resolve()
    runtime_config = RuntimeConfig(
        runtime_name="thin",
        model="claude-sonnet-4-20250514",
    )

    stack = CognitiaStack.create(
        prompts_dir=root / "prompts",
        skills_dir=root / "skills",
        project_root=root,
        runtime_config=runtime_config,
    )

    user_id = "demo_user"
    topic_id = "default"
    role_id = "coach"
    user_text = "Помоги составить план накопления на 1 000 000 за 12 месяцев."

    active_skill_ids = stack.role_skills_loader.get_skills(role_id)
    skills = [
        skill
        for skill in stack.skill_registry.list_all()
        if skill.spec.skill_id in active_skill_ids
    ]

    context_input = ContextInput(
        user_id=user_id,
        topic_id=topic_id,
        role_id=role_id,
        user_text=user_text,
        active_skill_ids=active_skill_ids,
    )
    built = await stack.context_builder.build(context_input, skills=skills)

    tool_allowlist = stack.skill_registry.get_tool_allowlist(active_skill_ids)
    active_tools: list[ToolSpec] = [
        ToolSpec(
            name=tool_name,
            description=f"MCP tool: {tool_name}",
            parameters={"type": "object"},
            is_local=False,
        )
        for tool_name in sorted(tool_allowlist)
        if tool_name.startswith("mcp__")
    ]

    runtime = stack.runtime_factory.create(
        config=runtime_config,
        local_tools={},
        mcp_servers={},
    )

    try:
        messages = [Message(role="user", content=user_text)]
        async for event in runtime.run(
            messages=messages,
            system_prompt=built.system_prompt,
            active_tools=active_tools,
            config=runtime_config,
        ):
            if event.type == "assistant_delta":
                print(event.data.get("text", ""), end="", flush=True)
            elif event.type == "final":
                print("\n\n[FINAL]")
                print(event.data.get("text", ""))
            elif event.type == "error":
                print("\n[ERROR]", event.data.get("message", "unknown"))
    finally:
        await runtime.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
```

## Архитектура

```
Приложение (Freedom Agent, ваш бот, ...)
       │
       │ использует протоколы
       ▼
┌─── Cognitia ──────────────────────────────┐
│                                           │
│  Protocols (14 портов, ISP ≤5 методов)    │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │FactStore │ │GoalStore │ │MessageStore│ │
│  └──────────┘ └──────────┘ └───────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │UserStore │ │PhaseStore│ │SummaryStore│ │
│  └──────────┘ └──────────┘ └───────────┘ │
│  ┌──────────────┐ ┌─────────────────────┐ │
│  │SessionState  │ │ToolEventStore       │ │
│  │Store         │ │                     │ │
│  └──────────────┘ └─────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │ToolPolicy│ │RoleRouter│ │ModelSelect │ │
│  └──────────┘ └──────────┘ └───────────┘ │
│  ┌─────────────┐ ┌────────────────────┐  │
│  │ContextBuild │ │SessionRehydrator   │  │
│  └─────────────┘ └────────────────────┘  │
│                                           │
│  Implementations                          │
│  ├── memory/     InMemory + Postgres      │
│  ├── context/    DefaultContextBuilder    │
│  ├── policy/     DefaultToolPolicy        │
│  ├── routing/    KeywordRoleRouter        │
│  ├── session/    InMemorySessionManager   │
│  ├── skills/     YamlSkillLoader          │
│  ├── runtime/    Claude SDK adapter       │
│  ├── resilience/ CircuitBreaker           │
│  └── observability/ AgentLogger           │
│                                           │
└───────────────────────────────────────────┘
```

## Ключевые принципы

- **ISP** — каждый протокол ≤5 методов. `FactStore` не знает о `GoalStore`.
- **DIP** — приложение зависит от протоколов, не от реализаций.
- **Pluggable** — поменяй `PostgresMemoryProvider` на `InMemoryMemoryProvider` одной строкой.
- **Domain-agnostic** — в коде cognitia нет слов "финансы", "вклад", "кредит".

## Протоколы (порты)

### Память (8 протоколов)

```python
class FactStore(Protocol):
    async def upsert_fact(self, user_id: str, key: str, value: Any,
                          topic_id: str | None = None, source: str = "user") -> None: ...
    async def get_facts(self, user_id: str, topic_id: str | None = None) -> dict[str, Any]: ...

class GoalStore(Protocol):
    async def save_goal(self, user_id: str, goal: GoalState) -> None: ...
    async def get_active_goal(self, user_id: str, topic_id: str) -> GoalState | None: ...

class MessageStore(Protocol):
    async def save_message(self, user_id: str, topic_id: str, role: str, content: str, ...) -> None: ...
    async def get_messages(self, user_id: str, topic_id: str, limit: int = 10) -> list[MemoryMessage]: ...
    async def count_messages(self, user_id: str, topic_id: str) -> int: ...
    async def delete_messages_before(self, user_id: str, topic_id: str, keep_last: int = 10) -> int: ...

class SummaryStore(Protocol):
    async def save_summary(self, user_id: str, topic_id: str, summary: str, messages_covered: int) -> None: ...
    async def get_summary(self, user_id: str, topic_id: str) -> str | None: ...

class UserStore(Protocol):
    async def ensure_user(self, external_id: str) -> str: ...
    async def get_user_profile(self, user_id: str) -> UserProfile: ...

class SessionStateStore(Protocol):
    async def save_session_state(self, user_id: str, topic_id: str, role_id: str,
                                  active_skill_ids: list[str], prompt_hash: str = "") -> None: ...
    async def get_session_state(self, user_id: str, topic_id: str) -> dict[str, Any] | None: ...

class PhaseStore(Protocol):
    async def save_phase_state(self, user_id: str, phase: str, notes: str = "") -> None: ...
    async def get_phase_state(self, user_id: str) -> PhaseState | None: ...

class ToolEventStore(Protocol):
    async def save_tool_event(self, user_id: str, event: ToolEvent) -> None: ...
```

### Поведение (6 протоколов)

```python
class RoleRouter(Protocol):
    def resolve(self, user_text: str, explicit_role: str | None = None) -> str: ...

class ModelSelector(Protocol):
    def select(self, role_id: str, tool_failure_count: int = 0) -> str: ...
    def select_for_turn(self, role_id: str, user_text: str, ...) -> str: ...

class ToolIdCodec(Protocol):
    def matches(self, tool_name: str, server_id: str) -> bool: ...
    def encode(self, server_id: str, tool_name: str) -> str: ...
    def extract_server(self, tool_name: str) -> str | None: ...

class ContextBuilder(Protocol):
    async def build(self, inp: Any, **kwargs: Any) -> Any: ...

class SessionRehydrator(Protocol):
    async def build_rehydration_payload(self, ctx: TurnContext) -> Mapping[str, Any]: ...

class RuntimePort(Protocol):
    @property
    def is_connected(self) -> bool: ...
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def stream_reply(self, user_text: str) -> AsyncIterator[Any]: ...
```

## Типы

```python
@dataclass(frozen=True)
class TurnContext:
    """Контекст одного turn'а — единица обработки."""
    user_id: str
    topic_id: str
    role_id: str
    model: str
    active_skill_ids: tuple[str, ...]

@dataclass(frozen=True)
class ContextPack:
    """Блок контекста для system prompt."""
    pack_id: str            # "guardrails", "active_goals", "user_profile"
    priority: int           # 0 = highest (guardrails), 6 = lowest (profile)
    content: str            # Текст для вставки в prompt
    tokens_estimate: int    # Оценка размера в токенах

@dataclass(frozen=True)
class SkillSet:
    """Набор skills для роли."""
    set_id: str
    skill_ids: tuple[str, ...] = ()
    local_tool_ids: tuple[str, ...] = ()
```

## Модули

### memory/ — персистентность

Две реализации одних протоколов:

```python
from cognitia.memory import InMemoryMemoryProvider, PostgresMemoryProvider

# Dev/тесты — без БД
memory = InMemoryMemoryProvider()

# Production — Postgres
from sqlalchemy.ext.asyncio import async_sessionmaker
memory = PostgresMemoryProvider(session_factory)

# Оба реализуют: FactStore, GoalStore, MessageStore, SummaryStore,
# UserStore, SessionStateStore, PhaseStore, ToolEventStore
```

### context/ — сборка system prompt

```python
from cognitia.context import DefaultContextBuilder, ContextInput, ContextBudget

builder = DefaultContextBuilder(prompts_dir="./prompts")

inp = ContextInput(
    user_id="u1", topic_id="t1", role_id="coach",
    user_text="Как накопить на отпуск?",
    active_skill_ids=["finuslugi"],
    budget=ContextBudget(total_tokens=8000),
)

built = await builder.build(
    inp,
    user_profile=profile,     # ContextPack priority=6
    active_goal=goal,          # ContextPack priority=2
    phase_state=phase,         # ContextPack priority=3
    summary="...",             # ContextPack priority=5
)

print(built.system_prompt)     # Собранный prompt из слоёв
print(built.prompt_hash)       # SHA256 hash (первые 16 символов)
print(built.truncated_packs)   # Какие пакеты обрезаны по бюджету
```

Приоритеты при бюджетном overflow (от высшего):
0. Guardrails
1. Role instruction
2. Active goals
3. Phase
4. Tool hints
5. Memory recall
6. User profile

### policy/ — безопасность инструментов

```python
from cognitia.policy import DefaultToolPolicy, ToolPolicyInput

policy = DefaultToolPolicy()

state = ToolPolicyInput(
    tool_name="mcp__finuslugi__get_deposits",
    input_data={"amount": 500000},
    active_skill_ids=["finuslugi"],
    allowed_local_tools={"mcp__freedom_tools__calculate_goal_plan"},
)

result = policy.can_use_tool("mcp__finuslugi__get_deposits", {}, state)
# → PermissionAllow (finuslugi в active skills)

result = policy.can_use_tool("Bash", {}, state)
# → PermissionDeny (ALWAYS_DENIED_TOOLS)
```

**Всегда запрещены:** Bash, Read, Write, Edit, MultiEdit, Glob, Grep, LS, TodoRead, TodoWrite, WebFetch, WebSearch.

### skills/ — декларативные MCP skills

```yaml
# skills/finuslugi/skill.yaml
skill_id: finuslugi
title: "ФинУслуги — банковские продукты"
mcp_servers:
  - name: user-finuslugi
    transport: url
    url: "https://..."
tool_include:
  - get_bank_deposits
  - get_bank_credits
intents: [deposits, credits, insurance]
```

```python
from cognitia.skills import YamlSkillLoader, SkillRegistry

loader = YamlSkillLoader("./skills")
skills = loader.load_all()
registry = SkillRegistry(skills)

# Получить MCP серверы для роли
servers = registry.get_mcp_servers_for_skills(["finuslugi", "iss"])

# Получить allowlist инструментов
tools = registry.get_tool_allowlist(["finuslugi"])
# → {"mcp__finuslugi__get_bank_deposits", "mcp__finuslugi__get_bank_credits"}
```

### session/ — управление сессиями

```python
from cognitia.session import InMemorySessionManager, SessionKey

manager = InMemorySessionManager()

# Регистрация сессии
manager.register(session_state)

# Получение по ключу (user_id + topic_id)
state = manager.get(SessionKey("user_1", "topic_deposits"))

# Streaming ответа
async for event in manager.stream_reply(key, "Хочу вклад"):
    if event.type == "text_delta":
        print(event.text, end="")
    elif event.type == "tool_use_start":
        print(f"[tool: {event.tool_name}]")
```

**Rehydration** — восстановление после рестарта:

```python
from cognitia.session import DefaultSessionRehydrator

rehydrator = DefaultSessionRehydrator(
    messages=memory, summaries=memory,
    goals=memory, sessions=memory, phases=memory,
)

payload = await rehydrator.build_rehydration_payload(turn_context)
# → {role_id, active_skill_ids, prompt_hash, summary, last_messages, goal, phase_state}
```

### routing/ — маршрутизация ролей

```python
from cognitia.routing import KeywordRoleRouter

router = KeywordRoleRouter(
    default_role="coach",
    keyword_map={
        "deposit_advisor": ["вклад", "депозит"],
        "credit_advisor": ["кредит", "ипотека"],
    },
)

role = router.resolve("Хочу открыть вклад")     # → "deposit_advisor"
role = router.resolve("Привет")                   # → "coach"
role = router.resolve("...", explicit_role="coach") # → "coach" (explicit wins)
```

### runtime/ — Claude Agent SDK

```python
from cognitia.runtime import RuntimeAdapter, ClaudeOptionsBuilder, ModelPolicy

options = ClaudeOptionsBuilder(model_policy=ModelPolicy()).build(
    role_id="coach",
    system_prompt="...",
    mcp_servers=servers,
)

adapter = RuntimeAdapter(options)
await adapter.connect()

async for event in adapter.stream_reply("Как накопить?"):
    # StreamEvent: text_delta | tool_use_start | tool_use_result | done | error
    ...
```

### resilience/ — устойчивость

```python
from cognitia.resilience import CircuitBreaker

cb = CircuitBreaker(failure_threshold=3, recovery_timeout_s=60)

if cb.can_execute():
    try:
        result = await call_mcp()
        cb.record_success()
    except Exception:
        cb.record_failure()
```

### observability/ — structured logging

```python
from cognitia.observability import AgentLogger, configure_logging

configure_logging(level="info", fmt="json")
logger = AgentLogger(component="my_app")

logger.session_created(user_id="u1", topic_id="t1", role_id="coach")
logger.turn_start(user_id="u1", topic_id="t1")
logger.tool_call(tool_name="finuslugi__get_deposits", latency_ms=450)
logger.tool_policy_event(tool_name="Bash", allowed=False, reason="ALWAYS_DENIED")
logger.turn_complete(user_id="u1", topic_id="t1", role_id="coach", prompt_hash="abc123")
```

JSON в stdout: `ts`, `level`, `event_type`, `user_id`, `topic_id`, `role_id`, `tool_name`, `latency_ms`.

## Тесты

```bash
pytest packages/cognitia/tests/ -v
# 334+ тестов, 96% coverage
```

## Зависимости

- `structlog` — structured logging
- `pyyaml` — загрузка skill.yaml
- `sqlalchemy[asyncio]` + `asyncpg` — Postgres (опционально)
- `claude-agent-sdk` — runtime (опционально, только adapter)
