# Cognitia

**LLM-agnostic Python framework for building AI agents** with pluggable runtimes, persistent memory, tool management, and structured observability.

[![PyPI version](https://img.shields.io/pypi/v/cognitia.svg)](https://pypi.org/project/cognitia/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Why Cognitia?

Building production AI agents requires more than an LLM API call. You need memory, tool management, security policies, session handling, observability, and the ability to swap providers without rewriting your app.

**Cognitia solves this** by providing a modular, protocol-driven framework where every component is pluggable:

- **Switch LLM providers** (Anthropic, OpenAI, Google, DeepSeek) with one config change — no code modifications
- **Swap runtimes** — from a lightweight built-in loop to Claude Agent SDK to LangChain — same business code
- **Pick your storage** — InMemory for prototyping, SQLite for single-user, PostgreSQL for production
- **Compose capabilities** — sandbox, web search, todo lists, memory bank, planning — enable only what you need
- **Stay secure** — default-deny tool policy, sandboxed execution, input validation built-in

Unlike monolithic agent frameworks, cognitia follows **Clean Architecture**: your business logic depends on protocols (abstractions), not implementations. Swap any layer without touching the rest.

## Install

```bash
pip install cognitia                # core (protocols, types, in-memory providers)
pip install cognitia[thin]          # + lightweight built-in runtime (Anthropic API)
pip install cognitia[claude]        # + Claude Agent SDK runtime (subprocess + MCP)
pip install cognitia[deepagents]    # + LangChain Deep Agents runtime
```

## Quick Start

### One-shot query (3 lines)

```python
from cognitia import Agent, AgentConfig

agent = Agent(AgentConfig(system_prompt="You are a helpful assistant.", runtime="thin"))
result = await agent.query("What is the capital of France?")
print(result.text)  # "The capital of France is Paris."
```

### Streaming

```python
async for event in agent.stream("Explain quantum computing"):
    if event.type == "text_delta":
        print(event.text, end="", flush=True)
```

### Multi-turn conversation

```python
async with agent.conversation() as conv:
    r1 = await conv.say("My name is Alice")
    r2 = await conv.say("What's my name?")
    print(r2.text)  # "Your name is Alice."
```

### Custom tools

```python
from cognitia import AgentConfig, Agent, tool

@tool(name="calculate", description="Calculate a math expression")
async def calculate(expression: str) -> str:
    return str(eval(expression))  # simplified for demo

agent = Agent(AgentConfig(
    system_prompt="You are a calculator assistant.",
    runtime="thin",
    tools=(calculate,),
))
result = await agent.query("What is 15 * 23?")
print(result.text)  # "345"
```

### Structured output

```python
agent = Agent(AgentConfig(
    system_prompt="Extract user info.",
    runtime="thin",
    output_format={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name", "age"],
    },
))
result = await agent.query("John is 30 years old")
print(result.structured_output)  # {"name": "John", "age": 30}
```

### Middleware (cost tracking, security)

```python
from cognitia.agent import CostTracker, SecurityGuard

tracker = CostTracker(budget_usd=1.0)
guard = SecurityGuard(blocked_patterns=["password", "secret"])

agent = Agent(AgentConfig(
    system_prompt="You are a helpful assistant.",
    runtime="thin",
    middleware=(tracker, guard),
))
result = await agent.query("Hello")
print(tracker.total_cost_usd)  # 0.002
```

## Features

### Core

| Feature | Description |
|---------|-------------|
| **Agent Facade** | High-level API: `query()`, `stream()`, `conversation()` — build agents in 3-5 lines |
| **3 Pluggable Runtimes** | `thin` (built-in Anthropic loop), `claude_sdk` (Claude Agent SDK), `deepagents` (LangChain) |
| **@tool Decorator** | Define tools with auto-inferred JSON Schema from Python type hints |
| **Middleware Chain** | Pluggable request/response interceptors: `CostTracker`, `SecurityGuard`, custom |
| **14 ISP Protocols** | Every interface has ≤5 methods. Depend on abstractions, swap implementations freely |
| **Multi-provider Models** | Anthropic, OpenAI, Google, DeepSeek — alias resolution (`"sonnet"` → `claude-sonnet-4-20250514`) |

### Memory & Persistence

| Feature | Description |
|---------|-------------|
| **3 Memory Providers** | InMemory (dev), SQLite (single-user), PostgreSQL (production) — same 8 protocols |
| **8 Memory Protocols** | `MessageStore`, `FactStore`, `GoalStore`, `SummaryStore`, `UserStore`, `SessionStateStore`, `PhaseStore`, `ToolEventStore` |
| **Memory Bank** | Long-term file-based memory across sessions (filesystem or database backend) |
| **Auto-summarization** | Template-based or LLM-powered conversation summarization |

### Capabilities (toggle independently)

| Capability | What it does | Tools provided |
| ----------- | ------------- | ---------------- |
| **Sandbox** | Isolated file I/O and command execution | `bash`, `read`, `write`, `edit`, `glob`, `grep`, `ls` |
| **Web** | Internet access with pluggable providers | `web_fetch`, `web_search` |
| **Todo** | Structured task tracking | `todo_read`, `todo_write` |
| **Memory Bank** | Persistent knowledge across sessions | `memory_read`, `memory_write`, `memory_list`, `memory_delete` |
| **Planning** | Step-by-step task decomposition and execution | `plan_create`, `plan_status`, `plan_execute` |
| **Thinking** | Chain-of-thought reasoning | `thinking` |

### Advanced

| Feature | Description |
|---------|-------------|
| **Tool Policy** | Default-deny with allowlists per role/skill. `ALWAYS_DENIED` set for dangerous tools |
| **Tool Budget** | Priority-based tool selection when too many tools would confuse the model |
| **MCP Skills** | Declarative YAML skill definitions with automatic MCP server management |
| **Role Routing** | Keyword-based automatic role switching with per-role tool/skill mapping |
| **Context Builder** | Token-budget-aware system prompt assembly with priority-based overflow |
| **Hooks** | Lifecycle hooks: `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit` |
| **Observability** | Structured JSON logging via structlog |
| **Circuit Breaker** | Resilience pattern for external service calls |
| **Session Management** | Multi-session support with rehydration from persistent storage |
| **Orchestration** | Subagents, team mode (lead + workers), planning mode |
| **Commands** | Custom slash-command registry |

## Runtimes

Cognitia supports 3 interchangeable runtimes. Switch with a single config change — your business code stays the same:

```python
# Built-in lightweight loop (direct Anthropic API)
agent = Agent(AgentConfig(system_prompt="...", runtime="thin"))

# Claude Agent SDK (subprocess with full MCP support)
agent = Agent(AgentConfig(system_prompt="...", runtime="claude_sdk"))

# LangChain Deep Agents
agent = Agent(AgentConfig(system_prompt="...", runtime="deepagents"))
```

Or via environment variable:
```bash
export COGNITIA_RUNTIME=thin
```

| Runtime | Best For | LLM Support | MCP | Install |
| ------- | -------- | ----------- | --- | ------- |
| `thin` | Fast prototyping, direct API, alternative LLMs | Any (via `base_url`) | Built-in client | `cognitia[thin]` |
| `claude_sdk` | Full Claude ecosystem, native MCP, subagents | Claude only | Native | `cognitia[claude]` |
| `deepagents` | LangChain ecosystem, LangGraph workflows | Any (LangChain) | Via LangChain | `cognitia[deepagents]` |

### Capability negotiation

Each runtime declares its capabilities. Use `CapabilityRequirements` to ensure your chosen runtime supports what you need:

```python
from cognitia.runtime.capabilities import CapabilityRequirements

agent = Agent(AgentConfig(
    system_prompt="...",
    runtime="claude_sdk",
    require_capabilities=CapabilityRequirements(
        tier="full",
        flags=("mcp", "resume"),
    ),
))
# Fails fast if the runtime doesn't support required features
```

## Architecture

```
Your Application
       │
       │ depends on protocols (DIP)
       ▼
╔══════════════════════════════════════════════════════════╗
║                      Cognitia                            ║
║                                                          ║
║  ┌─────────────────────────────────────────────────────┐ ║
║  │  Agent Facade                                       │ ║
║  │  Agent · AgentConfig · @tool · Middleware · Result   │ ║
║  └─────────────────┬───────────────────────────────────┘ ║
║                    │                                     ║
║  ┌─────────────────▼───────────────────────────────────┐ ║
║  │  14 Protocols (ISP: ≤5 methods each)                │ ║
║  │  MessageStore · FactStore · GoalStore · SummaryStore │ ║
║  │  UserStore · SessionStateStore · PhaseStore          │ ║
║  │  ToolEventStore · RoleRouter · ToolIdCodec          │ ║
║  │  ModelSelector · ContextBuilder · RuntimePort       │ ║
║  │  AgentRuntime                                       │ ║
║  └─────────────────┬───────────────────────────────────┘ ║
║                    │                                     ║
║  ┌─────────────────▼───────────────────────────────────┐ ║
║  │  Implementations                                    │ ║
║  │  memory/      InMemory │ PostgreSQL │ SQLite        │ ║
║  │  runtime/     thin │ claude_sdk │ deepagents        │ ║
║  │  context/     DefaultContextBuilder (token budget)  │ ║
║  │  policy/      DefaultToolPolicy (default-deny)      │ ║
║  │  routing/     KeywordRoleRouter                     │ ║
║  │  skills/      YamlSkillLoader + SkillRegistry       │ ║
║  │  hooks/       HookRegistry + SDK bridge             │ ║
║  │  tools/       Sandbox · Web · Todo · MemoryBank     │ ║
║  │  orchestration/  Planning · Subagents · Team        │ ║
║  │  observability/  AgentLogger (structlog)            │ ║
║  └─────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════╝
```

**Key principles:**

- **Domain-agnostic** — no business domain logic in the library
- **Protocol-first** — depend on abstractions, not implementations
- **Pluggable** — swap any component with a single line change
- **Clean Architecture** — dependencies point inward only (Infrastructure → Application → Domain)
- **ISP** — Interface Segregation: each protocol has ≤5 focused methods
- **Immutable types** — all domain objects are frozen dataclasses

## Memory Providers

Three interchangeable providers, all implementing the same 8 protocols:

```python
# Development — no database needed
from cognitia.memory import InMemoryMemoryProvider
memory = InMemoryMemoryProvider()

# Lightweight persistence — SQLite
from cognitia.memory import SQLiteMemoryProvider
memory = SQLiteMemoryProvider(db_path="./agent.db")

# Production — PostgreSQL
from cognitia.memory import PostgresMemoryProvider
memory = PostgresMemoryProvider(session_factory)
```

## Capabilities

Enable only what you need — each capability is an independent toggle:

```python
from cognitia.bootstrap import CognitiaStack
from cognitia.runtime.types import RuntimeConfig
from cognitia.tools.sandbox_local import LocalSandboxProvider
from cognitia.tools.web_httpx import HttpxWebProvider
from cognitia.todo.inmemory_provider import InMemoryTodoProvider

stack = CognitiaStack.create(
    prompts_dir="./prompts",
    skills_dir="./skills",
    project_root=".",
    runtime_config=RuntimeConfig(runtime_name="thin"),
    # Toggle capabilities independently:
    sandbox_provider=LocalSandboxProvider(sandbox_config),  # file I/O, bash
    web_provider=HttpxWebProvider(),                        # web search/fetch
    todo_provider=InMemoryTodoProvider(user_id="u1", topic_id="t1"),
    thinking_enabled=True,                                  # chain-of-thought
)
```

## Web Search Providers

Pluggable web search with 4 providers and 3 fetch backends:

```python
# Search providers (pick one)
from cognitia.tools.web_providers.duckduckgo import DuckDuckGoSearchProvider  # no API key
from cognitia.tools.web_providers.brave import BraveSearchProvider            # BRAVE_API_KEY
from cognitia.tools.web_providers.tavily import TavilySearchProvider          # TAVILY_API_KEY
from cognitia.tools.web_providers.searxng import SearXNGSearchProvider        # self-hosted

# Fetch providers (pick one)
from cognitia.tools.web_httpx import HttpxWebProvider           # default (httpx)
from cognitia.tools.web_providers.jina import JinaReaderFetchProvider    # JINA_API_KEY
from cognitia.tools.web_providers.crawl4ai import Crawl4AIFetchProvider  # Playwright
```

## Model Registry

Multi-provider model resolution with human-friendly aliases:

```python
from cognitia.runtime.types import resolve_model_name

resolve_model_name("sonnet")   # "claude-sonnet-4-20250514"
resolve_model_name("opus")     # "claude-opus-4-20250514"
resolve_model_name("gpt-4o")   # "gpt-4o"
resolve_model_name("gemini")   # "gemini-2.5-pro"
resolve_model_name("r1")       # "deepseek-reasoner"
```

Supported providers: **Anthropic** (Claude), **OpenAI** (GPT-4o, o3), **Google** (Gemini), **DeepSeek** (R1).

## Optional Dependencies

| Extra | Packages | Purpose |
|-------|----------|---------|
| `thin` | anthropic, httpx | Built-in lightweight runtime |
| `claude` | claude-agent-sdk | Claude Agent SDK runtime |
| `deepagents` | langchain-core, langchain-anthropic | LangChain runtime |
| `postgres` | asyncpg, sqlalchemy | PostgreSQL memory provider |
| `sqlite` | aiosqlite, sqlalchemy | SQLite memory provider |
| `web` | httpx | Web fetch (base) |
| `web-duckduckgo` | ddgs | DuckDuckGo search (no API key) |
| `web-tavily` | tavily-python | Tavily AI search |
| `web-jina` | httpx | Jina Reader (URL → markdown) |
| `web-crawl4ai` | crawl4ai | Crawl4AI (Playwright-based) |
| `e2b` | e2b | E2B cloud sandbox |
| `docker` | docker | Docker sandbox |
| `all` | All of the above | Development convenience |

## Documentation

- [Why Cognitia?](docs/why-cognitia.md) — value proposition, design philosophy
- [Getting Started](docs/getting-started.md) — installation, first agent, step-by-step
- [Agent Facade API](docs/agent-facade.md) — Agent, AgentConfig, @tool, Result, Conversation, Middleware
- [Runtimes](docs/runtimes.md) — Claude SDK vs ThinRuntime vs DeepAgents
- [Memory](docs/memory.md) — InMemory, PostgreSQL, SQLite providers
- [Tools & Skills](docs/tools-and-skills.md) — @tool decorator, MCP skills, tool policy
- [Capabilities](docs/capabilities.md) — sandbox, web, todo, memory bank, planning, thinking
- [Web Tools](docs/web-tools.md) — search and fetch providers
- [Configuration](docs/configuration.md) — CognitiaStack, RuntimeConfig, environment variables
- [Orchestration](docs/orchestration.md) — planning, subagents, team mode
- [Architecture](docs/architecture.md) — layers, protocols, packages
- [API Reference](docs/api-reference.md) — comprehensive API documentation
- [Advanced](docs/advanced.md) — hooks, observability, circuit breaker, context builder
- [Examples](docs/examples.md) — integration examples for different domains
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

## License

[MIT](LICENSE)
