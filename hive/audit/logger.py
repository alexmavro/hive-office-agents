"""Structured JSONL audit logger for the Hive system.

Writes system events to ~/.hive/logs/audit/YYYY-MM-DD.jsonl (one JSON line per event).
Async-safe via asyncio.Lock; file I/O is offloaded with asyncio.to_thread.

IMPORTANT: This is system-event logging only — NOT personal data logging.
See plan SA and STATUS.md for future reworks required before any public deployment.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SENSITIVE_KEYS = frozenset({"code", "content", "text", "body", "message", "prompt"})
_MAX_STRING_LEN = 200

# Anomaly thresholds
_ANOMALY_TOKENS_IN = 50_000
_ANOMALY_TOKENS_OUT = 10_000
_ANOMALY_DURATION_MS = 30_000


class AuditLogger:
    """Async-safe JSONL audit logger.

    Creates one file per UTC day at <log_dir>/YYYY-MM-DD.jsonl.
    All public methods are async and safe to call from any coroutine.
    """

    def __init__(self, log_dir: Path | None = None) -> None:
        if log_dir is None:
            log_dir = Path.home() / ".hive" / "logs" / "audit"
        self._log_dir = Path(log_dir)
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _today_path(self) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._log_dir / f"{date_str}.jsonl"

    def _sanitize_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """Return a sanitized copy of an args dict.

        - Keys in _SENSITIVE_KEYS have their values replaced with "<N chars>".
        - String values longer than _MAX_STRING_LEN are replaced with "<N chars>".
        - All other values are kept as-is.
        """
        result: dict[str, Any] = {}
        for key, value in args.items():
            if key in _SENSITIVE_KEYS:
                if isinstance(value, str):
                    result[key] = f"<{len(value)} chars>"
                else:
                    result[key] = "<redacted>"
            elif isinstance(value, str) and len(value) > _MAX_STRING_LEN:
                result[key] = f"<{len(value)} chars>"
            else:
                result[key] = value
        return result

    async def _write(self, event: dict[str, Any]) -> None:
        """Append one JSON line to today's log file."""
        event.setdefault("ts", datetime.now(timezone.utc).isoformat())
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        async with self._lock:
            await asyncio.to_thread(self._append_line, line)

    def _append_line(self, line: str) -> None:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        with self._today_path().open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # ------------------------------------------------------------------
    # Public logging methods
    # ------------------------------------------------------------------

    async def log_tool_call(
        self,
        actor: str,
        tool: str,
        args_summary: dict[str, Any],
        ok: bool,
        duration_ms: float,
        error: str | None = None,
    ) -> None:
        """Log a tool execution event.

        Args:
            actor: who triggered the call (e.g. "queen", "worker-1").
            tool: tool name (e.g. "docker_exec", "bash").
            args_summary: raw args dict — will be sanitized before writing.
            ok: True if the tool succeeded.
            duration_ms: wall-clock duration in milliseconds.
            error: short error message on failure (truncated to 500 chars).
        """
        event: dict[str, Any] = {
            "type": "tool_call",
            "actor": actor,
            "tool": tool,
            "args": self._sanitize_args(args_summary),
            "ok": ok,
            "duration_ms": round(duration_ms, 1),
        }
        if error is not None:
            event["error"] = str(error)[:500]
        await self._write(event)

    async def log_llm_call(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        tool_calls_n: int,
        duration_ms: float,
    ) -> None:
        """Log an LLM inference event with token counts and anomaly detection."""
        anomalies: list[str] = []
        if tokens_in > _ANOMALY_TOKENS_IN:
            anomalies.append(f"tokens_in>{_ANOMALY_TOKENS_IN}")
        if tokens_out > _ANOMALY_TOKENS_OUT:
            anomalies.append(f"tokens_out>{_ANOMALY_TOKENS_OUT}")
        if duration_ms > _ANOMALY_DURATION_MS:
            anomalies.append(f"duration_ms>{_ANOMALY_DURATION_MS}")

        event: dict[str, Any] = {
            "type": "llm_call",
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tool_calls_n": tool_calls_n,
            "duration_ms": round(duration_ms, 1),
        }
        if anomalies:
            event["anomalies"] = anomalies
        await self._write(event)

    async def log_channel_event(
        self,
        direction: str,
        channel: str,
        session_id: str,
        content_length: int,
    ) -> None:
        """Log an inbound or outbound channel message (metadata only, no content).

        Args:
            direction: "in" (received) or "out" (sent).
            channel: channel name (e.g. "telegram", "whatsapp", "cli").
            session_id: opaque session identifier.
            content_length: byte length of the message content — not the content itself.
        """
        await self._write({
            "type": "channel_event",
            "direction": direction,
            "channel": channel,
            "session_id": session_id,
            "content_length": content_length,
        })

    async def log_system(self, event: str, **kwargs: Any) -> None:
        """Log a gateway lifecycle event (start, stop, config change, etc.)."""
        await self._write({"type": "system", "event": event, **kwargs})

    async def log_worker(
        self,
        worker_id: str,
        name: str,
        event: str,
        **kwargs: Any,
    ) -> None:
        """Log a worker lifecycle event.

        Stub for S4 — worker spawn/complete/fail/timeout events will call this.
        """
        await self._write({
            "type": "worker",
            "worker_id": worker_id,
            "name": name,
            "event": event,
            **kwargs,
        })
