# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-16

### Added
- **ThinRuntime Built-in Tools** (`cognitia.runtime.thin.builtin_tools`)
  - 9 tools: `read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`, `execute`, `write_todos`, `task`
  - `feature_mode` filtering (portable/hybrid/native_first)
  - DeepAgents-compatible aliases (Read→read_file, Bash→execute, etc.)
  - `merge_tools_with_builtins()` — user tools override built-ins by name
- **Token-Level Streaming** (`cognitia.runtime.thin.stream_parser`)
  - `IncrementalEnvelopeParser` — stateful incremental JSON brace-tracking parser
  - `StreamParser` — high-level streaming parser with ActionEnvelope extraction
  - React + Conversational + Planner modes all stream per-token via `_try_stream_llm_call()`
  - Fallback to non-streaming on parse error
- **ThinTeamOrchestrator** (`cognitia.orchestration.thin_team`)
  - Full `TeamOrchestrator` + `ResumableTeamOrchestrator` protocol implementation
  - Lead delegation: `_compose_worker_task()` personalizes task per worker
  - MessageBus per-team with auto-registered `send_message` tool
  - pause/resume via cancel + re-spawn
- **ThinSubagent Full Implementation** (`cognitia.orchestration.thin_subagent`)
  - `_create_runtime()` creates per-worker `_ThinWorkerRuntime` with ThinRuntime
  - `register_tool()` public method for tool injection (replaces private access)
  - Supports `llm_call`, `local_tools`, `mcp_servers`, `runtime_config` via constructor
- **MessageBus Tools** (`cognitia.orchestration.message_tools`)
  - `SEND_MESSAGE_TOOL_SPEC` — ToolSpec with JSON Schema (to_agent, content)
  - `create_send_message_tool()` — factory for send/broadcast executor
  - `send_message_tool_spec()` — accessor function
- **McpBridge** (`cognitia.runtime.mcp_bridge`)
  - Library-level MCP facade (runtime-agnostic, works with thin + deepagents)
  - `discover_tools()` / `discover_all_tools()` — tool names prefixed as `mcp__{server}__{tool}`
  - `create_tool_executor()` — async callable factory for LangChain integration
  - Caching delegated to McpClient TTL (300s)
- **DeepAgents MCP Integration** (`cognitia.runtime.deepagents`)
  - `mcp_servers` parameter in `__init__()` — creates `McpBridge` automatically
  - MCP tools injected into `selected_tools` with executor wiring
  - Graceful degradation with `logging.warning` on discovery failure
- **WorkflowGraph** (`cognitia.orchestration.workflow_graph`)
  - Declarative graph execution: linear, conditional branching, loop with max, parallel, subgraph, interrupt/resume
  - `InMemoryCheckpoint` for state persistence
  - `to_mermaid()` — graph visualization export
- **Workflow Executors** (`cognitia.orchestration.workflow_executor`)
  - `ThinWorkflowExecutor` — LLM per-node via ThinRuntime
  - `MixedRuntimeExecutor` — route nodes to different runtimes via `node_interceptor`
  - `compile_to_langgraph()` — LangGraph StateGraph compiler for deepagents
- **GenericWorkflowEngine** (`cognitia.orchestration.generic_workflow_engine`)
  - Pluggable `ExecutorPort` + `VerifierPort` protocols
  - Retry/verify loop with configurable `max_retries`
- **CommandRegistry v2** (`cognitia.commands`)
  - `CommandDef` with typed `parameters` (JSON Schema), `description`, `category`
  - `to_tool_definitions()` — commands available as LLM tools
  - `execute_validated()` — JSON Schema parameter validation before execute
  - YAML auto-discovery via `loader.py` (`load_commands_from_yaml`, `auto_discover_commands`)
  - Backward compatible with string-based API
- **JSON Utilities** (`cognitia.runtime.thin.json_utils`)
  - `find_json_object_boundaries()` — shared brace-tracking parser (DRY extraction)

### Changed
- `CodeWorkflowEngine` now delegates to `GenericWorkflowEngine` (thin wrapper with `_PlannerExecutor` + `_DoDVerifierAdapter`)
- `MixedRuntimeExecutor` uses `node_interceptor` parameter instead of monkey-patching `_execute_node`
- Runtime Feature Matrix added to README.md

### Tests
- 298 new tests (1085 → 1383 passed): builtin_tools (20), streaming (20), thin_subagent (9), thin_team (12), message_tools (7), mcp_bridge (4), deepagents_mcp (5), workflow_graph (8), workflow_executor (10), generic_workflow (6), commands_v2 (12), json_utils (18), code_workflow_delegation (3), and more

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

[0.5.0]: https://github.com/fockus/cognitia/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/fockus/cognitia/compare/v0.3.0b1...v0.4.0
[0.3.0b1]: https://github.com/fockus/cognitia/compare/v0.2.0...v0.3.0b1
[0.2.0]: https://github.com/fockus/cognitia/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fockus/cognitia/releases/tag/v0.1.0
