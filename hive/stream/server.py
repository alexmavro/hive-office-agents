"""WebSocket stream server for real-time hive system observation.

Serves a read-only JSON event stream over WebSocket. Clients connect,
optionally authenticate, and receive HiveEvent objects as JSON lines.

Architecture:
    EventEmitter ──► StreamServer ──► WebSocket clients (fan-out)

Security:
    - Default bind: 127.0.0.1 (localhost only). Remote access via SSH tunnel.
    - Optional bearer token auth: if configured, clients must send
      {"type": "auth", "token": "..."} as their first message.
    - Read-only: all client messages after auth are ignored.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import websockets
from websockets.asyncio.server import serve, ServerConnection
from loguru import logger

from hive.bus.emitter import EventEmitter, HiveEvent


class StreamServer:
    """WebSocket server that streams HiveEvents to connected clients.

    Args:
        emitter: The EventEmitter to subscribe to for system events.
        host: Bind address. Default 127.0.0.1 (localhost only).
        port: Bind port. Default 9100.
        token: Optional auth token. If set, clients must authenticate.
        heartbeat_interval: Seconds between budget heartbeat events.
        ping_interval: Seconds between WebSocket ping frames.
        ping_timeout: Seconds to wait for pong before disconnecting.
    """

    def __init__(
        self,
        emitter: EventEmitter,
        host: str = "127.0.0.1",
        port: int = 9100,
        token: str | None = None,
        heartbeat_interval: float = 30.0,
        ping_interval: float = 15.0,
        ping_timeout: float = 45.0,
    ) -> None:
        self._emitter = emitter
        self._host = host
        self._port = port
        self._token = token
        self._heartbeat_interval = heartbeat_interval
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._server: Any = None
        self._heartbeat_task: asyncio.Task | None = None
        # Budget state callback — set by gateway wiring to fetch live budget.
        self._budget_callback: Any = None

    def set_budget_callback(self, callback: Any) -> None:
        """Set a callback that returns current budget state dict.

        Expected signature: async def callback() -> dict[str, Any]
        Returns: {"daily_usd": float, "daily_limit": float, "pct": float}
        """
        self._budget_callback = callback

    async def start(self) -> None:
        """Start the WebSocket server (non-blocking).

        Binds the server and starts the heartbeat loop. Use serve_forever()
        if you need to block until shutdown (used by gateway).
        """
        self._server = await serve(
            self._handle_client,
            self._host,
            self._port,
            ping_interval=self._ping_interval,
            ping_timeout=self._ping_timeout,
        )
        logger.info(f"[stream] WebSocket server listening on ws://{self._host}:{self._port}")

        # Start budget heartbeat emitter
        self._heartbeat_task = asyncio.create_task(self._budget_heartbeat_loop())

    async def serve_forever(self) -> None:
        """Start server and block until stopped. Used by gateway."""
        await self.start()
        if self._server:
            await self._server.wait_closed()

    async def stop(self) -> None:
        """Gracefully shut down the server."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("[stream] WebSocket server stopped")

    async def _handle_client(self, websocket: ServerConnection) -> None:
        """Handle a single WebSocket client connection.

        Flow:
        1. If token is configured, wait for auth message.
        2. Subscribe to EventEmitter.
        3. Stream events until client disconnects.
        4. Unsubscribe on exit.
        """
        client_addr = websocket.remote_address
        logger.info(f"[stream] Client connected: {client_addr}")

        # --- Auth phase ---
        if self._token:
            try:
                auth_ok = await self._authenticate(websocket)
                if not auth_ok:
                    return
            except Exception:
                logger.debug(f"[stream] Auth failed for {client_addr}")
                return

        # --- Subscribe to events ---
        sub_id, queue = self._emitter.subscribe()

        try:
            # Send welcome event
            welcome = HiveEvent(
                type="system",
                data={"event": "stream_connected", "message": "Hive emission stream active"},
            )
            await websocket.send(json.dumps(welcome.to_dict()))

            # Stream events from the queue
            while True:
                try:
                    # Wait for next event with a timeout so we can check connection health
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                    payload = json.dumps(event.to_dict())
                    await websocket.send(payload)
                except asyncio.TimeoutError:
                    # No events — check if connection is still alive.
                    # websockets v12+ uses .state or raises on send/recv.
                    try:
                        # Cheapest liveness check: attempt to send a zero-length pong
                        # or just check if the transport is closing.
                        if websocket.close_code is not None:
                            logger.info(f"[stream] Client gone: {client_addr}")
                            break
                    except Exception:
                        break
                    continue
                except asyncio.CancelledError:
                    # Server is shutting down
                    break
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"[stream] Client disconnected: {client_addr}")
                    break
                except Exception as exc:
                    logger.debug(f"[stream] Error sending to {client_addr}: {exc}")
                    break
        finally:
            self._emitter.unsubscribe(sub_id)
            logger.debug(f"[stream] Cleaned up subscription for {client_addr}")

    async def _authenticate(self, websocket: ServerConnection) -> bool:
        """Wait for an auth message from the client.

        Expected: {"type": "auth", "token": "<token>"}
        Returns True if authenticated, False if rejected.
        """
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            msg = json.loads(raw)

            if msg.get("type") != "auth" or msg.get("token") != self._token:
                await websocket.send(json.dumps({
                    "type": "error",
                    "data": {"message": "Authentication failed"},
                }))
                await websocket.close(4001, "Authentication failed")
                return False

            await websocket.send(json.dumps({
                "type": "system",
                "data": {"event": "auth_ok", "message": "Authenticated"},
            }))
            return True

        except asyncio.TimeoutError:
            await websocket.close(4002, "Auth timeout")
            return False
        except (json.JSONDecodeError, Exception) as exc:
            logger.debug(f"[stream] Invalid auth message: {exc}")
            await websocket.close(4003, "Invalid auth message")
            return False

    async def _budget_heartbeat_loop(self) -> None:
        """Emit periodic budget heartbeat events.

        If no budget callback is set, emits a minimal heartbeat with just
        a timestamp. If budget callback is available, includes spend data.
        """
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                data: dict[str, Any] = {"event": "heartbeat"}
                if self._budget_callback:
                    try:
                        budget_state = await self._budget_callback()
                        data.update(budget_state)
                    except Exception as exc:
                        data["budget_error"] = str(exc)

                await self._emitter.emit(HiveEvent(type="budget", data=data))

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"[stream] Heartbeat error: {exc}")
