"""Budget tracking and enforcement."""
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger

class BudgetTracker:
    def __init__(self, workspace: Path, daily_limit: float = 10.0):
        self.workspace = workspace
        self.daily_limit = daily_limit
        self.state_file = self.workspace / ".budget_state.json"
        self._lock = asyncio.Lock()
        
    async def add_cost(self, worker_id: str | None, cost_usd: float) -> None:
        """Add cost synchronously to the budget state."""
        if cost_usd <= 0:
            return
            
        async with self._lock:
            state = await asyncio.to_thread(self._load_state)
            state["daily_usd"] += cost_usd
            if worker_id:
                state["workers"][worker_id] = state["workers"].get(worker_id, 0.0) + cost_usd
            await asyncio.to_thread(self._save_state, state)
            
    async def get_usage(self, worker_id: str | None = None) -> tuple[float, float | None]:
        """Get (daily_usd, worker_usd) usage."""
        async with self._lock:
            state = await asyncio.to_thread(self._load_state)
        w_usd = state["workers"].get(worker_id, 0.0) if worker_id else None
        return state["daily_usd"], w_usd

    async def check_budget(self, worker_id: str | None, worker_limit: float | None = None) -> tuple[bool, str]:
        """Check if we are within budget. Returns (is_ok, reason)."""
        async with self._lock:
            state = await asyncio.to_thread(self._load_state)
            
        if state["daily_usd"] >= self.daily_limit:
            return False, f"Global daily budget exceeded (${state['daily_usd']:.2f} / ${self.daily_limit:.2f})"
            
        if worker_id and worker_limit is not None:
            worker_spent = state["workers"].get(worker_id, 0.0)
            if worker_spent >= worker_limit:
                return False, f"Worker budget exceeded (${worker_spent:.2f} / ${worker_limit:.2f})"
                
        return True, ""
        
    def _load_state(self) -> dict:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        default_state = {"date": today, "daily_usd": 0.0, "workers": {}}
        
        if not self.state_file.exists():
            return default_state
            
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
            if state.get("date") != today:
                # Reset for new day
                return default_state
            return state
        except Exception:
            return default_state
            
    def _save_state(self, state: dict) -> None:
        try:
            self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save budget state: {e}")
