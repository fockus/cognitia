# Cognitia Gaps for Code Factory v2

> **ОБНОВЛЕНО 2026-03-29** после аудита graph_* модуля.
> Большинство исходных gaps ЗАКРЫТЫ в `cognitia.multi_agent.graph_*`.

---

## CliAgentRuntime — РАБОТАЕТ

`runtime="cli"` уже запускает `claude --print --verbose --output-format stream-json -` через subprocess. Парсит NDJSON output через `ClaudeNdjsonParser`. Используется через подписку Claude Code, без API key. Gap закрыт.

---

## Gap 1: Agent Graph Traversal — ЗАКРЫТ

**Уже реализовано в `graph_store.py` (InMemory + SQLite + Postgres):**
- `get_subtree(node_id)` — все потомки (рекурсивно)
- `get_chain_of_command(node_id)` — путь от агента к root
- `snapshot()` — полный граф (nodes + edges)
- `find_by_role(role)` — поиск по роли
- `get_root()` — корневой узел

SQLite использует `WITH RECURSIVE` CTE. **Gap ЗАКРЫТ.**

---

## Gap 2: Task Dependencies (DAG) — ЧАСТИЧНО ЗАКРЫТ

**Уже реализовано в `graph_task_board.py` + `graph_task_types.py`:**
- `GraphTaskItem.parent_task_id` — иерархия задач
- `GraphTaskItem.goal_id` — привязка к цели
- `GraphTaskItem.dod_criteria` — критерии готовности
- `GraphTaskItem.checkout_agent_id` — атомарный lock
- `checkout_task(task_id, agent_id)` — atomic checkout (BEGIN IMMEDIATE)
- `complete_task(task_id)` — auto-propagation parent completion
- `get_subtasks(task_id)` — дочерние задачи
- `get_goal_ancestry(task_id)` — цепочка от root goal

**Чего НЕТ (остаточный gap):**
```python
# 1. Явные зависимости между задачами (не parent-child, а DAG)
#    GraphTaskItem НЕ имеет dependencies: tuple[str, ...]
#    Нет get_ready_tasks() — задачи у которых все deps DONE
#    Нет get_blocked_by(task_id) — что блокирует

# 2. Task delegation metadata
#    Нет delegated_by, delegation_reason в GraphTaskItem
#    (delegation есть в orchestrator, но не в task metadata)

# 3. Effort estimation
#    Нет estimated_effort: str (XS/S/M/L/XL)
#    Нет started_at / completed_at timestamps
```

**Варианты решения:**
- (a) Добавить `dependencies` field в `GraphTaskItem` + `get_ready_tasks()` в TaskBoard
- (b) Реализовать DAG как отдельный слой поверх существующего TaskBoard (в factory_lib)

Рекомендация: вариант (b) — не менять core Cognitia, добавить тонкий слой в factory.

---

## Gap 3: Inter-Agent Communication — ЗАКРЫТ

**Уже реализовано в `graph_communication.py` (5 backends):**
- `send_direct(msg)` — point-to-point
- `broadcast_subtree(from_id, content)` — broadcast потомкам
- `escalate(from_id, content)` — вверх по chain of command
- `get_inbox(agent_id)` — входящие сообщения
- `get_thread(task_id)` — thread по задаче

Backends: InMemory, SQLite, Postgres, Redis, NATS. **Gap ЗАКРЫТ.**

---

## Gap 4: Agent Delegation Protocol — ЗАКРЫТ

**Уже реализовано в `graph_orchestrator.py`:**
- `DelegationRequest(task_id, agent_id, goal, parent_task_id, max_retries)`
- `delegate(request)` — делегирование с approval gate
- `collect_result(task_id)` — получить результат
- `get_status(run_id)` — статус orchestration run
- `stop(run_id)` — остановить run
- `ApprovalGate` — optional gate для governance

Также `graph_tools.py` предоставляет agent-callable tools: `graph_hire_agent`, `graph_delegate_task`, `graph_escalate`.

**Gap ЗАКРЫТ.**

---

## Gap 5: SqliteAgentRegistry — ЗАКРЫТ

**Уже реализовано:**
- `agent_registry_sqlite.py` — SqliteAgentRegistry (flat registry)
- `graph_store_sqlite.py` — SqliteAgentGraph (hierarchical graph с traversal)

Оба с WAL mode, thread-safe. **Gap ЗАКРЫТ.**

---

## Gap 6: Agent Dynamic Reconfiguration — ОСТАЁТСЯ

**Что есть:** `AgentNode` / `AgentConfig` = frozen dataclass.

**Чего нет:** Способ пересоздать агента с новой конфигурацией, сохранив ID и историю.

**Решение:** `remove_node(id) → add_node(new_node_with_same_id)` работает, но теряет историю. Для factory нужен `update_node(id, **partial)` в AgentGraphStore.

**Приоритет:** LOW — workaround через remove+add достаточен для MVP.

---

## Дополнительные находки (НЕ gaps, а assets)

### orchestration/ модуль
```
PlanManager        — create/approve/execute/cancel plans (с SQLite/Postgres store)
ThinTeamOrchestrator — multi-agent team coordination
MessageBus         — inter-agent messaging (team mode)
DoDStateMachine    — Definition of Done verification
CodeVerifier       — code quality checks
TddCodeVerifier    — TDD-specific verification
```

### EventBus
```
InMemoryEventBus   — subscribe/unsubscribe/emit
                     Все graph_* компоненты emit events:
                     graph.orchestrator.started/delegated/denied/completed/escalated/stopped
                     graph.message.direct/broadcast/escalation
```

### GraphContextBuilder
```
build_context(agent_id) → GraphContextSnapshot
  chain_of_command, goal_ancestry, siblings, children, tools, shared_knowledge
render_system_prompt(snapshot) → str (with token_budget)
```

---

## Обновлённая сводка

| # | Gap | Статус | Действие |
|---|-----|--------|----------|
| 1 | Graph traversal | **ЗАКРЫТ** | Использовать graph_store.* |
| 2 | Task dependencies (DAG) | **ЧАСТИЧНО** | Добавить DAG layer в factory_lib |
| 3 | Comm channels | **ЗАКРЫТ** | Использовать graph_communication.* |
| 4 | Delegation tracking | **ЗАКРЫТ** | Использовать graph_orchestrator.* |
| 5 | SqliteAgentRegistry | **ЗАКРЫТ** | Использовать graph_store_sqlite / agent_registry_sqlite |
| 6 | Agent reconfiguration | **ОСТАЁТСЯ** | LOW — workaround через remove+add |

**Вывод:** Factory v2 должен быть ТОНКИМ СЛОЕМ поверх существующих Cognitia компонентов, а не параллельной реализацией. factory_lib добавляет только pipeline-специфичные сущности: sprints, goals/epics, costs, budget, circuit breaker, judge gates, phases, calibration.
