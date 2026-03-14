"""HITL/interrupt helpers для DeepAgents native path."""

from __future__ import annotations

from itertools import zip_longest
from typing import Any

from cognitia.runtime.types import RuntimeErrorData, RuntimeEvent


def validate_hitl_config(
    native_config: dict[str, Any],
) -> RuntimeErrorData | None:
    """Проверить, что interrupt/hitl config совместим с native graph state."""
    if native_config.get("interrupt_on") and native_config.get("checkpointer") is None:
        return RuntimeErrorData(
            kind="capability_unsupported",
            message=(
                "DeepAgents interrupt_on требует checkpointer в native_config, "
                "иначе resume/HITL невозможны."
            ),
            recoverable=False,
        )
    return None


def build_interrupt_events(chunk: dict[str, Any]) -> list[RuntimeEvent]:
    """Преобразовать LangGraph __interrupt__ chunk в portable RuntimeEvent list."""
    interrupts = chunk.get("__interrupt__") or ()
    events: list[RuntimeEvent] = []

    for raw_interrupt in interrupts:
        value = _interrupt_value(raw_interrupt)
        interrupt_id = _interrupt_id(raw_interrupt)

        if isinstance(value, dict) and {
            "action_requests",
            "review_configs",
        }.issubset(value):
            events.extend(
                _approval_events_from_hitl_request(
                    value,
                    interrupt_id=interrupt_id,
                )
            )
        elif isinstance(value, str):
            events.append(
                RuntimeEvent.user_input_requested(
                    prompt=value,
                    interrupt_id=interrupt_id,
                )
            )
        else:
            events.append(
                RuntimeEvent.native_notice(
                    "DeepAgents emitted unsupported interrupt payload",
                    metadata={
                        "interrupt_id": interrupt_id,
                        "value": repr(value),
                    },
                )
            )

    return events


def _approval_events_from_hitl_request(
    request: dict[str, Any],
    *,
    interrupt_id: str | None,
) -> list[RuntimeEvent]:
    action_requests = request.get("action_requests") or []
    review_configs = request.get("review_configs") or []
    events: list[RuntimeEvent] = []

    for action, review in zip_longest(action_requests, review_configs, fillvalue={}):
        action_name = action.get("name") or review.get("action_name") or ""
        if not action_name:
            events.append(
                RuntimeEvent.native_notice(
                    "DeepAgents interrupt payload missing action name",
                    metadata={"interrupt_id": interrupt_id},
                )
            )
            continue

        events.append(
            RuntimeEvent.approval_required(
                action_name=action_name,
                args=dict(action.get("args") or {}),
                allowed_decisions=list(review.get("allowed_decisions") or []),
                interrupt_id=interrupt_id,
                description=str(action.get("description") or ""),
            )
        )

    return events


def _interrupt_value(raw_interrupt: Any) -> Any:
    if isinstance(raw_interrupt, dict):
        return raw_interrupt.get("value")
    return getattr(raw_interrupt, "value", None)


def _interrupt_id(raw_interrupt: Any) -> str | None:
    if isinstance(raw_interrupt, dict):
        return raw_interrupt.get("id")
    return getattr(raw_interrupt, "id", None)
