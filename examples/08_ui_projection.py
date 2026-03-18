"""UI event projection -- transform RuntimeEvent streams into UIState.

Demonstrates: ChatProjection, project_stream, RuntimeEvent factories.
No API keys required.
"""

import asyncio
from collections.abc import AsyncIterator

from cognitia.runtime.types import RuntimeEvent
from cognitia.ui.projection import ChatProjection, project_stream


async def fake_event_stream() -> AsyncIterator[RuntimeEvent]:
    """Simulate a runtime event stream."""
    yield RuntimeEvent.assistant_delta("Hello, ")
    yield RuntimeEvent.assistant_delta("how can I help?")
    yield RuntimeEvent.tool_call_started("search", args={"query": "weather"}, correlation_id="c1")
    yield RuntimeEvent.tool_call_finished("search", correlation_id="c1", ok=True, result_summary="Sunny, 22C")
    yield RuntimeEvent.assistant_delta(" It's sunny today!")
    yield RuntimeEvent.final(text="Hello, how can I help? It's sunny today!")


async def main() -> None:
    # 1. Manual apply -- step by step
    proj = ChatProjection()
    proj.apply(RuntimeEvent.assistant_delta("Step-by-step "))
    state = proj.apply(RuntimeEvent.assistant_delta("demo."))
    print(f"Messages: {len(state.messages)}, Status: {state.status}")

    # 2. project_stream -- async iteration
    stream = fake_event_stream()
    proj2 = ChatProjection()
    async for ui_state in project_stream(stream, proj2):
        msg_count = len(ui_state.messages)
        block_count = sum(len(m.blocks) for m in ui_state.messages)
        print(f"Status={ui_state.status}, messages={msg_count}, blocks={block_count}")

    # 3. Serialize to dict (for JSON API / WebSocket)
    final_dict = ui_state.to_dict()
    print(f"Serialized keys: {list(final_dict.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
