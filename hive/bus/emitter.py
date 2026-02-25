"""Generic async event emitter for system telemetry.

Provides a fan-out pub/sub mechanism for internal system events (tool calls,
LLM calls, worker lifecycle, budget updates). Subscribers receive events via
bounded asyncio queues — slow consumers drop oldest events, never block the
emitter.

This is intentionally separate from MessageBus (channel I/O) and AuditLogger
(disk persistence). Each serves a different concern.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from loguru import logger


@dataclass
class HiveEvent:
    """A single telemetry event emitted by the hive system.

    Attributes:
        type: Event category — "tool_call", "llm_call", "worker", "budget",
              "channel", "system", "heartbeat".
        data: Arbitrary payload dict specific to the event type.
        ts: ISO 8601 UTC timestamp (auto-filled on creation).
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON encoding."""
        return asdict(self)


# Maximum events buffered per subscriber before oldest are dropped.
_DEFAULT_QUEUE_SIZE = 1000


class EventEmitter:
    """Async fan-out event emitter for hive system telemetry.

    Thread-safe via asyncio.Lock. Each subscriber gets its own bounded
    asyncio.Queue. If a subscriber falls behind, oldest events are silently
    dropped — the emitter never blocks.

    Usage:
        emitter = EventEmitter()
        sub_id = emitter.subscribe(my_async_callback)
        await emitter.emit(HiveEvent(type="tool_call", data={...}))
        emitter.unsubscribe(sub_id)
    """

    def __init__(self, queue_size: int = _DEFAULT_QUEUE_SIZE) -> None:
        self._queue_size = queue_size
        # Map subscription_id → asyncio.Queue
        self._subscribers: dict[str, asyncio.Queue[HiveEvent]] = {}
        self._lock = asyncio.Lock()

    async def emit(self, event: HiveEvent) -> None:
        """Fan out an event to all subscribers.

        Never raises — a failed delivery to one subscriber does not affect
        others. If a subscriber's queue is full, the oldest event is dropped
        to make room (bounded buffer, no backpressure).
        """
        async with self._lock:
            for sub_id, queue in self._subscribers.items():
                try:
                    if queue.full():
                        # Drop oldest event to make room — never block the emitter.
                        try:
                            queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    queue.put_nowait(event)
                except Exception as exc:
                    logger.debug(f"[emitter] Failed to deliver to {sub_id}: {exc}")

    def subscribe(
        self,
        callback: Callable[[HiveEvent], Awaitable[None]] | None = None,
    ) -> tuple[str, asyncio.Queue[HiveEvent]]:
        """Register a new subscriber.

        Returns:
            Tuple of (subscription_id, queue). The caller can either:
            - Poll the queue directly (StreamServer pattern), or
            - Pass a callback that will be invoked (future use).

        The queue is bounded at ``queue_size`` events. Overflow drops oldest.
        """
        sub_id = str(uuid.uuid4())
        queue: asyncio.Queue[HiveEvent] = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers[sub_id] = queue
        logger.debug(f"[emitter] New subscriber: {sub_id} (total: {len(self._subscribers)})")
        return sub_id, queue

    def unsubscribe(self, sub_id: str) -> None:
        """Remove a subscriber by ID. No-op if not found."""
        removed = self._subscribers.pop(sub_id, None)
        if removed is not None:
            logger.debug(f"[emitter] Unsubscribed: {sub_id} (remaining: {len(self._subscribers)})")

    @property
    def subscriber_count(self) -> int:
        """Number of active subscribers."""
        return len(self._subscribers)
