"""Тесты: cognitia.sessions удалён, каноничный модуль — cognitia.session.

Гарантируем, что:
- cognitia.session экспортирует все нужные классы
- cognitia.sessions больше не существует (удалён в v0.2.x)
"""

from __future__ import annotations

import pytest


class TestSessionsRemoved:
    """cognitia.sessions удалён, cognitia.session — единственный модуль."""

    def test_sessions_package_not_importable(self) -> None:
        """import cognitia.sessions → ModuleNotFoundError."""
        with pytest.raises(ModuleNotFoundError):
            import cognitia.sessions  # type: ignore[import-not-found]  # noqa: F401

    def test_canonical_session_importable(self) -> None:
        """import cognitia.session работает без ошибок."""
        from cognitia.session import (
            DefaultSessionRehydrator,
            InMemorySessionManager,
            SessionKey,
            SessionState,
        )

        assert DefaultSessionRehydrator is not None
        assert InMemorySessionManager is not None
        assert SessionKey is not None
        assert SessionState is not None
