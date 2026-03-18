"""Shared helpers для strategy functions ThinRuntime."""

from __future__ import annotations

import time

from cognitia.runtime.types import (
    Message,
    RuntimeConfig,
    TurnMetrics,
)


def _messages_to_lm(messages: list[Message]) -> list[dict[str, str]]:
    """Конвертировать Message -> dict для LLM."""
    result = []
    for m in messages:
        d: dict[str, str] = {"role": m.role, "content": m.content}
        if m.name:
            d["name"] = m.name
        result.append(d)
    return result


def _build_metrics(
    start_time: float,
    config: RuntimeConfig,
    iterations: int = 0,
    tool_calls: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> TurnMetrics:
    """Собрать метрики turn'а."""
    return TurnMetrics(
        latency_ms=int((time.monotonic() - start_time) * 1000),
        iterations=iterations,
        tool_calls_count=tool_calls,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=config.model,
    )


def _should_buffer_postprocessing(config: RuntimeConfig) -> bool:
    """Нужен ли buffered output path для безопасного post-processing."""
    return bool(
        config.output_guardrails
        or config.output_type is not None
        or config.retry_policy is not None
    )
