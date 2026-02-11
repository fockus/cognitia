"""Mode detection для ThinRuntime — эвристика выбора режима.

Правила (KISS):
- mode_hint задан → используем его
- Иначе keyword heuristics:
  - "план/стратегия/пошагово/дорожная карта" → planner
  - "подбери/найди/сравни" → react
  - Иначе → conversational
"""

from __future__ import annotations

import re
from collections.abc import Sequence

# Паттерны для planner mode
_PLANNER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bплан\b", re.IGNORECASE),
    re.compile(r"\bстратеги", re.IGNORECASE),
    re.compile(r"\bпошагов", re.IGNORECASE),
    re.compile(r"\bдорожн", re.IGNORECASE),
]

# Паттерны для react mode
_REACT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bподбер", re.IGNORECASE),
    re.compile(r"\bнайд", re.IGNORECASE),
    re.compile(r"\bсравни", re.IGNORECASE),
]

VALID_MODES = frozenset({"conversational", "react", "planner"})


def detect_mode(
    text: str,
    mode_hint: str | None = None,
    react_patterns: Sequence[re.Pattern[str]] | None = None,
    planner_patterns: Sequence[re.Pattern[str]] | None = None,
) -> str:
    """Определить режим ThinRuntime для данного turn'а.

    Args:
        text: Текст пользователя.
        mode_hint: Явная подсказка ("conversational", "react", "planner").
        react_patterns: Кастомные паттерны для react-режима.
        planner_patterns: Кастомные паттерны для planner-режима.

    Returns:
        Один из: "conversational", "react", "planner".
    """
    # Приоритет 1: явный hint
    if mode_hint and mode_hint in VALID_MODES:
        return mode_hint

    # Приоритет 2: planner keywords
    effective_planner_patterns = planner_patterns or _PLANNER_PATTERNS
    for pattern in effective_planner_patterns:
        if pattern.search(text):
            return "planner"

    # Приоритет 3: react keywords
    effective_react_patterns = react_patterns or _REACT_PATTERNS
    for pattern in effective_react_patterns:
        if pattern.search(text):
            return "react"

    # Default
    return "conversational"
