# Status

## Текущий фокус

**Graph Agents + Knowledge Bank + Task Enhancements** — завершены 3 крупных блока работ:
1. Graph Agent Config (5 фаз): AgentExecutionContext, skills/MCP inheritance, dual-dispatch runner, builder API, governance (capabilities + limits)
2. Knowledge Bank (4 фазы): domain types, ISP protocols, multi-backend storage (FS/SQLite/Postgres), tools + consolidation
3. Task Progress + Workflow (4 фазы): TaskStatus.BLOCKED, progress auto-calc, extensible stages (WorkflowConfig), block/unblock в 3 backend'ах

3770 тестов pass, ruff clean. Pending: version bump 0.5.0 → 1.0.0, PyPI release.

## Версии

- cognitia: 0.5.0 → 1.0.0-core (все фичи реализованы, pending version bump)
- deepagents: 0.4.11 (0.5.0 ещё не на PyPI)

## Roadmap

**Завершено (v0.1.0 → v0.5.0)**:
1. ✅ Phase 0C: Shared ProviderResolver
2. ✅ Phase 0B: ThinRuntime multi-provider (3 адаптера + stream + caching)
3. ✅ Phase 1: Upstream params (memory/subagents/skills/middleware)
4. ✅ Phase 2: Compaction (noop native, token-aware portable, arg truncation)
5. ✅ Phase 0A: Portable memory + token-aware compaction
6. ✅ Phase 3: Cross-session memory + auto-backend
7. ✅ Phase 4: Capabilities (HITL native-only)
8. ⏸️ Phase 5: deepagents 0.5.0 (ожидаем PyPI release)

**Завершено (v0.5.0 → v1.0.0-core)** — Master Plan v3.2:

- ✅ Phase 6: DX Foundation (structured output, @tool, registry, cancel, context manager, typed events, protocols split)
- ✅ Phase 7: Production Safety (cost budget, guardrails, input filters, retry/fallback)
- ✅ Phase 8: Persistence & UI (session backends, event bus, tracing, UI projection, RAG)

*Enterprise extras:*
- ✅ Phase 9 MVP: Agent-as-tool + simple task queue + simple agent registry
- ✅ Graph Agents: AgentExecutionContext, governance, skills/MCP inheritance, dual-dispatch runner
- ✅ Knowledge Bank: 5 ISP protocols, multi-backend (FS/SQLite/Postgres), tools, consolidation
- ✅ Task Enhancements: BLOCKED status, progress auto-calc, extensible workflow stages
- ⬜ Phase 9 Full: Enterprise scheduler, advanced task policies

*Platform:*
- ✅ Phase 10A: CLI Agent Runtime (CliAgentRuntime, NdjsonParser, registry integration)
- ⬜ Phase 10 rest: MCP, credential proxy, OAuth, RTK, `cognitia init`, LiteLLM

*Ecosystem:*
- ⬜ Phase 11: OpenAI Agents SDK (4-й runtime + bridges, gated on SDK ≥ v1.0)

**Детали**: `plans/2026-03-18_masterplan_v3.md` (v3.2)

## Тесты

- 3770 passed, 5 deselected, 0 failed
- Source files: ~220 .py files
- Coverage: 89%+ overall
- Graph Agents (A1-A5): ~102 new tests
- Knowledge Bank (B1-B4): ~140 new tests
- Task Progress + BLOCKED + Stages: ~50 new tests
- Previous phases: ~480 tests (6-8, 9MVP, 10A)

## Verification Notes

- Full offline `pytest -q` green after OpenRouter live examples/runtime follow-up (`2524 passed, 11 skipped, 5 deselected`)
- Full offline `pytest -q` green after unified release-risk remediation + follow-up hardening (`2397 passed, 16 skipped, 5 deselected`)
- Representative targeted regressions green: Batch 1/2 (`205 passed`), merge-point portable/session pack (`110 passed`), orchestration/workflow/storage pack (`66 passed`)
- Full offline `pytest -q` green after full re-audit remediation (`2366 passed, 16 skipped, 5 deselected`)
- Targeted Wave 1 regression `pytest` green (`256 passed`)
- Targeted Wave 2 portable-helper regression `pytest` green (`76 passed, 1 skipped`)
- Targeted import-isolation/runtime-registry regressions green (`54 passed`, затем `32 passed` compatibility subset и `30 passed` memory/skills subset)
- Targeted `ruff check` on changed files green
- Targeted `mypy --follow-imports=silent` on changed source modules green
- Repo-wide `ruff check src/ tests/` green
- Repo-wide `mypy src/cognitia/` green
- Smoke verification green: `python examples/20_workflow_graph.py`, real `CliAgentRuntime` success path via temporary `claude` wrapper, and generic NDJSON fail-fast path (`bad_model_output`)

## Ключевые решения

- Portable path ОСТАЁТСЯ (fallback без backend, multi-provider)
- ThinRuntime → multi-provider (Anthropic + OpenAI-compat + Google)
- `cognitia[thin]` = canonical multi-provider install
- SqliteSessionBackend uses asyncio.to_thread() for non-blocking IO
- EventBus wired into ThinRuntime via llm_call wrapper + tool_call event forwarding
- TracingSubscriber uses correlation_id for concurrent tool call span tracking
- GuardrailContext gets session_id from config.extra
- LLM-facing instructions in English (structured output, prompts)
- ConsoleTracer lazy-imports structlog to keep Protocol layer dependency-free
- ThinRuntime buffers assistant text whenever guardrails, output validation, or retry can still reject/replace the response
