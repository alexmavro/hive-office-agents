import pytest
import asyncio
from pathlib import Path
from hive.agent.circuit_breaker import CircuitBreaker
from hive.agent.budget import BudgetTracker

def test_circuit_breaker_action_loop():
    breaker = CircuitBreaker(max_repeats=3)
    
    # Action 1 - 1st time
    ok, _ = breaker.check_action("search", {"query": "test"})
    assert ok is True
    
    # Action 1 - 2nd time
    ok, _ = breaker.check_action("search", {"query": "test"})
    assert ok is True
    
    # Action 1 - 3rd time (trips breaker)
    ok, reason = breaker.check_action("search", {"query": "test"})
    assert ok is False
    assert "Repeated identical tool call" in reason
    
    # Different action resets
    ok, _ = breaker.check_action("read_file", {"path": "test.txt"})
    assert ok is True

def test_circuit_breaker_error_loop():
    breaker = CircuitBreaker(max_errors=3)
    
    # Error - 1st time
    ok, _ = breaker.check_result("Error: File not found")
    assert ok is True
    
    # Error - 2nd time
    ok, _ = breaker.check_result("Error: File not found")
    assert ok is True
    
    # Error - 3rd time (trips breaker)
    ok, reason = breaker.check_result("Error: File not found")
    assert ok is False
    assert "Received identical error" in reason
    
    # Success resets
    ok, _ = breaker.check_result("Success!")
    assert ok is True
    
    # Different error resets
    ok, _ = breaker.check_result("Error: Permission denied")
    assert ok is True

@pytest.mark.asyncio
async def test_budget_tracker(tmp_path: Path):
    tracker = BudgetTracker(workspace=tmp_path, daily_limit=1.0)
    
    # Add initial cost
    await tracker.add_cost(worker_id="w-1", cost_usd=0.4)
    
    ok, reason = await tracker.check_budget(worker_id="w-1", worker_limit=0.5)
    assert ok is True
    
    # Add cost crossing worker limit but not global limit
    await tracker.add_cost(worker_id="w-1", cost_usd=0.2)
    ok, reason = await tracker.check_budget(worker_id="w-1", worker_limit=0.5)
    assert ok is False
    assert "Worker budget exceeded" in reason
    
    # Add cost crossing global limit
    await tracker.add_cost(worker_id="w-2", cost_usd=0.5)
    ok, reason = await tracker.check_budget(worker_id="w-2", worker_limit=1.0)
    assert ok is False
    assert "Global daily budget exceeded" in reason


# ---------------------------------------------------------------------------
# Gap tests added after S6 audit (2026-02-25)
# Rationale: only 3 tests existed for 2 critical safety systems. The coverage
# below addresses the specific edge cases identified in the builder report.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_tracker_persists_across_instances(tmp_path: Path):
    """BudgetTracker must read from disk on init — costs written by one instance
    must be visible to a second instance using the same workspace path.

    Without this, a gateway restart would silently reset the budget counter.
    """
    tracker_a = BudgetTracker(workspace=tmp_path, daily_limit=1.0)
    await tracker_a.add_cost(worker_id=None, cost_usd=1.10)  # Exceeds the 1.0 daily limit

    # A *new* tracker pointing at the same workspace must see the 1.10 already spent
    tracker_b = BudgetTracker(workspace=tmp_path, daily_limit=1.0)
    ok, reason = await tracker_b.check_budget(worker_id=None, worker_limit=None)
    assert ok is False, (
        "New BudgetTracker did not read persisted state from disk. "
        f"check_budget returned ok=True. Reason: {reason}"
    )
    assert "Global daily budget exceeded" in reason


@pytest.mark.asyncio
async def test_budget_tracker_day_rollover_resets_counter(tmp_path: Path):
    """Costs from yesterday must NOT carry over when a new day begins.

    We simulate this by writing a budget state file dated yesterday and then
    asking a fresh BudgetTracker to check — it must load a clean slate.
    """
    import json
    from datetime import datetime, timezone, timedelta

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    state_file = tmp_path / ".budget_state.json"
    state_file.write_text(
        json.dumps({"date": yesterday, "daily_usd": 9.99, "workers": {"w-old": 9.99}}),
        encoding="utf-8",
    )

    tracker = BudgetTracker(workspace=tmp_path, daily_limit=1.0)
    # Should load clean state because yesterday's date doesn't match today
    ok, reason = await tracker.check_budget(worker_id=None, worker_limit=None)
    assert ok is True, (
        f"Budget tracker did not reset on day rollover. "
        f"Reported spent from yesterday. Reason: {reason}"
    )


