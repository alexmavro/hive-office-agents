"""Tests for the S7 WebSocket stream server."""

import asyncio
import json
import pytest

from hive.bus.emitter import EventEmitter, HiveEvent
from hive.stream.server import StreamServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_server(port: int, **kwargs) -> StreamServer:
    """Create, start, and return a StreamServer bound to the given port.

    Test-friendly defaults: very short heartbeat and ping intervals to
    avoid long teardown waits.
    """
    kwargs.setdefault("heartbeat_interval", 999)
    kwargs.setdefault("ping_interval", None)  # Disable ping for tests
    kwargs.setdefault("ping_timeout", None)  # Disable pong timeout for tests
    emitter = kwargs.pop("emitter", EventEmitter())
    server = StreamServer(emitter, host="127.0.0.1", port=port, **kwargs)
    await server.start()
    return server, emitter


async def _cleanup(server: StreamServer) -> None:
    """Stop server cleanly."""
    await server.stop()


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_starts_and_stops():
    """StreamServer starts and stops cleanly without errors."""
    server, _ = await _make_server(19100)
    await _cleanup(server)


# ---------------------------------------------------------------------------
# Client communication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_receives_welcome():
    """Client receives a welcome system event on connect."""
    import websockets.asyncio.client

    server, _ = await _make_server(19101)
    try:
        async with websockets.asyncio.client.connect(
            "ws://127.0.0.1:19101", ping_interval=None
        ) as ws:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert msg["type"] == "system"
            assert msg["data"]["event"] == "stream_connected"
    finally:
        await _cleanup(server)


@pytest.mark.asyncio
async def test_client_receives_emitted_events():
    """Events emitted to the emitter are delivered to connected clients."""
    import websockets.asyncio.client

    emitter = EventEmitter()
    server, _ = await _make_server(19102, emitter=emitter)
    try:
        async with websockets.asyncio.client.connect(
            "ws://127.0.0.1:19102", ping_interval=None
        ) as ws:
            # Consume welcome
            await asyncio.wait_for(ws.recv(), timeout=2.0)

            # Emit a tool call event
            await emitter.emit(HiveEvent(
                type="tool_call", data={"tool": "exec", "ok": True, "duration_ms": 42.5}
            ))

            # Client should receive it
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert msg["type"] == "tool_call"
            assert msg["data"]["tool"] == "exec"
            assert msg["data"]["ok"] is True
    finally:
        await _cleanup(server)


@pytest.mark.asyncio
async def test_multiple_clients_receive_events():
    """Multiple connected clients all receive the same events."""
    import websockets.asyncio.client

    emitter = EventEmitter()
    server, _ = await _make_server(19103, emitter=emitter)
    try:
        async with websockets.asyncio.client.connect(
            "ws://127.0.0.1:19103", ping_interval=None
        ) as ws1:
            async with websockets.asyncio.client.connect(
                "ws://127.0.0.1:19103", ping_interval=None
            ) as ws2:
                # Consume welcome messages
                await asyncio.wait_for(ws1.recv(), timeout=2.0)
                await asyncio.wait_for(ws2.recv(), timeout=2.0)

                # Emit event
                await emitter.emit(HiveEvent(type="llm_call", data={"model": "test"}))

                # Both should receive
                msg1 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
                msg2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
                assert msg1["type"] == "llm_call"
                assert msg2["type"] == "llm_call"
    finally:
        await _cleanup(server)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_required_rejects_without_token():
    """When token is set, clients without correct auth are rejected."""
    import websockets.asyncio.client

    server, _ = await _make_server(19104, token="secret123")
    try:
        async with websockets.asyncio.client.connect(
            "ws://127.0.0.1:19104", ping_interval=None
        ) as ws:
            # Send wrong token
            await ws.send(json.dumps({"type": "auth", "token": "wrong"}))
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert msg["type"] == "error"
    finally:
        await _cleanup(server)


@pytest.mark.asyncio
async def test_auth_required_accepts_correct_token():
    """When token is set, clients with correct token are accepted."""
    import websockets.asyncio.client

    server, _ = await _make_server(19105, token="secret123")
    try:
        async with websockets.asyncio.client.connect(
            "ws://127.0.0.1:19105", ping_interval=None
        ) as ws:
            # Send correct token
            await ws.send(json.dumps({"type": "auth", "token": "secret123"}))

            # Should get auth_ok, then welcome
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert msg["data"]["event"] == "auth_ok"

            msg2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert msg2["type"] == "system"
            assert msg2["data"]["event"] == "stream_connected"
    finally:
        await _cleanup(server)


# ---------------------------------------------------------------------------
# Budget heartbeat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_heartbeat_fires():
    """Budget heartbeat emits events on interval."""
    emitter = EventEmitter()
    server, _ = await _make_server(19106, emitter=emitter, heartbeat_interval=0.2)

    # Mock budget callback
    async def mock_budget():
        return {"daily_usd": 1.5, "daily_limit": 10.0, "pct": 15.0}
    server.set_budget_callback(mock_budget)

    _, queue = emitter.subscribe()  # Direct subscribe to verify heartbeat

    try:
        # Wait for at least one heartbeat
        await asyncio.sleep(0.5)

        # Should have heartbeat events in the queue
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        heartbeats = [e for e in events if e.type == "budget" and e.data.get("event") == "heartbeat"]
        assert len(heartbeats) >= 1
        assert heartbeats[0].data["daily_usd"] == 1.5
    finally:
        await _cleanup(server)


# ---------------------------------------------------------------------------
# StreamConfig
# ---------------------------------------------------------------------------


def test_stream_config_defaults():
    """StreamConfig has sensible defaults."""
    from hive.config.schema import StreamConfig
    cfg = StreamConfig()
    assert cfg.enabled is True
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9100
    assert cfg.token.get_secret_value() == ""


def test_config_includes_stream():
    """Root Config includes stream config."""
    from hive.config.schema import Config
    cfg = Config()
    assert hasattr(cfg, "stream")
    assert cfg.stream.enabled is True
    assert cfg.stream.port == 9100
