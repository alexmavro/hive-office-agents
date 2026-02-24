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
