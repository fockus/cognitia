# Plan

## Текущий приоритет
**Phase 9 MVP + Phase 10A — ЗАВЕРШЕНЫ** (все 22 этапа + 2 раунда code review).
Master Plan v3.2 → `plans/2026-03-18_masterplan_v3.md`

## Активный план

**v1.0.0-core Release Pipeline** → `plans/2026-03-18_feature_v1-release-pipeline.md`
10 этапов: ruff/mypy cleanup → Wave 2/3 remediation → docs → PyPI release

## Следующий шаг (после v1.0.0 release)

1. **Phase 9 Full** — Enterprise tasks (priority/deadline scheduling, hierarchy, delegation, distributed scheduler)
2. **Phase 10 rest** — MCP server, credential proxy, OAuth, RTK integration, `cognitia init` CLI, LiteLLM adapter

## Направление
cognitia = **простая библиотека** (не фреймворк) для AI агентов.
- Core (Phases 6-8): ✅ DONE → v1.0.0-core
- Enterprise extras (Phase 9): tasks, hierarchy, delegation, scheduler
- Platform (Phase 10): CLI, MCP, plugins
- Ecosystem (Phase 11): OpenAI Agents SDK

## Ключевые изменения v3 vs v2
- Core/Enterprise разделение (optional extras)
- 9B/9C/9E: MVP + Full уровни
- Ложные зависимости убраны (9E⊬10A, 9C⊬9B, 9A⊬7A)
- 10A/10B стартуют на 8 недель раньше
- RuntimeConfig → composition (typed groups)
- Migration plan для legacy (RuntimePort, SessionManager)
- Error handling strategy для multi-agent
- API Stability plan → semver после v1.0-core

## Завершено
- ✅ Phase 0-4: upstream middleware + multi-provider ThinRuntime (v0.5.0)
- ✅ Phase 6: DX Foundation (structured output, @tool, registry, cancel, typed events)
- ✅ Phase 7: Production Safety (cost budget, guardrails, input filters, retry/fallback)
- ✅ Phase 8: Persistence & UI (sessions, event bus, tracing, UI projection, RAG)
