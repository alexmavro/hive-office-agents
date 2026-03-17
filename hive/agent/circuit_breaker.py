"""Circuit breaker for detecting infinite loops and repetitive failures."""
from typing import Any
import hashlib
import json

class CircuitBreaker:
    def __init__(self, max_repeats: int = 3, max_errors: int = 3):
        self.max_repeats = max_repeats
        self.max_errors = max_errors
        
        # State tracking
        self._last_action_hash: str | None = None
        self._action_repeat_count: int = 0
        
        self._last_error_hash: str | None = None
        self._error_repeat_count: int = 0

    def check_action(self, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Check if an action is repeating infinitely. Returns (is_ok, reason)."""
        action_payload = json.dumps({"name": tool_name, "args": arguments}, sort_keys=True)
        action_hash = hashlib.sha256(action_payload.encode()).hexdigest()
        
        if self._last_action_hash == action_hash:
            self._action_repeat_count += 1
            if self._action_repeat_count >= self.max_repeats:
                return False, f"Circuit breaker tripped: Repeated identical tool call `{tool_name}` {self.max_repeats} times."
        else:
            self._last_action_hash = action_hash
            self._action_repeat_count = 1
            
        return True, ""

    def check_result(self, result: str) -> tuple[bool, str]:
        """Check if identical errors are repeating. Returns (is_ok, reason)."""
        # Only consider results that look like errors (case-insensitive)
        result_str = str(result)
        if not result_str.lower().startswith("error"):
            self._last_error_hash = None
            self._error_repeat_count = 0
            return True, ""
            
        error_hash = hashlib.sha256(result_str.encode()).hexdigest()
        if self._last_error_hash == error_hash:
            self._error_repeat_count += 1
            if self._error_repeat_count >= self.max_errors:
                return False, f"Circuit breaker tripped: Received identical error {self.max_errors} times sequentially."
        else:
            self._last_error_hash = error_hash
            self._error_repeat_count = 1
            
        return True, ""
