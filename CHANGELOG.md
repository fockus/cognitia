# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-03-15

### Added
- **Code Verification Pipeline** (`cognitia.orchestration`)
  - `CodeVerifier` Protocol — ISP-compliant (5 methods: verify_contracts, verify_tests_substantive, verify_tests_before_code, verify_linters, verify_coverage)
  - `TddCodeVerifier` — implementation respecting `CodingStandardsConfig` (disabled checks auto-SKIP)
  - `CommandRunner` Protocol + `CommandResult` — sandbox-agnostic command execution
  - `DoDStateMachine` — criteria-driven verification state machine (PENDING → VERIFYING → PASSED/FAILED) with max loop counter
  - `CodeWorkflowEngine` — structured code pipeline: plan → execute → verify_dod → loop
  - `WorkflowPipeline` Protocol — generic research → plan → execute → review → verify
  - `WorkflowResult` — structured pipeline result
- **Verification Types** (`cognitia.orchestration.verification_types`)
  - `VerificationStatus` (PASS/FAIL/SKIP), `CheckDetail`, `VerificationResult` with `.passed` property
- **Coding Standards Configs** (`cognitia.orchestration.coding_standards`)
  - `CodingStandardsConfig` — TDD, SOLID, DRY, KISS, Clean Arch flags with factory methods: `strict()`, `minimal()`, `off()`
  - `WorkflowAutomationConfig` — `full()`, `light()`, `off()` factories
  - `AutonomousLoopConfig` — `strict()`, `light()` factories
  - `CodePipelineConfig` — aggregate with `production()`, `development()` presets
  - `TeamAgentsConfig` — team role configuration
- **ToolOutputCompressor Middleware** (`cognitia.agent.middleware`)
  - Content-type aware compression: JSON (truncate arrays), HTML (strip tags), Text (head+tail)
  - Integrates with `HookRegistry` via `on_post_tool_use` callback
  - Configurable `max_result_chars` (default 10000)
- **Middleware helpers**
  - `build_middleware_stack()` — factory for common middleware combinations (cost_tracker, tool_compressor, security_guard)
- **HookRegistry.merge()** — public API to combine hook registries from multiple middlewares
- **PlanStep DoD fields** — `dod_criteria`, `dod_verified`, `verification_log` for plan verification tracking

### Changed
- `PlanStep` transition methods use `dataclasses.replace()` (new DoD fields auto-propagate)

### Tests
- 51 new unit tests: tool_output_compressor (12), verification_types (9), coding_standards (12), code_verifier (10), dod_state_machine (8)

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

[0.4.0]: https://github.com/fockus/cognitia/compare/v0.3.0b1...v0.4.0
[0.3.0b1]: https://github.com/fockus/cognitia/compare/v0.2.0...v0.3.0b1
[0.2.0]: https://github.com/fockus/cognitia/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fockus/cognitia/releases/tag/v0.1.0
