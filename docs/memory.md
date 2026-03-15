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

## Data Types

The memory module uses these core data types (`cognitia.memory.types`):

| Type | Fields | Purpose |
|------|--------|---------|
| `MemoryMessage` | `role`, `content`, `tool_calls` | A single message in conversation history |
| `UserProfile` | `user_id`, `facts`, `created_at` | User identity with extracted facts |
| `GoalState` | `goal_id`, `title`, `target_amount`, `current_amount`, `phase`, `plan`, `is_main` | User goal tracking |
| `PhaseState` | `user_id`, `phase`, `notes` | Current conversation phase |
| `ToolEvent` | `topic_id`, `tool_name`, `input_json`, `output_json`, `latency_ms` | Tool usage audit entry |

## Summarization

Cognitia includes two summarizers for managing conversation history.

### TemplateSummaryGenerator

Zero-dependency, formats recent messages as a bullet list:

```python
from cognitia.memory.summarizer import TemplateSummaryGenerator
from cognitia.memory.types import MemoryMessage

summarizer = TemplateSummaryGenerator(max_messages=20, max_message_chars=200)

messages = [
    MemoryMessage(role="user", content="What's the weather?"),
    MemoryMessage(role="assistant", content="It's sunny today."),
]
summary = summarizer.summarize(messages)
# "- [user]: What's the weather?\n- [assistant]: It's sunny today."
```

### LlmSummaryGenerator

Uses an LLM call for richer summaries with automatic fallback to `TemplateSummaryGenerator` on error:

```python
from cognitia.memory.llm_summarizer import LlmSummaryGenerator

async def my_llm_call(prompt: str, text: str) -> str:
    # Your LLM integration here
    return await call_claude(prompt + "\n\n" + text)

summarizer = LlmSummaryGenerator(llm_call=my_llm_call)

# Sync (delegates to template fallback):
summary = summarizer.summarize(messages)

# Async (calls LLM, falls back on error):
summary = await summarizer.asummarize(messages)
```

If the LLM returns a response shorter than 50 characters or raises an exception, the template fallback is used automatically.

## Related: Memory Bank

For **long-term project memory** that persists across sessions (plans, decisions, progress logs), see [Memory Bank](memory-bank.md). Memory Bank is a separate capability with its own protocol and file-based API.
