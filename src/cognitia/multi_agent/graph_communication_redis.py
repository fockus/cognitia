"""Redis-backed graph communication — real-time inter-agent messaging via Redis Streams.

Messages are stored in Redis Streams (persistent, ordered, replayable).
Each agent's inbox is a Stream: ``cognitia:inbox:{agent_id}``.
Task threads use a Stream: ``cognitia:thread:{task_id}``.
Requires ``redis[hiredis]`` (lazy import).
"""

from __future__ import annotations

import uuid
from typing import Any

from cognitia.multi_agent.graph_comm_types import ChannelType, GraphMessage


class RedisGraphCommunication:
    """Redis Streams-based implementation of GraphCommunication.

    Uses Redis Streams for persistent, ordered message storage:
    - Inbox: ``{prefix}:inbox:{agent_id}`` stream
    - Thread: ``{prefix}:thread:{task_id}`` stream

    Optionally emits events via EventBus.
    """

    def __init__(
        self,
        redis_url: str,
        graph_query: Any,
        *,
        event_bus: Any | None = None,
        stream_prefix: str = "cognitia",
        max_stream_len: int = 10000,
    ) -> None:
        self._url = redis_url
        self._graph = graph_query
        self._bus = event_bus
        self._prefix = stream_prefix
        self._max_len = max_stream_len
        self._redis: Any = None

    async def connect(self) -> None:
        """Initialize Redis connection."""
        try:
            from redis.asyncio import Redis
        except ImportError as exc:
            raise ImportError(
                "redis package required: pip install 'cognitia[redis]' "
                "or pip install redis[hiredis]"
            ) from exc
        self._redis = Redis.from_url(self._url, decode_responses=True)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()

    def _inbox_key(self, agent_id: str) -> str:
        return f"{self._prefix}:inbox:{agent_id}"

    def _thread_key(self, task_id: str) -> str:
        return f"{self._prefix}:thread:{task_id}"

    async def _store_msg(self, msg: GraphMessage) -> None:
        """Store message in agent's inbox stream + task thread stream."""
        if self._redis is None:
            raise RuntimeError("Not connected — call connect() first")

        fields = {
            "id": msg.id, "from": msg.from_agent_id, "to": msg.to_agent_id,
            "channel": msg.channel.value, "content": msg.content,
            "task_id": msg.task_id or "",
        }
        # Add to inbox
        await self._redis.xadd(
            self._inbox_key(msg.to_agent_id), fields, maxlen=self._max_len,
        )
        # Add to task thread if task_id present
        if msg.task_id:
            await self._redis.xadd(
                self._thread_key(msg.task_id), fields, maxlen=self._max_len,
            )

    @staticmethod
    def _parse_msg(entry: dict[str, str]) -> GraphMessage:
        return GraphMessage(
            id=entry["id"], from_agent_id=entry["from"],
            to_agent_id=entry["to"], channel=ChannelType(entry["channel"]),
            content=entry["content"], task_id=entry["task_id"] or None,
        )

    async def send_direct(self, msg: GraphMessage) -> None:
        await self._store_msg(msg)
        await self._emit("graph.message.direct", msg)

    async def broadcast_subtree(
        self, from_id: str, content: str, *, task_id: str | None = None,
    ) -> None:
        descendants = await self._graph.get_subtree(from_id)
        for node in descendants:
            if node.id == from_id:
                continue
            msg = GraphMessage(
                id=uuid.uuid4().hex,
                from_agent_id=from_id, to_agent_id=node.id,
                channel=ChannelType.BROADCAST,
                content=content, task_id=task_id,
            )
            await self._store_msg(msg)
            await self._emit("graph.message.broadcast", msg)

    async def escalate(
        self, from_id: str, content: str, *, task_id: str | None = None,
    ) -> None:
        chain = await self._graph.get_chain_of_command(from_id)
        for node in chain[1:]:
            msg = GraphMessage(
                id=uuid.uuid4().hex,
                from_agent_id=from_id, to_agent_id=node.id,
                channel=ChannelType.ESCALATION,
                content=content, task_id=task_id,
            )
            await self._store_msg(msg)
            await self._emit("graph.message.escalation", msg)

    async def get_inbox(self, agent_id: str) -> list[GraphMessage]:
        if self._redis is None:
            return []
        entries = await self._redis.xrange(self._inbox_key(agent_id))
        return [self._parse_msg(fields) for _, fields in entries]

    async def get_thread(self, task_id: str) -> list[GraphMessage]:
        if self._redis is None:
            return []
        entries = await self._redis.xrange(self._thread_key(task_id))
        return [self._parse_msg(fields) for _, fields in entries]

    async def _emit(self, topic: str, msg: GraphMessage) -> None:
        if self._bus is not None:
            await self._bus.emit(topic, {
                "id": msg.id, "from": msg.from_agent_id,
                "to": msg.to_agent_id, "channel": msg.channel.value,
                "task_id": msg.task_id,
            })
