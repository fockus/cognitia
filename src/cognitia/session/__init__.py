"""Модуль сессий — управление сессиями агента."""

from cognitia.session.backends import (
    InMemorySessionBackend,
    MemoryScope,
    SessionBackend,
    SqliteSessionBackend,
    scoped_key,
)
from cognitia.session.manager import InMemorySessionManager
from cognitia.session.rehydrator import DefaultSessionRehydrator
from cognitia.session.types import SessionKey, SessionState

__all__ = [
    "DefaultSessionRehydrator",
    "InMemorySessionBackend",
    "InMemorySessionManager",
    "MemoryScope",
    "SessionBackend",
    "SessionKey",
    "SessionState",
    "SqliteSessionBackend",
    "scoped_key",
]
