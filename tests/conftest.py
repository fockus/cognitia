"""Shared test fixtures для cognitia tests."""

from __future__ import annotations

from typing import Any


class FakeStreamEvent:
    """Minimal StreamEvent-like mock для unit/integration/e2e тестов Agent Facade."""

    def __init__(self, type: str = "done", text: str = "", **kwargs: Any) -> None:
        self.type = type
        self.text = text
        self.is_final = kwargs.get("is_final", False)
        self.session_id = kwargs.get("session_id")
        self.total_cost_usd = kwargs.get("total_cost_usd")
        self.usage = kwargs.get("usage")
        self.structured_output = kwargs.get("structured_output")
        self.tool_name = kwargs.get("tool_name", "")
        self.tool_input = kwargs.get("tool_input")
        self.tool_result = kwargs.get("tool_result", "")
