"""CircuitBreaker — защита от каскадных сбоев MCP (секция 13 архитектуры).

Один breaker per server_id.
Состояния: CLOSED → OPEN → HALF_OPEN → CLOSED (или обратно в OPEN).
"""

from __future__ import annotations

import enum
import time


class CircuitState(enum.Enum):
    """Состояние circuit breaker."""

    CLOSED = "closed"  # Нормальная работа
    OPEN = "open"  # Отклоняет запросы
    HALF_OPEN = "half_open"  # Одна probe-попытка


class CircuitBreaker:
    """Circuit breaker для одного MCP-сервера.

    - failure_threshold: после скольких подряд ошибок открывается
    - cooldown_seconds: время в OPEN перед переходом в HALF_OPEN
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._state = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Текущее состояние breaker."""
        return self._state

    def allow_request(self) -> bool:
        """Разрешить запрос? Если OPEN и cooldown истёк → HALF_OPEN."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._cooldown:
                self._state = CircuitState.HALF_OPEN
                return True
            return False

        # HALF_OPEN — пропускаем одну probe-попытку
        return True

    def record_success(self) -> None:
        """Зафиксировать успешный вызов."""
        self._consecutive_failures = 0
        if self._state in (CircuitState.HALF_OPEN, CircuitState.CLOSED):
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Зафиксировать ошибку."""
        self._consecutive_failures += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            # Probe провалился — обратно в OPEN
            self._state = CircuitState.OPEN
            return

        if self._consecutive_failures >= self._threshold:
            self._state = CircuitState.OPEN


class CircuitBreakerRegistry:
    """Реестр circuit breakers per server_id."""

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, server_id: str) -> CircuitBreaker:
        """Получить или создать breaker для сервера."""
        if server_id not in self._breakers:
            self._breakers[server_id] = CircuitBreaker(
                failure_threshold=self._threshold,
                cooldown_seconds=self._cooldown,
            )
        return self._breakers[server_id]
