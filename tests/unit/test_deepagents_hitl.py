"""Unit: HITL/interrupt helpers для DeepAgents native path."""

from __future__ import annotations

from langgraph.types import Interrupt

from cognitia.runtime.deepagents_hitl import (
    build_interrupt_events,
    validate_hitl_config,
)


def test_validate_hitl_config_requires_checkpointer() -> None:
    """interrupt_on без checkpointer должен fail-fast."""
    error = validate_hitl_config({"interrupt_on": {"edit_file": True}})

    assert error is not None
    assert error.kind == "capability_unsupported"
    assert "checkpointer" in error.message


def test_build_interrupt_events_maps_hitl_request_to_approval_required() -> None:
    """HITLRequest payload маппится в approval_required event."""
    interrupt = Interrupt(
        value={
            "action_requests": [
                {
                    "name": "edit_file",
                    "args": {"path": "app.py"},
                    "description": "Review file edit",
                }
            ],
            "review_configs": [
                {
                    "action_name": "edit_file",
                    "allowed_decisions": ["approve", "edit", "reject"],
                }
            ],
        },
        id="interrupt-1",
    )

    events = build_interrupt_events({"__interrupt__": (interrupt,)})

    assert len(events) == 1
    event = events[0]
    assert event.type == "approval_required"
    assert event.data["action_name"] == "edit_file"
    assert event.data["args"] == {"path": "app.py"}
    assert event.data["allowed_decisions"] == ["approve", "edit", "reject"]
    assert event.data["interrupt_id"] == "interrupt-1"
    assert event.data["description"] == "Review file edit"


def test_build_interrupt_events_maps_string_interrupt_to_user_input_requested() -> None:
    """Строковый interrupt value маппится в user_input_requested."""
    interrupt = Interrupt(value="Need human answer", id="interrupt-2")

    events = build_interrupt_events({"__interrupt__": (interrupt,)})

    assert len(events) == 1
    event = events[0]
    assert event.type == "user_input_requested"
    assert event.data["prompt"] == "Need human answer"
    assert event.data["interrupt_id"] == "interrupt-2"
