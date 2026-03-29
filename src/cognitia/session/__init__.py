"""Sessions module - agent session management."""

from cognitia.session.backends import (
    InMemorySessionBackend,
    MemoryScope,
    SessionBackend,
    SqliteSessionBackend,
    scoped_key,
)
from cognitia.session.manager import InMemorySessionManager
from cognitia.session.rehydrator import DefaultSessionRehydrator
from cognitia.session.task_session_store import (
    InMemoryTaskSessionStore,
    SqliteTaskSessionStore,
    TaskSessionStore,
)
from cognitia.session.task_session_types import TaskSessionParams
from cognitia.session.types import SessionKey, SessionState

__all__ = [
    "DefaultSessionRehydrator",
    "InMemorySessionBackend",
    "InMemorySessionManager",
    "InMemoryTaskSessionStore",
    "MemoryScope",
    "SessionBackend",
    "SessionKey",
    "SessionState",
    "SqliteSessionBackend",
    "SqliteTaskSessionStore",
    "TaskSessionParams",
    "TaskSessionStore",
    "scoped_key",
]
