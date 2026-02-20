"""Tool registry for dynamic tool management."""

import hashlib
import re
import time
from typing import Any, TYPE_CHECKING

from hive.agent.tools.base import Tool

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
    Registry for agent tools.

    Allows dynamic registration and execution of tools.
    """

    def __init__(self, audit: "AuditLogger | None" = None):
        self._tools: dict[str, Tool] = {}
        self._audit = audit
        self._session_id: str | None = None
    
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
    
    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """
        Execute a tool by name with given parameters.

        Args:
            name: Tool name.
            params: Tool parameters.

        Returns:
            Tool execution result as string.

        Raises:
            KeyError: If tool not found.
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

        t0 = time.monotonic()
        error: str | None = None
        ok = True
        result = ""
        try:
            errors = tool.validate_params(params)
            if errors:
                error = "Invalid parameters: " + "; ".join(errors)
                ok = False
                return f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors)
            result = await tool.execute(**params)
            return result
        except Exception as e:
            ok = False
            error = str(e)
            return f"Error executing {name}: {str(e)}"
        finally:
            if self._audit:
                duration_ms = (time.monotonic() - t0) * 1000
                security = _security_meta(name, params, result) if name in ("docker_exec", "exec") else None
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
    
    @property
    def tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools
