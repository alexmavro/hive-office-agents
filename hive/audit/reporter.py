"""Daily audit report generator.

Reads the JSONL audit log for a given date and produces a Markdown summary
written to ~/.hive/logs/reports/YYYY-MM-DD.md.

Reports cover:
  - Event count summary
  - Tool usage table (call counts, error counts, avg duration)
  - LLM call stats (total tokens, estimated cost, anomaly count)
  - Error / failure list
  - Anomaly details

Called once per day by an asyncio scheduled task in cli/commands.py (SA.3).
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any


# Rough cost estimates (USD per 1M tokens) for common models.
# Used only for ballpark figures in the daily report.
_COST_TABLE: dict[str, tuple[float, float]] = {
    # model_fragment: (input_per_1M, output_per_1M)
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-exp": (0.0, 0.0),          # experimental = free tier
    "gemini": (1.25, 5.00),            # fallback for gemini models
    "claude-opus": (15.0, 75.0),
    "claude-sonnet": (3.0, 15.0),
    "claude-haiku": (0.25, 1.25),
    "gpt-4o": (2.5, 10.0),
    "gpt-4": (10.0, 30.0),
    "gpt-3.5": (0.5, 1.5),
    "deepseek": (0.27, 1.10),
    "openrouter": (1.0, 1.0),          # generic fallback
}


def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Return a rough USD cost estimate for one LLM call."""
    model_lower = model.lower()
    for fragment, (in_rate, out_rate) in _COST_TABLE.items():
        if fragment in model_lower:
            return (tokens_in * in_rate + tokens_out * out_rate) / 1_000_000
    # Unknown model — no estimate
    return 0.0


def _load_events(log_path: Path) -> list[dict[str, Any]]:
    """Read all valid JSON events from a JSONL file."""
    if not log_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def generate_daily_report(
    report_date: date | None = None,
    log_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> str:
    """Generate a Markdown daily audit report and write it to disk.

    Args:
        report_date: UTC date to report on. Defaults to yesterday.
        log_dir: Directory containing YYYY-MM-DD.jsonl files.
                 Defaults to ~/.hive/logs/audit/.
        reports_dir: Output directory for .md files.
                     Defaults to ~/.hive/logs/reports/.

    Returns:
        The absolute path of the written report file as a string.
    """
    if report_date is None:
        report_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    if log_dir is None:
        log_dir = Path.home() / ".hive" / "logs" / "audit"
    if reports_dir is None:
        reports_dir = Path.home() / ".hive" / "logs" / "reports"

    date_str = report_date.strftime("%Y-%m-%d")
    log_path = log_dir / f"{date_str}.jsonl"
    events = _load_events(log_path)

    md = _build_report(date_str, events)

    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"{date_str}.md"
    out_path.write_text(md, encoding="utf-8")
    return str(out_path)


def _build_report(date_str: str, events: list[dict[str, Any]]) -> str:
    """Build the Markdown report string from a list of events."""
    lines: list[str] = []

    lines.append(f"# Hive Audit Report — {date_str}")
    lines.append("")
    lines.append(
        "_System-event log only. Does not contain personal data. "
        "See STATUS.md SA section for future reworks before public deployment._"
    )
    lines.append("")

    if not events:
        lines.append("No events recorded for this date.")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # 1. Summary counts                                                    #
    # ------------------------------------------------------------------ #
    type_counts: dict[str, int] = defaultdict(int)
    for ev in events:
        type_counts[ev.get("type", "unknown")] += 1

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Event type | Count |")
    lines.append(f"|---|---|")
    for etype, count in sorted(type_counts.items()):
        lines.append(f"| {etype} | {count} |")
    lines.append("")

    # ------------------------------------------------------------------ #
    # 2. Tool usage                                                        #
    # ------------------------------------------------------------------ #
    tool_events = [e for e in events if e.get("type") == "tool_call"]
    if tool_events:
        tool_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "errors": 0, "total_ms": 0.0}
        )
        for ev in tool_events:
            name = ev.get("tool", "unknown")
            tool_stats[name]["calls"] += 1
            if not ev.get("ok", True):
                tool_stats[name]["errors"] += 1
            tool_stats[name]["total_ms"] += ev.get("duration_ms", 0.0)

        lines.append("## Tool Usage")
        lines.append("")
        lines.append("| Tool | Calls | Errors | Avg duration (ms) |")
        lines.append("|---|---|---|---|")
        for tool_name, stats in sorted(tool_stats.items()):
            avg = stats["total_ms"] / stats["calls"] if stats["calls"] else 0
            lines.append(
                f"| {tool_name} | {stats['calls']} | {stats['errors']} | {avg:.0f} |"
            )
        lines.append("")

    # ------------------------------------------------------------------ #
    # 3. LLM call stats                                                   #
    # ------------------------------------------------------------------ #
    llm_events = [e for e in events if e.get("type") == "llm_call"]
    if llm_events:
        total_in = sum(e.get("tokens_in", 0) for e in llm_events)
        total_out = sum(e.get("tokens_out", 0) for e in llm_events)
        total_ms = sum(e.get("duration_ms", 0.0) for e in llm_events)
        anomaly_count = sum(1 for e in llm_events if e.get("anomalies"))
        models_seen = {e.get("model", "unknown") for e in llm_events}

        # Cost estimate — use first model found for simplicity
        first_model = next(iter(models_seen), "unknown")
        est_cost = _estimate_cost(first_model, total_in, total_out)

        lines.append("## LLM Calls")
        lines.append("")
        lines.append(f"- **Calls:** {len(llm_events)}")
        lines.append(f"- **Models:** {', '.join(sorted(models_seen))}")
        lines.append(f"- **Total tokens in:** {total_in:,}")
        lines.append(f"- **Total tokens out:** {total_out:,}")
        lines.append(f"- **Total duration:** {total_ms / 1000:.1f}s")
        if est_cost > 0:
            lines.append(f"- **Estimated cost:** ${est_cost:.4f} USD _(rough estimate only)_")
        if anomaly_count:
            lines.append(f"- **Anomalies flagged:** {anomaly_count}")
        lines.append("")

    # ------------------------------------------------------------------ #
    # 4. Errors / failures                                                 #
    # ------------------------------------------------------------------ #
    failures = [e for e in tool_events if not e.get("ok", True)]
    if failures:
        lines.append("## Errors & Failures")
        lines.append("")
        for ev in failures[:20]:  # cap at 20 to keep report readable
            ts = ev.get("ts", "?")[:19]
            tool = ev.get("tool", "?")
            err = ev.get("error", "no details")[:200]
            lines.append(f"- `{ts}` **{tool}**: {err}")
        if len(failures) > 20:
            lines.append(f"- _...and {len(failures) - 20} more_")
        lines.append("")

    # ------------------------------------------------------------------ #
    # 5. Anomalies                                                         #
    # ------------------------------------------------------------------ #
    anomalies = [e for e in llm_events if e.get("anomalies")]
    if anomalies:
        lines.append("## LLM Anomalies")
        lines.append("")
        for ev in anomalies[:10]:
            ts = ev.get("ts", "?")[:19]
            model = ev.get("model", "?")
            flags = ", ".join(ev.get("anomalies", []))
            tin = ev.get("tokens_in", 0)
            tout = ev.get("tokens_out", 0)
            lines.append(
                f"- `{ts}` {model} — **{flags}** "
                f"(tokens_in={tin:,}, tokens_out={tout:,})"
            )
        if len(anomalies) > 10:
            lines.append(f"- _...and {len(anomalies) - 10} more_")
        lines.append("")

    lines.append("---")
    lines.append(f"_Generated by Hive audit layer · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_")

    return "\n".join(lines)
