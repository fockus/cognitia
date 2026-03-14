"""Conversation — explicit multi-turn управление диалогом."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from cognitia.agent.result import Result
from cognitia.runtime.types import Message

if TYPE_CHECKING:
    from cognitia.agent.agent import Agent


class Conversation:
    """Multi-turn conversation с Agent.

    Управляет историей сообщений и runtime lifecycle.
    - claude_sdk: warm subprocess (continue_conversation)
    - thin/deepagents: accumulated messages → AgentRuntime.run()
    """

    def __init__(
        self,
        agent: Agent,
        session_id: str | None = None,
    ) -> None:
        self._agent = agent
        self._session_id = session_id or uuid.uuid4().hex
        self._history: list[Message] = []
        self._adapter: Any = None  # RuntimeAdapter для claude_sdk
        self._connected = False

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def history(self) -> list[Message]:
        return list(self._history)

    async def say(self, prompt: str) -> Result:
        """Отправить сообщение и получить ответ."""
        # Apply middleware before_query
        from cognitia.agent.agent import apply_before_query

        effective_prompt = await apply_before_query(
            prompt, self._agent.config.middleware, self._agent.config,
        )

        self._history.append(Message(role="user", content=effective_prompt))

        # Execute + collect
        from cognitia.agent.agent import collect_stream_result

        collected = await collect_stream_result(self._execute(effective_prompt))

        if collected["text"]:
            self._history.append(Message(role="assistant", content=collected["text"]))

        # Conversation всегда заполняет session_id
        if not collected["session_id"]:
            collected["session_id"] = self._session_id

        result = Result(**collected)

        # Apply middleware after_result
        for mw in self._agent.config.middleware:
            result = await mw.after_result(result)

        return result

    async def stream(self, prompt: str) -> AsyncIterator[Any]:
        """Streaming multi-turn reply."""
        from cognitia.agent.agent import apply_before_query

        effective_prompt = await apply_before_query(
            prompt, self._agent.config.middleware, self._agent.config,
        )

        self._history.append(Message(role="user", content=effective_prompt))

        full_text = ""
        async for event in self._execute(effective_prompt):
            if event.type == "text_delta":
                full_text += event.text
            yield event

        if full_text:
            self._history.append(Message(role="assistant", content=full_text))

    async def close(self) -> None:
        """Закрыть conversation (отключить runtime)."""
        if self._adapter is not None and self._connected:
            await self._adapter.disconnect()
            self._connected = False
            self._adapter = None

    async def __aenter__(self) -> Conversation:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    async def _execute(self, prompt: str) -> AsyncIterator[Any]:
        """Route execution по runtime."""
        runtime_name = self._agent.config.runtime

        if runtime_name == "claude_sdk":
            async for event in self._execute_claude_sdk(prompt):
                yield event
        else:
            async for event in self._execute_agent_runtime(prompt, runtime_name):
                yield event

    async def _execute_claude_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """Multi-turn через Claude SDK (warm subprocess)."""
        if self._adapter is None:
            self._adapter = await self._create_adapter()
            self._connected = True

        async for event in self._adapter.stream_reply(prompt):
            yield event

    async def _execute_agent_runtime(
        self, prompt: str, runtime_name: str
    ) -> AsyncIterator[Any]:
        """Multi-turn через AgentRuntime (accumulated messages)."""
        from cognitia.agent.agent import _RuntimeEventAdapter
        from cognitia.runtime.factory import RuntimeFactory

        config = self._agent._build_runtime_config(runtime_name)
        if runtime_name == "deepagents":
            config.native_config = {
                **config.native_config,
                "thread_id": self._session_id,
            }
        factory = RuntimeFactory()
        runtime = factory.create(
            config=config,
            tool_executors={td.name: td.handler for td in self._agent.config.tools},
        )

        active_tools = [td.to_tool_spec() for td in self._agent.config.tools]

        try:
            async for event in runtime.run(
                messages=list(self._history),
                system_prompt=self._agent.config.system_prompt,
                active_tools=active_tools,
            ):
                yield _RuntimeEventAdapter(event)
        finally:
            await runtime.cleanup()

    async def _create_adapter(self) -> Any:
        """Создать и подключить RuntimeAdapter для claude_sdk."""
        from cognitia.agent.agent import merge_hooks
        from cognitia.hooks.sdk_bridge import registry_to_sdk_hooks
        from cognitia.runtime.adapter import RuntimeAdapter
        from cognitia.runtime.options_builder import ClaudeOptionsBuilder

        config = self._agent.config

        # Merge hooks из middleware + config
        merged_hooks = merge_hooks(config.hooks, config.middleware)

        # Build options
        builder = ClaudeOptionsBuilder(
            cwd=config.cwd,
            override_model=config.resolved_model,
        )

        sdk_mcp_servers = {}

        if config.tools:
            from cognitia.agent.agent import build_tools_mcp_server

            sdk_mcp_servers["__agent_tools__"] = build_tools_mcp_server(config.tools)

        sdk_hooks = None
        if merged_hooks:
            sdk_hooks = registry_to_sdk_hooks(merged_hooks)

        opts = builder.build(
            role_id="agent",
            system_prompt=config.system_prompt,
            mcp_servers=config.mcp_servers or None,
            sdk_mcp_servers=sdk_mcp_servers if sdk_mcp_servers else None,
            hooks=sdk_hooks,
            output_format=config.output_format,
            continue_conversation=True,
            max_turns=config.max_turns,
            permission_mode=config.permission_mode,
            setting_sources=list(config.setting_sources) if config.setting_sources else None,
            betas=list(config.betas) if config.betas else None,
            max_budget_usd=config.max_budget_usd,
            max_thinking_tokens=config.max_thinking_tokens,
            fallback_model=config.fallback_model,
            sandbox=config.sandbox,
            env=dict(config.env) if config.env else None,
            include_partial_messages=bool(
                config.native_config.get("include_partial_messages")
            ),
        )

        adapter = RuntimeAdapter(opts)
        await adapter.connect()
        return adapter

    def _merge_hooks(self) -> Any:
        """Merge hooks из config.hooks + middleware.get_hooks()."""
        from cognitia.agent.agent import merge_hooks

        return merge_hooks(self._agent.config.hooks, self._agent.config.middleware)
