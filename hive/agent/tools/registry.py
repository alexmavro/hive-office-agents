"""Tool registry for dynamic tool management."""

import time
from typing import Any, TYPE_CHECKING

from hive.agent.tools.base import Tool

if TYPE_CHECKING:
    from hive.audit import AuditLogger


class ToolRegistry:
    """
    Registry for agent tools.

    Allows dynamic registration and execution of tools.
    """

    def __init__(self, audit: "AuditLogger | None" = None):
        self._tools: dict[str, Tool] = {}
        self._audit = audit
    
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
                )
            return f"Error: Tool '{name}' not found"

        t0 = time.monotonic()
        error: str | None = None
        ok = True
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
                await self._audit.log_tool_call(
                    actor="queen",
                    tool=name,
                    args_summary=params,
                    ok=ok,
                    duration_ms=duration_ms,
                    error=error,
                )
    
    @property
    def tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools
