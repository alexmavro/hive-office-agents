"""Tests for hive/audit/ — AuditLogger, sanitization, retention, size check (SA.1)."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from hive.audit import AuditLogger
from hive.audit.retention import check_size_gb, run_retention


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_events(path: Path) -> list[dict]:
    """Parse all non-empty JSONL lines in *path* and return as a list of dicts."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Tool call logging
# ---------------------------------------------------------------------------

class TestLogToolCall:
    async def test_writes_jsonl_structure(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        await logger.log_tool_call(
            actor="queen",
            tool="docker_exec",
            args_summary={"lang": "python", "code": "print('hi')"},
            ok=True,
            duration_ms=123.4,
        )
        files = list(tmp_path.glob("*.jsonl"))
        assert len(files) == 1
        events = read_events(files[0])
        assert len(events) == 1
        ev = events[0]
        assert ev["type"] == "tool_call"
        assert ev["actor"] == "queen"
        assert ev["tool"] == "docker_exec"
        assert ev["ok"] is True
        assert ev["duration_ms"] == 123.4
        assert "ts" in ev
        # sensitive arg must be sanitized
        assert ev["args"]["code"] != "print('hi')"
        assert ev["args"]["lang"] == "python"

    async def test_error_field_present_on_failure(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        await logger.log_tool_call(
            actor="queen",
            tool="bash",
            args_summary={"cmd": "ls"},
            ok=False,
            duration_ms=5.0,
            error="Permission denied",
        )
        ev = read_events(list(tmp_path.glob("*.jsonl"))[0])[0]
        assert ev["ok"] is False
        assert ev["error"] == "Permission denied"

    async def test_no_error_field_on_success(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        await logger.log_tool_call(
            actor="queen", tool="bash", args_summary={}, ok=True, duration_ms=1.0
        )
        ev = read_events(list(tmp_path.glob("*.jsonl"))[0])[0]
        assert "error" not in ev


# ---------------------------------------------------------------------------
# LLM call logging + anomaly detection
# ---------------------------------------------------------------------------

class TestLogLlmCall:
    async def test_writes_jsonl_structure(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        await logger.log_llm_call(
            model="gemini/gemini-exp-1206",
            tokens_in=1000,
            tokens_out=200,
            tool_calls_n=2,
            duration_ms=1500.0,
        )
        ev = read_events(list(tmp_path.glob("*.jsonl"))[0])[0]
        assert ev["type"] == "llm_call"
        assert ev["model"] == "gemini/gemini-exp-1206"
        assert ev["tokens_in"] == 1000
        assert ev["tokens_out"] == 200
        assert ev["tool_calls_n"] == 2
        assert ev["duration_ms"] == 1500.0
        assert "anomalies" not in ev

    async def test_anomaly_tokens_in(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        await logger.log_llm_call("m", tokens_in=60_000, tokens_out=100, tool_calls_n=0, duration_ms=1000)
        ev = read_events(list(tmp_path.glob("*.jsonl"))[0])[0]
        assert "anomalies" in ev
        assert any("tokens_in" in a for a in ev["anomalies"])

    async def test_anomaly_tokens_out(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        await logger.log_llm_call("m", tokens_in=100, tokens_out=15_000, tool_calls_n=0, duration_ms=1000)
        ev = read_events(list(tmp_path.glob("*.jsonl"))[0])[0]
        assert "anomalies" in ev
        assert any("tokens_out" in a for a in ev["anomalies"])

    async def test_anomaly_duration(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        await logger.log_llm_call("m", tokens_in=100, tokens_out=100, tool_calls_n=0, duration_ms=35_000)
        ev = read_events(list(tmp_path.glob("*.jsonl"))[0])[0]
        assert "anomalies" in ev
        assert any("duration_ms" in a for a in ev["anomalies"])

    async def test_no_anomaly_below_thresholds(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        await logger.log_llm_call("m", tokens_in=1000, tokens_out=500, tool_calls_n=1, duration_ms=2000)
        ev = read_events(list(tmp_path.glob("*.jsonl"))[0])[0]
        assert "anomalies" not in ev

    async def test_multiple_anomalies_all_flagged(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)
        await logger.log_llm_call("m", tokens_in=60_000, tokens_out=15_000, tool_calls_n=0, duration_ms=35_000)
        ev = read_events(list(tmp_path.glob("*.jsonl"))[0])[0]
        assert len(ev["anomalies"]) == 3


# ---------------------------------------------------------------------------
# Arg sanitization
# ---------------------------------------------------------------------------

class TestSanitizeArgs:
    def _logger(self, tmp_path: Path) -> AuditLogger:
        return AuditLogger(log_dir=tmp_path)

    def test_sensitive_key_replaced_with_length(self, tmp_path):
        logger = self._logger(tmp_path)
        secret = "import os; os.system('rm -rf /')"
        result = logger._sanitize_args({"code": secret})
        assert result["code"] == f"<{len(secret)} chars>"

    def test_all_sensitive_keys_replaced(self, tmp_path):
        logger = self._logger(tmp_path)
        sensitive = {"code": "x", "content": "y", "text": "z", "body": "w", "message": "v", "prompt": "u"}
        result = logger._sanitize_args(sensitive)
        for key in sensitive:
            assert result[key].startswith("<"), f"{key} was not sanitized"

    def test_long_value_truncated(self, tmp_path):
        logger = self._logger(tmp_path)
        long_val = "a" * 500
        result = logger._sanitize_args({"cmd": long_val})
        assert result["cmd"] == "<500 chars>"

    def test_short_non_sensitive_value_kept(self, tmp_path):
        logger = self._logger(tmp_path)
        result = logger._sanitize_args({"lang": "python", "timeout": 30})
        assert result["lang"] == "python"
        assert result["timeout"] == 30

    def test_non_string_sensitive_value_redacted(self, tmp_path):
        logger = self._logger(tmp_path)
        result = logger._sanitize_args({"code": 12345})
        assert result["code"] == "<redacted>"

    def test_mixed_args_sanitized_correctly(self, tmp_path):
        logger = self._logger(tmp_path)
        result = logger._sanitize_args({
            "code": "secret code",
            "lang": "python",
            "note": "a" * 300,
            "n": 5,
        })
        assert result["code"].startswith("<")
        assert result["lang"] == "python"
        assert result["note"].startswith("<")
        assert result["n"] == 5


# ---------------------------------------------------------------------------
# Daily file rotation
# ---------------------------------------------------------------------------

class TestDailyRotation:
    async def test_different_dates_produce_different_files(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)

        with patch.object(logger, "_today_path", return_value=tmp_path / "2026-01-01.jsonl"):
            await logger.log_system("test_day_one")

        with patch.object(logger, "_today_path", return_value=tmp_path / "2026-01-02.jsonl"):
            await logger.log_system("test_day_two")

        files = sorted(tmp_path.glob("*.jsonl"))
        assert len(files) == 2
        assert files[0].name == "2026-01-01.jsonl"
        assert files[1].name == "2026-01-02.jsonl"

    async def test_same_day_appends_to_one_file(self, tmp_path):
        logger = AuditLogger(log_dir=tmp_path)

        for _ in range(3):
            await logger.log_system("ping")

        files = list(tmp_path.glob("*.jsonl"))
        assert len(files) == 1
        events = read_events(files[0])
        assert len(events) == 3


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------

class TestRetention:
    def _write_fake_jsonl(self, directory: Path, filename: str) -> Path:
        p = directory / filename
        p.write_text('{"type":"test"}\n', encoding="utf-8")
        return p

    async def test_moves_files_older_than_active_days(self, tmp_path):
        log_dir = tmp_path / "audit"
        log_dir.mkdir()
        archive_dir = tmp_path / "archive"

        old_date = (datetime.now(timezone.utc) - timedelta(days=35)).strftime("%Y-%m-%d")
        old_file = self._write_fake_jsonl(log_dir, f"{old_date}.jsonl")

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        recent_file = self._write_fake_jsonl(log_dir, f"{today}.jsonl")

        moved = await run_retention(log_dir, archive_dir, active_days=30)

        assert moved == 1
        assert not old_file.exists()
        assert (archive_dir / old_file.name).exists()
        assert recent_file.exists()

    async def test_keeps_files_within_active_window(self, tmp_path):
        log_dir = tmp_path / "audit"
        log_dir.mkdir()

        recent_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        self._write_fake_jsonl(log_dir, f"{recent_date}.jsonl")

        moved = await run_retention(log_dir, active_days=30)
        assert moved == 0
        assert len(list(log_dir.glob("*.jsonl"))) == 1

    async def test_empty_dir_returns_zero(self, tmp_path):
        log_dir = tmp_path / "empty"
        log_dir.mkdir()
        moved = await run_retention(log_dir, active_days=30)
        assert moved == 0

    async def test_nonexistent_dir_returns_zero(self, tmp_path):
        moved = await run_retention(tmp_path / "nonexistent", active_days=30)
        assert moved == 0


# ---------------------------------------------------------------------------
# Size check
# ---------------------------------------------------------------------------

class TestCheckSizeGb:
    def test_returns_correct_size_for_active_logs(self, tmp_path):
        log_dir = tmp_path / "audit"
        log_dir.mkdir()
        (log_dir / "2026-01-01.jsonl").write_bytes(b"x" * 1024)

        size_gb = check_size_gb(log_dir)
        expected_gb = 1024 / (1024**3)
        assert abs(size_gb - expected_gb) < 1e-9

    def test_includes_archive_directory(self, tmp_path):
        log_dir = tmp_path / "audit"
        log_dir.mkdir()
        archive_dir = log_dir / "archive"
        archive_dir.mkdir()

        (log_dir / "today.jsonl").write_bytes(b"x" * 512)
        (archive_dir / "old.jsonl").write_bytes(b"x" * 512)

        size_gb = check_size_gb(log_dir)
        expected_gb = 1024 / (1024**3)
        assert abs(size_gb - expected_gb) < 1e-9

    def test_empty_dir_returns_zero(self, tmp_path):
        assert check_size_gb(tmp_path / "nonexistent") == 0.0