@pytest.mark.asyncio
async def test_budget_tracker_concurrent_add_cost_is_safe(tmp_path: Path):
    """Multiple concurrent add_cost calls must not corrupt the total due to
    race conditions. The asyncio.Lock in BudgetTracker must serialize writes.

    This test fires 10 simultaneous coroutines each adding $0.10 — the total
    must be exactly $1.00, not less due to lost updates.
    """
    tracker = BudgetTracker(workspace=tmp_path, daily_limit=100.0)

    # Fire 10 concurrent writes
    await asyncio.gather(*[
        tracker.add_cost(worker_id=None, cost_usd=0.10)
        for _ in range(10)
    ])

    daily, _ = await tracker.get_usage()
    assert abs(daily - 1.00) < 1e-9, (
        f"Concurrent add_cost corrupted the budget total. Expected $1.00, got ${daily:.4f}. "
        "The asyncio.Lock may not be correctly protecting the read-modify-write cycle."
    )


@pytest.mark.asyncio
async def test_budget_gate_trips_at_exact_limit(tmp_path: Path):
    """The gate must trip when daily_usd == daily_limit (>= not just >).

    A status of exactly 1.00 / 1.00 must be rejected.
    """
    tracker = BudgetTracker(workspace=tmp_path, daily_limit=1.0)
    await tracker.add_cost(worker_id=None, cost_usd=1.0)  # Exactly at the limit

    ok, reason = await tracker.check_budget(worker_id=None, worker_limit=None)
    assert ok is False, (
        "Budget gate allowed execution when daily_usd == daily_limit. "
        "The check must use >= (not >) to prevent off-by-epsilon exploitation."
    )
    assert "Global daily budget exceeded" in reason


def test_circuit_breaker_action_count_does_not_bleed_across_tools():
    """Changing tools must reset the repeat counter entirely.

    If tool A is called twice and then tool B is called once, tool B's counter
    should start at 1 — the A-counter must not bleed through.
    """
    breaker = CircuitBreaker(max_repeats=3)

    # Call tool A twice — it's being tracked
    breaker.check_action("tool_a", {"x": 1})
    breaker.check_action("tool_a", {"x": 1})

    # Switch to tool B — different hash, counter must reset to 1
    ok, _ = breaker.check_action("tool_b", {"x": 1})
    assert ok is True

    # Call tool B again — that's 2 repeats, still under max_repeats=3
    ok, _ = breaker.check_action("tool_b", {"x": 1})
    assert ok is True

    # Call tool B a 3rd time — trips now (3 == max_repeats)
    ok, reason = breaker.check_action("tool_b", {"x": 1})
    assert ok is False, (
        "Circuit breaker tripped too early or missed the trip. "
        "Counter from tool_a may have bled into tool_b count."
    )
    assert "Repeated identical tool call" in reason


def test_circuit_breaker_trips_exactly_at_threshold_not_before():
    """The breaker must allow exactly max_repeats - 1 duplicate calls before
    tripping on the Nth. Off-by-one here means either over-blocking or never blocking.
    """
    max_r = 4
    breaker = CircuitBreaker(max_repeats=max_r)

    # Calls 1 through max_r - 1: all OK
    for i in range(max_r - 1):
        ok, reason = breaker.check_action("looping_tool", {"q": "same"})
        assert ok is True, (
            f"Circuit breaker tripped too early on repeat #{i + 1} "
            f"(max_repeats={max_r}). Reason: {reason}"
        )

    # The max_r-th call trips it
    ok, reason = breaker.check_action("looping_tool", {"q": "same"})
    assert ok is False, (
        f"Circuit breaker did not trip on repeat #{max_r} (max_repeats={max_r})."
    )
    assert "Repeated identical tool call" in reason
