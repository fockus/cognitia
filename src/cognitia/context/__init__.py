"""Модуль контекста — сборка system_prompt с бюджетированием."""

from cognitia.context.budget import ContextBudget, estimate_tokens, truncate_to_budget
from cognitia.context.builder import (
    BuiltContext,
    ContextInput,
    DefaultContextBuilder,
    compute_prompt_hash,
)

__all__ = [
    "BuiltContext",
    "ContextBudget",
    "ContextInput",
    "DefaultContextBuilder",
    "compute_prompt_hash",
    "estimate_tokens",
    "truncate_to_budget",
]
