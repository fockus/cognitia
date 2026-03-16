"""TDD Red Phase: MessageBus wiring + send_message tool (Этап 2.3).

Тесты проверяют:
- Agent A sends → Agent B receives через MessageBus
- broadcast → all agents receive
- send_message tool → message appears in bus

Contract: cognitia.orchestration.message_tools.send_message tool
+ MessageBus integration с ThinTeamOrchestrator
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cognitia.orchestration.message_bus import MessageBus
from cognitia.orchestration.team_types import TeamMessage

# ---------------------------------------------------------------------------
# MessageBus direct tests (существующий функционал — smoke)
# ---------------------------------------------------------------------------


class TestMessageBusSendReceive:
    """Базовая шина сообщений: send → receive."""

    @pytest.mark.asyncio
    async def test_message_bus_send_receive(self) -> None:
        """Agent A sends → Agent B receives."""
        bus = MessageBus()

        msg = TeamMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            content="Hello from A",
            timestamp=datetime.now(tz=UTC),
        )
        await bus.send(msg)

        inbox_b = await bus.get_inbox("agent_b")
        assert len(inbox_b) == 1
        assert inbox_b[0].content == "Hello from A"
        assert inbox_b[0].from_agent == "agent_a"

        # Agent A не видит сообщение в своём inbox
        inbox_a = await bus.get_inbox("agent_a")
        assert len(inbox_a) == 0

    @pytest.mark.asyncio
    async def test_message_bus_broadcast(self) -> None:
        """broadcast → all agents receive."""
        bus = MessageBus()

        await bus.broadcast(
            from_agent="lead",
            content="Everyone stop",
            recipients=["worker_0", "worker_1", "worker_2"],
        )

        for worker in ["worker_0", "worker_1", "worker_2"]:
            inbox = await bus.get_inbox(worker)
            assert len(inbox) == 1
            assert inbox[0].content == "Everyone stop"
            assert inbox[0].from_agent == "lead"

        # Lead не получает своё broadcast
        inbox_lead = await bus.get_inbox("lead")
        assert len(inbox_lead) == 0


# ---------------------------------------------------------------------------
# send_message tool (новый модуль)
# ---------------------------------------------------------------------------


class TestSendMessageTool:
    """send_message tool — workers отправляют сообщения через tool call."""

    @pytest.mark.asyncio
    async def test_message_tool_sends_via_bus(self) -> None:
        """Tool call send_message → message appears in MessageBus."""
        from cognitia.orchestration.message_tools import create_send_message_tool

        bus = MessageBus()
        send_message_executor = create_send_message_tool(
            bus=bus,
            sender_agent_id="worker_0",
        )

        # Вызываем tool как если бы LLM его вызвала
        await send_message_executor({
            "to_agent": "worker_1",
            "content": "I found the answer",
        })

        # Сообщение должно быть в шине
        inbox = await bus.get_inbox("worker_1")
        assert len(inbox) == 1
        assert inbox[0].content == "I found the answer"
        assert inbox[0].from_agent == "worker_0"

    @pytest.mark.asyncio
    async def test_message_tool_broadcast_via_bus(self) -> None:
        """Tool call send_message с to_agent='*' → broadcast."""
        from cognitia.orchestration.message_tools import create_send_message_tool

        bus = MessageBus()
        send_message_executor = create_send_message_tool(
            bus=bus,
            sender_agent_id="lead",
            team_members=["worker_0", "worker_1"],
        )

        await send_message_executor({
            "to_agent": "*",
            "content": "All hands meeting",
        })

        for worker in ["worker_0", "worker_1"]:
            inbox = await bus.get_inbox(worker)
            assert len(inbox) == 1

    def test_message_tool_spec_has_correct_schema(self) -> None:
        """send_message tool имеет правильный ToolSpec."""
        from cognitia.orchestration.message_tools import SEND_MESSAGE_TOOL_SPEC

        assert SEND_MESSAGE_TOOL_SPEC.name == "send_message"
        assert "to_agent" in str(SEND_MESSAGE_TOOL_SPEC.parameters)
        assert "content" in str(SEND_MESSAGE_TOOL_SPEC.parameters)
