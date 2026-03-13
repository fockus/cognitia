# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0b1] - 2026-03-13

### Added
- **Agent Facade API** (`cognitia.agent`) — high-level 3-line API for AI agents
  - `Agent` class with `query()`, `stream()`, `conversation()` methods
  - `@tool` decorator for defining tools with auto-inferred JSON Schema
  - `Middleware` protocol with built-in `CostTracker` and `SecurityGuard`
  - `Conversation` for explicit multi-turn dialog management
- **Import isolation** — `import cognitia` works without any optional dependencies
- **Test markers** — `requires_claude_sdk`, `requires_anthropic`, `requires_langchain`, `live`
- LICENSE (MIT), CHANGELOG, CONTRIBUTING, comprehensive documentation

### Fixed
- `@tool` handler contract mismatch with Claude Agent SDK MCP format
- `hooks/__init__.py` crash when `claude_agent_sdk` not installed
- Optional dependency boundaries fully verified with smoke tests

## [0.2.0] - 2026-02-11

### Added
- **Multi-runtime support** — 3 pluggable runtimes:
  - `claude_sdk` — Claude Agent SDK (subprocess, built-in MCP)
  - `thin` — lightweight built-in loop (react/planner/conversational modes)
  - `deepagents` — LangChain Deep Agents integration
- **RuntimeFactory** — create runtime by config/env/override
- **Runtime Ports** — `BaseRuntimePort`, `ThinRuntimePort`, `DeepAgentsRuntimePort`
- **Model Registry** — multi-provider (Anthropic, OpenAI, Google, DeepSeek) with aliases
- **CognitiaStack** — bootstrap facade factory for quick setup
- **Memory providers** — InMemory, PostgreSQL, SQLite
- **Web tools** — pluggable search (DuckDuckGo, Tavily, SearXNG, Brave) and fetch providers
- **Orchestration** — plan manager, subagent spawning, team coordination
- **SDK 0.1.48 integration** — `one_shot_query`, `sdk_tools`, hooks bridge
- **LLM Summarizer** — automatic conversation summarization with history cap
- **Circuit Breaker** — resilience pattern for external calls
- 14 ISP-compliant protocols (each <=5 methods)

### Changed
- Domain-agnostic: removed all finance-specific defaults from library code
- `RoleSkillsLoader` moved to `cognitia.config.role_skills`
- `RoleRouterConfig` is now a typed dataclass (was dict)

## [0.1.0] - 2026-02-10

### Added
- **Core protocols** — `FactStore`, `GoalStore`, `MessageStore`, `SummaryStore`, `UserStore`, `SessionStateStore`, `PhaseStore`, `ToolEventStore`
- **Behavior protocols** — `RoleRouter`, `ModelSelector`, `ToolIdCodec`, `ContextBuilder`, `SessionRehydrator`, `RuntimePort`
- **Session management** — `InMemorySessionManager`, `DefaultSessionRehydrator`
- **Context builder** — `DefaultContextBuilder` with token budget and priority-based overflow
- **Tool policy** — `DefaultToolPolicy` with default-deny and always-denied tools list
- **Skills** — `YamlSkillLoader`, `SkillRegistry` for declarative MCP skill management
- **Routing** — `KeywordRoleRouter` for keyword-based role resolution
- **Observability** — `AgentLogger` with structured JSON logging
- **Memory** — `InMemoryMemoryProvider`, `PostgresMemoryProvider`
- **Commands** — `CommandRegistry` with aliases

[0.3.0b1]: https://github.com/fockus/cognitia/compare/v0.2.0...v0.3.0b1
[0.2.0]: https://github.com/fockus/cognitia/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fockus/cognitia/releases/tag/v0.1.0
