"""Tests for the EventEmitter and HiveEvent (S7 emission stream foundation)."""

import asyncio
import pytest
from hive.bus.emitter import EventEmitter, HiveEvent


# ---------------------------------------------------------------------------
# HiveEvent
# ---------------------------------------------------------------------------


def test_hive_event_to_dict():
    """HiveEvent.to_dict() returns a plain dict with type, data, ts."""
    event = HiveEvent(type="tool_call", data={"tool": "exec", "ok": True})
    d = event.to_dict()
    assert d["type"] == "tool_call"
    assert d["data"]["tool"] == "exec"
    assert d["data"]["ok"] is True
    assert "ts" in d  # Auto-filled timestamp


def test_hive_event_auto_timestamp():
    """HiveEvent auto-fills ts on creation."""
    event = HiveEvent(type="test")
    assert event.ts is not None
    assert len(event.ts) > 10  # ISO timestamp


# ---------------------------------------------------------------------------
# EventEmitter — basic pub/sub
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_to_single_subscriber():
    """Emitting an event delivers it to a single subscriber."""
    emitter = EventEmitter()
    sub_id, queue = emitter.subscribe()

    event = HiveEvent(type="tool_call", data={"tool": "exec"})
    await emitter.emit(event)

    received = queue.get_nowait()
    assert received.type == "tool_call"
    assert received.data["tool"] == "exec"

    emitter.unsubscribe(sub_id)


@pytest.mark.asyncio
async def test_emit_to_multiple_subscribers():
    """All subscribers receive the same event."""
    emitter = EventEmitter()
    _, q1 = emitter.subscribe()
    _, q2 = emitter.subscribe()
    _, q3 = emitter.subscribe()

    event = HiveEvent(type="llm_call", data={"model": "gemini"})
    await emitter.emit(event)

    for q in (q1, q2, q3):
        received = q.get_nowait()
        assert received.type == "llm_call"
        assert received.data["model"] == "gemini"


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    """After unsubscribe, events are no longer delivered to that subscriber."""
    emitter = EventEmitter()
    sub_id, queue = emitter.subscribe()

    # First event — should be delivered
    await emitter.emit(HiveEvent(type="test1"))
    assert not queue.empty()
    queue.get_nowait()

    # Unsubscribe
    emitter.unsubscribe(sub_id)

    # Second event — should NOT be delivered
    await emitter.emit(HiveEvent(type="test2"))
    assert queue.empty()


@pytest.mark.asyncio
async def test_emit_with_no_subscribers():
    """Emitting with no subscribers does not raise."""
    emitter = EventEmitter()
    # Should not raise
    await emitter.emit(HiveEvent(type="orphan"))


@pytest.mark.asyncio
async def test_queue_overflow_drops_oldest():
    """When a subscriber's queue is full, oldest events are dropped."""
    emitter = EventEmitter(queue_size=3)
    _, queue = emitter.subscribe()

    # Emit 5 events — queue can only hold 3
    for i in range(5):
        await emitter.emit(HiveEvent(type="test", data={"i": i}))

    # Queue should have the 3 most recent events (indices 2, 3, 4)
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    assert len(events) == 3
    assert events[0].data["i"] == 2
    assert events[1].data["i"] == 3
    assert events[2].data["i"] == 4


@pytest.mark.asyncio
async def test_subscriber_count():
    """subscriber_count tracks active subscribers."""
    emitter = EventEmitter()
    assert emitter.subscriber_count == 0

    s1, _ = emitter.subscribe()
    assert emitter.subscriber_count == 1

    s2, _ = emitter.subscribe()
    assert emitter.subscriber_count == 2

    emitter.unsubscribe(s1)
    assert emitter.subscriber_count == 1

    emitter.unsubscribe(s2)
    assert emitter.subscriber_count == 0


@pytest.mark.asyncio
async def test_unsubscribe_unknown_id_is_noop():
    """Unsubscribing with an unknown ID does not raise."""
    emitter = EventEmitter()
    # Should not raise
    emitter.unsubscribe("nonexistent-id")


@pytest.mark.asyncio
async def test_concurrent_emit_is_safe():
    """Multiple concurrent emits do not corrupt state."""
    emitter = EventEmitter()
    _, queue = emitter.subscribe()

    # Fire 50 events concurrently
    events = [HiveEvent(type="test", data={"i": i}) for i in range(50)]
    await asyncio.gather(*(emitter.emit(e) for e in events))

    # All 50 should arrive (default queue size is 1000)
    received = []
    while not queue.empty():
        received.append(queue.get_nowait())
    assert len(received) == 50
