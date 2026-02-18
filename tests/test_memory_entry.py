"""Tests for MemoryEntry confidence tracking (S2.3)."""

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from hive.agent.memory import (
    MemoryEntry,
    decay_confidence,
    read_memory_entries,
    write_memory_entry,
)


def make_entry(**kwargs) -> MemoryEntry:
    defaults = dict(
        content="Docker version is 24.0.7",
        confidence="HIGH",
        source="verified_command",
    )
    defaults.update(kwargs)
    return MemoryEntry(**defaults)


class TestWriteAndRead:
    def test_roundtrip_single_entry(self, tmp_path):
        filepath = tmp_path / "test.md"
        entry = make_entry(content="name: Alex", confidence="HIGH", source="user_stated")
        write_memory_entry(filepath, entry)

        entries = read_memory_entries(filepath)
        assert len(entries) == 1
        assert entries[0].content == "name: Alex"
        assert entries[0].confidence == "HIGH"
        assert entries[0].source == "user_stated"

    def test_multiple_entries_in_one_file(self, tmp_path):
        filepath = tmp_path / "test.md"
        write_memory_entry(filepath, make_entry(content="fact one", confidence="HIGH"))
        write_memory_entry(filepath, make_entry(content="fact two", confidence="MEDIUM"))
        write_memory_entry(filepath, make_entry(content="fact three", confidence="LOW"))

        entries = read_memory_entries(filepath)
        assert len(entries) == 3
        assert entries[0].content == "fact one"
        assert entries[1].content == "fact two"
        assert entries[2].content == "fact three"

    def test_preserves_all_fields(self, tmp_path):
        filepath = tmp_path / "test.md"
        now = datetime.now(timezone.utc).isoformat()
        entry = MemoryEntry(
            content="IP address: 10.0.0.1",
            confidence="MEDIUM",
            source="inferred_from_logs",
            timestamp=now,
            last_verified="2026-01-01T00:00:00+00:00",
            needs_reverification=True,
        )
        write_memory_entry(filepath, entry)

        result = read_memory_entries(filepath)[0]
        assert result.content == "IP address: 10.0.0.1"
        assert result.confidence == "MEDIUM"
        assert result.source == "inferred_from_logs"
        assert result.last_verified == "2026-01-01T00:00:00+00:00"
        assert result.needs_reverification is True

    def test_content_with_special_chars(self, tmp_path):
        filepath = tmp_path / "test.md"
        entry = make_entry(content='has "quotes" and: colons')
        write_memory_entry(filepath, entry)

        entries = read_memory_entries(filepath)
        assert entries[0].content == 'has "quotes" and: colons'

    def test_read_nonexistent_file_returns_empty(self, tmp_path):
        filepath = tmp_path / "nonexistent.md"
        assert read_memory_entries(filepath) == []

    def test_creates_parent_directories(self, tmp_path):
        filepath = tmp_path / "deep" / "nested" / "file.md"
        write_memory_entry(filepath, make_entry())
        assert filepath.exists()


class TestConfidenceDecay:
    def _entry_aged(self, days: int, confidence: str = "HIGH") -> MemoryEntry:
        ts = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        return make_entry(confidence=confidence, timestamp=ts)

    def test_high_after_30_days_becomes_medium(self):
        entry = self._entry_aged(31, "HIGH")
        result = decay_confidence(entry)
        assert result.confidence == "MEDIUM"

    def test_high_before_30_days_stays_high(self):
        entry = self._entry_aged(29, "HIGH")
        result = decay_confidence(entry)
        assert result.confidence == "HIGH"

    def test_medium_after_90_days_becomes_low(self):
        entry = self._entry_aged(91, "MEDIUM")
        result = decay_confidence(entry)
        assert result.confidence == "LOW"

    def test_medium_before_90_days_stays_medium(self):
        entry = self._entry_aged(89, "MEDIUM")
        result = decay_confidence(entry)
        assert result.confidence == "MEDIUM"

    def test_low_after_7_days_flags_reverification(self):
        entry = self._entry_aged(8, "LOW")
        result = decay_confidence(entry)
        assert result.needs_reverification is True

    def test_low_before_7_days_no_flag(self):
        entry = self._entry_aged(6, "LOW")
        result = decay_confidence(entry)
        assert result.needs_reverification is False

    def test_fresh_entry_unchanged(self):
        entry = make_entry(confidence="HIGH")
        result = decay_confidence(entry)
        assert result.confidence == "HIGH"
        assert result.needs_reverification is False

    def test_custom_now_parameter(self):
        # Entry is 31 days old relative to a custom "now"
        ts = "2026-01-01T00:00:00+00:00"
        entry = make_entry(confidence="HIGH", timestamp=ts)
        custom_now = datetime(2026, 2, 1, tzinfo=timezone.utc)  # 31 days later
        result = decay_confidence(entry, now=custom_now)
        assert result.confidence == "MEDIUM"

    def test_returns_same_object_if_unchanged(self):
        entry = make_entry(confidence="HIGH")
        result = decay_confidence(entry)
        # Same object returned when nothing changed
        assert result is entry

    def test_invalid_timestamp_returns_unchanged(self):
        entry = make_entry(confidence="HIGH", timestamp="not-a-date")
        result = decay_confidence(entry)
        assert result is entry
