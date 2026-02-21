"""Tool registry for dynamic tool management."""

import asyncio
import hashlib
import re
import time
import uuid
from pathlib import Path
from typing import Any, TYPE_CHECKING

from hive.agent.tools.base import Tool
from hive.agent.tools.gate import classify_tool, Tier, GateDecision

if TYPE_CHECKING:
    from hive.audit import AuditLogger

# Patterns present in to_tool_output() and ExecTool output that indicate non-zero exit.
_EXIT_CODE_RE = re.compile(r"Exit code:\s*(-?\d+)")


def _security_meta(name: str, params: dict[str, Any], result: str) -> dict[str, Any] | None:
    """Build security metadata for audit logging.

    Returns a dict with tool-specific security fields, or None if not applicable.
    Always safe to call — never raises.
    """
    meta: dict[str, Any] = {}

    # Exit code + stderr tail — same format for both docker_exec and exec results.
    timed_out = "Execution timed out" in result
    if timed_out:
        meta["timed_out"] = True
        meta["exit_code"] = -1
    else:
        m = _EXIT_CODE_RE.search(result)
        if m:
            meta["exit_code"] = int(m.group(1))
        # exit_code absent = 0 (to_tool_output omits "Exit code:" line on success)

    had_stderr = "STDERR:" in result
    if had_stderr:
        meta["had_stderr"] = True
        stderr_part = result.split("STDERR:\n", 1)[-1]
        # Chop off trailing "Exit code:" line if present
        stderr_clean = stderr_part.split("\nExit code:")[0]
        meta["stderr_tail"] = stderr_clean[-200:].strip()

    # docker_exec-specific: hash + first line of the code blob.
    if name == "docker_exec" and isinstance(params.get("code"), str):
        code = params["code"]
        meta["code_sha256"] = hashlib.sha256(code.encode()).hexdigest()[:16]
        first_line = code.lstrip().splitlines()[0] if code.strip() else ""
        meta["code_first_line"] = first_line[:120]
        meta["code_lines"] = code.count("\n") + 1

    return meta if meta else None


