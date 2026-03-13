"""Result — unified результат запроса Agent facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    """Immutable результат query/stream запроса.

    ok=True если error is None (запрос успешен).
    """

    text: str = ""
    session_id: str | None = None
    total_cost_usd: float | None = None
    usage: dict[str, Any] | None = None
    structured_output: Any = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True если запрос завершился без ошибки."""
        return self.error is None
