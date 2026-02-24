"""SB.1 — Session pre-approval tool.

Lets the user grant Queen category-level autonomy for a session.
Call this ONLY after the user has explicitly approved a category of actions.

Usage flow:
  1. Queen attempts a Tier 1 action → gate returns deferred response
  2. Queen tells the user what she needs and asks for confirmation
  3. User says "yes, proceed with X"
  4. Queen calls session_approve(category="exec", reason="user approved X")
  5. Gate now passes for all Tier 1 actions in that category for this session
  6. Queen retries the original action → succeeds

Valid categories:
  exec     — host shell commands (rm, mv, run scripts, etc.)
  write    — write_file/edit_file outside workspace
  git      — git push, git reset, git checkout --
  packages — pip install, apt install (host-level)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hive.agent.tools.base import Tool

if TYPE_CHECKING:
    from hive.agent.tools.registry import ToolRegistry

_VALID_CATEGORIES = {"exec", "write", "git", "packages"}


class SessionApproveTool(Tool):
    """Grant session-level approval for a category of Tier 1 actions.

    This tool is Tier 2 (always free) — it cannot gate itself.
    Every call is recorded in the audit log.
    """

    def __init__(self, registry: "ToolRegistry") -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        return "session_approve"

    @property
    def description(self) -> str:
        return (
            "Grant approval for a category of Tier 1 (gated) actions. "
            "This approval ONLY lasts for the duration of the current task/plan (until you finish processing this request). "
            "Call this ONLY when the user has explicitly approved a category of actions — "
            "never call it speculatively or to unblock your own requests without user consent. "
            "Valid categories: exec, write, git, packages."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": sorted(_VALID_CATEGORIES),
                    "description": "The action category to pre-approve for this session.",
                },
                "reason": {
                    "type": "string",
                    "description": "What the user said that constitutes approval (for audit trail).",
                },
            },
            "required": ["category", "reason"],
        }

    async def execute(self, category: str, reason: str, **kwargs: Any) -> str:
        role = getattr(self._registry, "_channel_role", "user")
        if role != "admin":
            return "Error: You cannot approve Tier 1 actions because the user in this channel is not an admin."
        
        if category not in _VALID_CATEGORIES:
            return (
                f"Error: '{category}' is not a valid approval category. "
                f"Valid categories: {', '.join(sorted(_VALID_CATEGORIES))}"
            )
        self._registry.pre_approve(category)
        return (
            f"Approval granted for category '{category}'. "
            f"Reason recorded: {reason!r}. "
            f"Tier 1 actions in this category will now proceed without further prompting "
            f"for the remainder of this plan/turn."
        )
