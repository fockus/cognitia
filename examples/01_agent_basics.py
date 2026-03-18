"""Agent basics: query, stream, and multi-turn conversation.

Demonstrates: Agent, AgentConfig, query(), stream(), conversation().
Requires ANTHROPIC_API_KEY (or set COGNITIA_RUNTIME=thin + appropriate key).
"""

import asyncio

from cognitia import Agent, AgentConfig


async def main() -> None:
    # --- 1. One-shot query ---
    agent = Agent(AgentConfig(
        system_prompt="You are a helpful assistant. Reply concisely.",
        runtime="thin",
        model="sonnet",
    ))

    result = await agent.query("What is the capital of France?")
    print(f"Query result: {result.text}")
    print(f"Session ID: {result.session_id}")
    if result.usage:
        print(f"Tokens used: {result.usage}")

    # --- 2. Streaming response ---
    print("\nStreaming:")
    async for event in agent.stream("Write a haiku about Python"):
        if event.type == "text_delta":
            print(event.text, end="", flush=True)
        elif event.type == "tool_use_start":
            print(f"\n[Tool: {event.tool_name}]")
    print()  # newline after stream

    # --- 3. Multi-turn conversation ---
    print("\nConversation:")
    async with agent.conversation() as conv:
        r1 = await conv.say("My name is Alice")
        print(f"Turn 1: {r1.text}")

        r2 = await conv.say("What's my name?")
        print(f"Turn 2: {r2.text}")

        # Streaming inside a conversation
        print("Turn 3 (stream): ", end="")
        async for event in conv.stream("Tell me a one-line joke"):
            if event.type == "text_delta":
                print(event.text, end="", flush=True)
        print()

    # --- 4. Context manager cleanup ---
    async with Agent(AgentConfig(
        system_prompt="You are a math tutor.",
        runtime="thin",
    )) as math_agent:
        r = await math_agent.query("What is 17 * 23?")
        print(f"\nMath: {r.text}")
    # cleanup called automatically


if __name__ == "__main__":
    asyncio.run(main())
