"""Audit log retention management.

Moves JSONL files older than `active_days` from the active log directory to an
archive subdirectory, and reports total storage used.

Called at gateway start (non-blocking, async) so old logs are rotated out
without delaying startup.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path


async def run_retention(
    log_dir: Path,
    archive_dir: Path | None = None,
    active_days: int = 30,
) -> int:
    """Move JSONL log files older than `active_days` to `archive_dir`.

    Files are matched by their YYYY-MM-DD.jsonl filename.
    Returns the number of files moved.

    Non-blocking: the actual I/O runs in a thread pool via asyncio.to_thread.
    """
    return await asyncio.to_thread(_run_retention_sync, log_dir, archive_dir, active_days)


def _run_retention_sync(
    log_dir: Path,
    archive_dir: Path | None,
    active_days: int,
) -> int:
    if archive_dir is None:
        archive_dir = log_dir / "archive"

    if not log_dir.exists():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=active_days)
    moved = 0

    for path in sorted(log_dir.glob("*.jsonl")):
        try:
            file_date = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue  # skip files with non-date names

        if file_date < cutoff:
            archive_dir.mkdir(parents=True, exist_ok=True)
            dest = archive_dir / path.name
            path.rename(dest)
            moved += 1

    return moved


def check_size_gb(log_dir: Path, archive_dir: Path | None = None) -> float:
    """Return total size in GB of active log directory and archive combined.

    Scans:
    - Direct *.jsonl files in log_dir (active logs).
    - All files recursively in archive_dir (defaults to log_dir/archive/).
    """
    if archive_dir is None:
        archive_dir = log_dir / "archive"

    total_bytes = 0

    # Active logs — direct children only (subdirectories are not active logs)
    if log_dir.exists():
        for path in log_dir.glob("*.jsonl"):
            if path.is_file():
                total_bytes += path.stat().st_size

    # Archive — everything inside recursively
    if archive_dir.exists():
        for path in archive_dir.rglob("*"):
            if path.is_file():
                total_bytes += path.stat().st_size

    return total_bytes / (1024**3)
