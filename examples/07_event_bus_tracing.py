"""Event bus and tracing -- publish-subscribe + span-based observability.

Demonstrates: InMemoryEventBus, NoopTracer, TracingSubscriber.
No API keys required. Uses NoopTracer to avoid structlog dependency.
"""

import asyncio

from cognitia.observability.event_bus import InMemoryEventBus
from cognitia.observability.tracer import NoopTracer, TracingSubscriber


async def main() -> None:
    bus = InMemoryEventBus()
    tracer = NoopTracer()

    # 1. Manual subscription
    events_log: list[str] = []

    def on_llm_start(data: dict) -> None:
        events_log.append(f"LLM started: model={data.get('model')}")

    def on_llm_end(data: dict) -> None:
        events_log.append(f"LLM ended: tokens={data.get('tokens')}")

    bus.subscribe("llm_call_start", on_llm_start)
    bus.subscribe("llm_call_end", on_llm_end)

    # 2. Emit events
    await bus.emit("llm_call_start", {"model": "gpt-4o"})
    await bus.emit("llm_call_end", {"tokens": 150})
    print(f"Events captured: {events_log}")

    # 3. TracingSubscriber bridges EventBus -> Tracer
    subscriber = TracingSubscriber(bus, tracer)
    subscriber.attach()

    await bus.emit("llm_call_start", {"model": "claude-sonnet"})
    await bus.emit("llm_call_end", {"tokens": 200})
    await bus.emit("tool_call_start", {"name": "search", "correlation_id": "t1"})
    await bus.emit("tool_call_end", {"name": "search", "correlation_id": "t1"})

    print("TracingSubscriber bridged events to NoopTracer spans.")

    # 4. Cleanup
    subscriber.detach()
    print("Detached subscriber.")


if __name__ == "__main__":
    asyncio.run(main())