class ToolRegistry:
    """
    Registry for agent tools with SB.1 tiered permission gate.

    Every tool call passes through the gate in execute() before reaching
    the tool implementation. The gate is in code — the LLM cannot reason
    around it.

    Tiers:
      Tier 0 — hard reject, no approval path
      Tier 1 — deferred: requires session pre-approval (pre_approve()) or
                SB.2 admin channel YES (receive_approval())
      Tier 2 — always free, no approval needed

    Session pre-approval (SB.1):
      registry.pre_approve("exec")  →  all Tier 1 exec actions pass for this session
      Granted by the SessionApproveTool after explicit user consent.

    Async approval (SB.2, not yet active):
      registry.receive_approval(approval_id, approved)  →  called by channel handler
      when user sends YES/NO from an admin channel.
    """

    def __init__(
        self,
        audit: "AuditLogger | None" = None,
        workspace: Path | None = None,
        approval_timeout: float = 300.0,
    ) -> None:
        self._tools: dict[str, Tool] = {}
        self._audit = audit
        self._session_id: str | None = None
        self._workspace = workspace
        self._approval_timeout = approval_timeout  # reserved for SB.2

        # SB.1: session-level pre-approved categories
        self._pre_approved: set[str] = set()

        # SB.2: async per-action approval (pre-wired, not active in SB.1)
        self._pending_approvals: dict[str, tuple[asyncio.Event, list[bool]]] = {}

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool by name."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def get_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions in OpenAI format."""
        return [tool.to_schema() for tool in self._tools.values()]

    # ------------------------------------------------------------------
    # Approval API
    # ------------------------------------------------------------------

    def pre_approve(self, category: str) -> None:
        """Grant session-level approval for a Tier 1 action category.

        Called by SessionApproveTool after the user explicitly consents.
        Valid categories: exec, write, git, packages, spawn, script_approval:<hash>:<path>.
        """
        self._pre_approved.add(category)
        
        # SB.4: If this is a script approval, persist the hash permanently.
        if category.startswith("script_approval:"):
            import json
            parts = category.split(":", 2)
            if len(parts) >= 2 and self._workspace:
                script_hash = parts[1]
                system_dir = self._workspace / ".system"
                system_dir.mkdir(parents=True, exist_ok=True)
                approved_json_path = system_dir / "approved_scripts.json"
                
                approved_data = {"approved_hashes": []}
                if approved_json_path.exists():
                    try:
                        approved_data = json.loads(approved_json_path.read_text())
                    except Exception:
                        pass
                        
                if script_hash not in approved_data.get("approved_hashes", []):
                    approved_data.setdefault("approved_hashes", []).append(script_hash)
                    approved_json_path.write_text(json.dumps(approved_data, indent=2))

    async def receive_approval(self, approval_id: str, approved: bool) -> bool:
        """SB.2 hook: resolve a pending per-action approval request.

        Called by the channel handler when the user sends YES or NO from an
        admin channel. Not used in SB.1 (no pending approvals are created yet).

        Returns:
            True if the approval_id was found and resolved.
            False if the approval_id is unknown or already expired.
        """
        if approval_id in self._pending_approvals:
            event, result = self._pending_approvals[approval_id]
            result.append(approved)
            event.set()
            return True
        return False

    # ------------------------------------------------------------------
    # Tool execution (gate lives here)
    # ------------------------------------------------------------------

    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """Execute a tool by name with given parameters.

        The SB.1 gate fires before every execution:
          - Tier 0 → immediate hard reject (no log of attempted execution)
          - Tier 1 → deferred unless category is pre-approved
          - Tier 2 → proceed immediately

        Args:
            name:   Tool name.
            params: Tool parameters.

        Returns:
            Tool execution result as string.
        """
        tool = self._tools.get(name)
        if not tool:
            if self._audit:
                await self._audit.log_tool_call(
                    actor="queen", tool=name, args_summary=params,
                    ok=False, duration_ms=0, error=f"Tool '{name}' not found",
                    session_id=self._session_id,
                )
            return f"Error: Tool '{name}' not found"

        decision: GateDecision | None = None
        t0 = time.monotonic()
        error: str | None = None
        ok = True
        result = ""

        try:
            # --- SB.1 Gate ---
            decision = classify_tool(name, params, self._workspace)

            if decision.tier == Tier.ZERO:
                ok = False
                error = f"Tier 0 blocked: {decision.reason}"
                return (
                    f"Error: This action is absolutely forbidden and has no approval path. "
                    f"Reason: {decision.reason}"
                )

            if decision.tier == Tier.ONE:
                if decision.category not in self._pre_approved:
                    ok = False
                    error = f"Tier 1 deferred: {decision.reason}"
                    return (
                        f"Action requires approval: {decision.reason}\n\n"
                        f"To proceed:\n"
                        f"1. Explain to the user what you need and why.\n"
                        f"2. Ask them to confirm.\n"
                        f"3. Once they say yes, call: "
                        f"session_approve(category='{decision.category}', "
                        f"reason='<what the user said>')\n"
                        f"4. Then retry this action."
                    )
                # Category is pre-approved — fall through to execution

            # Tier 2 or pre-approved Tier 1: validate params and execute
            param_errors = tool.validate_params(params)
            if param_errors:
                ok = False
                error = "Invalid parameters: " + "; ".join(param_errors)
                return f"Error: Invalid parameters for tool '{name}': " + "; ".join(param_errors)

            result = await tool.execute(**params)
            return result

        except Exception as e:
            ok = False
            error = str(e)
            return f"Error executing {name}: {str(e)}"

        finally:
            if self._audit:
                duration_ms = (time.monotonic() - t0) * 1000
                security = (
                    _security_meta(name, params, result)
                    if name in ("docker_exec", "exec")
                    else None
                )
                if decision is not None:
                    gate_meta: dict[str, Any] = {
                        "gate_tier": decision.tier.value,
                        "gate_reason": decision.reason,
                    }
                    if decision.category:
                        gate_meta["gate_category"] = decision.category
                    security = {**(security or {}), **gate_meta}
                await self._audit.log_tool_call(
                    actor="queen",
                    tool=name,
                    args_summary=params,
                    ok=ok,
                    duration_ms=duration_ms,
                    error=error,
                    session_id=self._session_id,
                    security=security,
                )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
