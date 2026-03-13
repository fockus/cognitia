# Memory Providers

Cognitia provides 3 interchangeable memory providers behind a unified protocol interface.

## Protocols

Memory is split into 8 ISP-compliant protocols (each <=5 methods):

| Protocol | Methods | Purpose |
|----------|---------|---------|
| `MessageStore` | `save_message`, `get_messages`, `count_messages`, `delete_messages_before` | Conversation history |
| `FactStore` | `upsert_fact`, `get_facts` | Key-value user facts |
| `GoalStore` | `save_goal`, `get_active_goal` | User goals |
| `SummaryStore` | `save_summary`, `get_summary` | Conversation summaries |
| `UserStore` | `ensure_user`, `get_user_profile` | User identity |
| `SessionStateStore` | `save_session_state`, `get_session_state` | Session metadata |
| `PhaseStore` | `save_phase_state`, `get_phase_state` | User phase tracking |
| `ToolEventStore` | `save_tool_event` | Tool usage audit trail |

All three providers implement all 8 protocols.

## InMemoryMemoryProvider

Zero-dependency, great for tests and development:

```python
from cognitia.memory import InMemoryMemoryProvider

memory = InMemoryMemoryProvider()

# Store a fact
await memory.upsert_fact("user_1", "name", "Alice")

# Retrieve facts
facts = await memory.get_facts("user_1")
print(facts)  # {"name": "Alice"}

# Store a message
await memory.save_message("user_1", "topic_1", "user", "Hello!")

# Get messages
messages = await memory.get_messages("user_1", "topic_1", limit=10)
```

Data lives in memory and is lost when the process exits.

## PostgresMemoryProvider

Production-ready with SQLAlchemy async:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from cognitia.memory import PostgresMemoryProvider

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
session_factory = async_sessionmaker(engine, expire_on_commit=False)

memory = PostgresMemoryProvider(session_factory)
```

Requires `pip install cognitia[postgres]`.

### Schema

Tables are managed by the application (via Alembic or raw SQL). Required tables:

- `messages` (user_id, topic_id, role, content, metadata, created_at)
- `facts` (user_id, topic_id, key, value, source, updated_at)
- `goals` (user_id, topic_id, data, created_at)
- `summaries` (user_id, topic_id, summary, messages_covered, created_at)
- `users` (external_id, user_id, created_at)
- `session_state` (user_id, topic_id, role_id, active_skill_ids, prompt_hash)
- `phase_state` (user_id, phase, notes, updated_at)
- `tool_events` (user_id, event_data, created_at)

## SQLiteMemoryProvider

Lightweight persistence without a database server:

```python
from cognitia.memory import SQLiteMemoryProvider

memory = SQLiteMemoryProvider(db_path="./agent.db")
# Tables are created automatically on first use
```

Requires `pip install cognitia[sqlite]`.

## Choosing a Provider

| Provider | Persistence | Setup | Best For |
|----------|-------------|-------|----------|
| InMemory | None | Zero | Tests, prototyping |
| SQLite | File-based | Minimal | Single-user apps, CLIs |
| PostgreSQL | Full | Database | Production, multi-user |

## Dependency Injection

All providers implement the same protocols. Swap with one line:

```python
# Development
memory = InMemoryMemoryProvider()

# Production
memory = PostgresMemoryProvider(session_factory)

# Your code uses protocols, not concrete classes:
async def save_user_fact(store: FactStore, user_id: str):
    await store.upsert_fact(user_id, "onboarded", "true")
```

## Summarization

Cognitia includes a summarizer for managing conversation history:

```python
from cognitia.memory.summarizer import TemplateSummaryGenerator

summarizer = TemplateSummaryGenerator()
summary = await summarizer.generate(messages, existing_summary="")
```

For LLM-powered summarization:

```python
from cognitia.memory.llm_summarizer import LlmSummaryGenerator

summarizer = LlmSummaryGenerator(model="sonnet")
summary = await summarizer.generate(messages)
```

History is automatically capped and summarized when it exceeds the configured limit.
