"""Session backends and memory scopes.

Demonstrates: InMemorySessionBackend, MemoryScope, scoped_key.
No API keys required.
"""

import asyncio

from cognitia.session.backends import InMemorySessionBackend, MemoryScope, scoped_key


async def main() -> None:
    backend = InMemorySessionBackend()

    # 1. Save and load session state
    await backend.save("session-1", {"messages": ["Hello"], "turn": 1})
    state = await backend.load("session-1")
    print(f"Loaded state: {state}")

    # 2. Use memory scopes for agent isolation
    agent_key = scoped_key(MemoryScope.AGENT, "agent-alpha:memory")
    global_key = scoped_key(MemoryScope.GLOBAL, "shared-facts")
    shared_key = scoped_key(MemoryScope.SHARED, "team-context")

    print(f"Agent key:  {agent_key}")
    print(f"Global key: {global_key}")
    print(f"Shared key: {shared_key}")

    # 3. Store scoped data
    await backend.save(agent_key, {"facts": ["User likes Python"]})
    await backend.save(global_key, {"version": "1.0"})
    await backend.save(shared_key, {"project": "cognitia"})

    # 4. List all keys
    keys = await backend.list_keys()
    print(f"All keys: {keys}")

    # 5. Delete a key
    deleted = await backend.delete(agent_key)
    print(f"Deleted {agent_key}: {deleted}")
    print(f"Keys after delete: {await backend.list_keys()}")


if __name__ == "__main__":
    asyncio.run(main())
