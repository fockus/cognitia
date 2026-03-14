"""Unit: Conversation — explicit multi-turn управление диалогом."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import FakeStreamEvent

from cognitia.agent.agent import Agent
from cognitia.agent.config import AgentConfig
from cognitia.agent.conversation import Conversation

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(**overrides: Any) -> Agent:
    defaults = {"system_prompt": "test prompt"}
    defaults.update(overrides)
    return Agent(AgentConfig(**defaults))


# ---------------------------------------------------------------------------
# Conversation.say()
# ---------------------------------------------------------------------------


class TestConversationSay:
    """Conversation.say() → Result."""

    @pytest.mark.asyncio
    async def test_say_returns_result(self) -> None:
        agent = _make_agent()
        conv = Conversation(agent=agent)

        async def fake_execute(prompt):
            yield FakeStreamEvent("text_delta", text="Hi!")
            yield FakeStreamEvent(
                "done",
                text="Hi!",
                is_final=True,
                session_id="s1",
                total_cost_usd=0.01,
                native_metadata={"thread_id": "thread-1"},
            )

        with patch.object(conv, "_execute", side_effect=fake_execute):
            result = await conv.say("Hello")

        assert result.ok is True
        assert result.text == "Hi!"
        assert result.session_id == "s1"
        assert result.native_metadata == {"thread_id": "thread-1"}

    @pytest.mark.asyncio
    async def test_multi_turn_accumulates_history(self) -> None:
        """Несколько say() → history растёт."""
        agent = _make_agent()
        conv = Conversation(agent=agent)

        call_count = 0

        async def fake_execute(prompt):
            nonlocal call_count
            call_count += 1
            yield FakeStreamEvent("text_delta", text=f"Reply {call_count}")
            yield FakeStreamEvent("done", text=f"Reply {call_count}", is_final=True)

        with patch.object(conv, "_execute", side_effect=fake_execute):
            r1 = await conv.say("First")
            r2 = await conv.say("Second")

        assert r1.text == "Reply 1"
        assert r2.text == "Reply 2"
        assert len(conv.history) == 4  # 2 user + 2 assistant
        assert conv.history[0].role == "user"
        assert conv.history[0].content == "First"
        assert conv.history[1].role == "assistant"
        assert conv.history[1].content == "Reply 1"
        assert conv.history[2].role == "user"
        assert conv.history[2].content == "Second"
        assert conv.history[3].role == "assistant"
        assert conv.history[3].content == "Reply 2"


# ---------------------------------------------------------------------------
# Conversation.stream()
# ---------------------------------------------------------------------------


class TestConversationStream:
    """Conversation.stream() → streaming events."""

    @pytest.mark.asyncio
    async def test_stream_yields_events(self) -> None:
        agent = _make_agent()
        conv = Conversation(agent=agent)

        async def fake_execute(prompt):
            yield FakeStreamEvent("text_delta", text="chunk1")
            yield FakeStreamEvent("text_delta", text="chunk2")
            yield FakeStreamEvent("done", text="chunk1chunk2", is_final=True)

        with patch.object(conv, "_execute", side_effect=fake_execute):
            events = []
            async for event in conv.stream("Hi"):
                events.append(event)

        assert len(events) == 3
        # History updated
        assert len(conv.history) == 2  # user + assistant
        assert conv.history[1].content == "chunk1chunk2"


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


class TestConversationSessionId:
    """session_id management."""

    def test_auto_generated_session_id(self) -> None:
        agent = _make_agent()
        conv = Conversation(agent=agent)
        assert conv.session_id  # non-empty
        assert len(conv.session_id) == 32  # uuid hex

    def test_explicit_session_id(self) -> None:
        agent = _make_agent()
        conv = Conversation(agent=agent, session_id="my-session")
        assert conv.session_id == "my-session"

    def test_two_conversations_different_ids(self) -> None:
        agent = _make_agent()
        c1 = Conversation(agent=agent)
        c2 = Conversation(agent=agent)
        assert c1.session_id != c2.session_id


class TestConversationHistory:
    """history property."""

    def test_empty_initially(self) -> None:
        agent = _make_agent()
        conv = Conversation(agent=agent)
        assert conv.history == []

    def test_history_is_copy(self) -> None:
        """history returns a copy, not internal list."""
        agent = _make_agent()
        conv = Conversation(agent=agent)
        h1 = conv.history
        h2 = conv.history
        assert h1 is not h2


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestConversationLifecycle:
    """close() + context manager."""

    @pytest.mark.asyncio
    async def test_close_fresh_conversation(self) -> None:
        """close() на свежей conversation — не ломается."""
        agent = _make_agent()
        conv = Conversation(agent=agent)
        await conv.close()

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        agent = _make_agent()
        async with Conversation(agent=agent) as conv:
            assert isinstance(conv, Conversation)

    @pytest.mark.asyncio
    async def test_close_disconnects_adapter(self) -> None:
        """Если adapter подключён → close() отключает."""
        agent = _make_agent()
        conv = Conversation(agent=agent)

        mock_adapter = AsyncMock()
        mock_adapter.disconnect = AsyncMock()
        conv._adapter = mock_adapter
        conv._connected = True

        await conv.close()

        mock_adapter.disconnect.assert_awaited_once()
        assert conv._connected is False

    @pytest.mark.asyncio
    async def test_create_adapter_propagates_runtime_options(self) -> None:
        """_create_adapter пробрасывает remote MCP, max_turns, permission_mode и setting_sources."""
        from cognitia.hooks.registry import HookRegistry
        from cognitia.skills.types import McpServerSpec

        hooks = HookRegistry()

        async def noop(**kwargs: Any) -> dict[str, Any]:
            return {"continue_": True}

        hooks.on_pre_tool_use(noop)

        agent = _make_agent(
            hooks=hooks,
            mcp_servers={"iss": McpServerSpec(name="iss", url="http://iss.test")},
            max_turns=7,
            permission_mode="plan",
            setting_sources=("project", "user"),
            env={"X": "1"},
            native_config={"include_partial_messages": True},
        )
        conv = Conversation(agent=agent)

        fake_builder = MagicMock()
        fake_builder.build.return_value = "opts"
        fake_adapter = AsyncMock()

        with (
            patch(
                "cognitia.runtime.options_builder.ClaudeOptionsBuilder",
                return_value=fake_builder,
            ),
            patch("cognitia.runtime.adapter.RuntimeAdapter", return_value=fake_adapter),
            patch(
                "cognitia.hooks.sdk_bridge.registry_to_sdk_hooks",
                return_value={"PreToolUse": []},
            ),
        ):
            adapter = await conv._create_adapter()

        assert adapter is fake_adapter
        fake_builder.build.assert_called_once()
        kwargs = fake_builder.build.call_args.kwargs
        assert kwargs["mcp_servers"] == agent.config.mcp_servers
        assert kwargs["max_turns"] == 7
        assert kwargs["permission_mode"] == "plan"
        assert kwargs["setting_sources"] == ["project", "user"]
        assert kwargs["env"] == {"X": "1"}
        assert kwargs["include_partial_messages"] is True

    @pytest.mark.asyncio
    async def test_execute_agent_runtime_passes_tool_executors(self) -> None:
        from cognitia.agent.tool import tool

        @tool(name="calc", description="Calculator")
        async def calc(expr: str) -> str:
            return "42"

        agent = _make_agent(runtime="deepagents", tools=(calc.__tool_definition__,))
        conv = Conversation(agent=agent)

        class FakeRuntime:
            async def run(self, **kwargs: Any):
                from cognitia.runtime.types import RuntimeEvent

                yield RuntimeEvent.final("ok")

            async def cleanup(self) -> None:
                return None

        fake_factory = MagicMock()
        fake_factory.create.return_value = FakeRuntime()

        with patch("cognitia.runtime.factory.RuntimeFactory", return_value=fake_factory):
            events = []
            async for event in conv._execute_agent_runtime("hello", "deepagents"):
                events.append(event)

        assert events[-1].type == "done"
        create_kwargs = fake_factory.create.call_args.kwargs
        assert create_kwargs["tool_executors"]["calc"] is calc.__tool_definition__.handler


# ---------------------------------------------------------------------------
# _merge_hooks
# ---------------------------------------------------------------------------


class TestConversationMergeHooks:
    """_merge_hooks — merge hooks из config и middleware."""

    def test_no_hooks_returns_none(self) -> None:
        """Без hooks и middleware → None."""
        agent = _make_agent()
        conv = Conversation(agent=agent)
        assert conv._merge_hooks() is None

    def test_only_config_hooks(self) -> None:
        """Только config.hooks → возвращает тот же registry."""
        from cognitia.hooks.registry import HookRegistry

        hooks = HookRegistry()

        async def noop(**kwargs: Any) -> dict[str, Any]:
            return {"continue_": True}

        hooks.on_pre_tool_use(noop)

        agent = _make_agent(hooks=hooks)
        conv = Conversation(agent=agent)
        merged = conv._merge_hooks()
        assert merged is hooks  # same object, no merge needed

    def test_only_middleware_hooks(self) -> None:
        """Middleware с hooks, без config.hooks → middleware hooks."""
        from cognitia.agent.middleware import SecurityGuard

        guard = SecurityGuard(block_patterns=["rm -rf"])
        agent = _make_agent(middleware=(guard,))
        conv = Conversation(agent=agent)
        merged = conv._merge_hooks()
        assert merged is not None
        assert "PreToolUse" in merged.list_events()

    def test_merge_config_and_middleware(self) -> None:
        """Config hooks + middleware hooks → merged registry."""
        from cognitia.agent.middleware import SecurityGuard
        from cognitia.hooks.registry import HookRegistry

        config_hooks = HookRegistry()

        async def noop(**kwargs: Any) -> dict[str, Any]:
            return {"continue_": True}

        config_hooks.on_post_tool_use(noop)

        guard = SecurityGuard(block_patterns=["rm -rf"])
        agent = _make_agent(hooks=config_hooks, middleware=(guard,))
        conv = Conversation(agent=agent)
        merged = conv._merge_hooks()
        assert merged is not None
        events = merged.list_events()
        assert "PostToolUse" in events
        assert "PreToolUse" in events
