"""Strategy re-exports для ThinRuntime.

Facade module: импортирует и реэкспортирует все strategy functions
и helpers из модулей-реализаций. Обеспечивает backward compatibility
для runtime.py и внешних потребителей.
"""

from cognitia.runtime.thin.conversational import run_conversational
from cognitia.runtime.thin.helpers import _build_metrics, _messages_to_lm
from cognitia.runtime.thin.planner_strategy import run_planner
from cognitia.runtime.thin.react_strategy import run_react

__all__ = [
    "_build_metrics",
    "_messages_to_lm",
    "run_conversational",
    "run_planner",
    "run_react",
]
