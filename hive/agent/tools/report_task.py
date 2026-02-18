"""report_task tool — Queen signals meaningful events to trigger memory consolidation.

This is the primary mechanism for signal-based learning. When the Queen calls
report_task(), it fires consolidation.consolidate() asynchronously, which writes
to the appropriate part of the memory/ hierarchy.

Usage (from Queen's perspective):
    report_task(status="success", task_type="deploy", summary="Deployed analytics service")
    report_task(status="failure", summary="pip install in container fails on restart", attempts=3)
    report_task(status="correction", summary="VPS IP changed", what_changed="IP was 1.2.3.4, now 5.6.7.8")
    report_task(status="decision", task_type="architecture", summary="Chose JSONL over SQLite")
"""

from typing import Any, Callable, Coroutine

from hive.agent.tools.base import Tool


class ReportTaskTool(Tool):
    """Signal that a meaningful event occurred, triggering memory consolidation."""

    def __init__(self, consolidation_callback: Callable[..., Coroutine] | None = None):
        """
        Args:
            consolidation_callback: Async function called with the event dict.
                                    Signature: async (event: dict) -> None
        """
        self._callback = consolidation_callback

    @property
    def name(self) -> str:
        return "report_task"

    @property
    def description(self) -> str:
        return (
            "Signal that a significant event has occurred. "
            "This triggers memory consolidation — the Queen writes what was learned "
            "to the appropriate memory file so it persists for future sessions.\n\n"
            "Call this when:\n"
            "- A task completes successfully (status='success')\n"
            "- A task fails after multiple attempts (status='failure')\n"
            "- You update your understanding from user feedback (status='correction')\n"
            "- A significant decision is made (status='decision')\n"
            "- A pattern is recognized across multiple successes (status='pattern')\n"
            "- A new skill is created (status='skill_created')\n\n"
            "Not calling this means you don't learn from experience."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["success", "failure", "correction", "decision", "pattern", "skill_created"],
                    "description": "Type of event being reported",
                },
                "summary": {
                    "type": "string",
                    "description": (
                        "What was accomplished, learned, or decided. "
                        "Be specific enough to be useful when found later."
                    ),
                },
                "task_type": {
                    "type": "string",
                    "description": (
                        "Category of task: deploy, debug, research, write, configure, etc. "
                        "Used to route the lesson to the right workflow file."
                    ),
                },
                "attempts": {
                    "type": "integer",
                    "description": "Number of attempts made (important for failure reports).",
                },
                "what_changed": {
                    "type": "string",
                    "description": (
                        "For corrections: what understanding changed. "
                        "Format: 'old understanding → new understanding'"
                    ),
                },
            },
            "required": ["status", "summary"],
        }

    async def execute(self, **kwargs: Any) -> str:
        event = {
            "status": kwargs.get("status"),
            "summary": kwargs.get("summary", ""),
            "task_type": kwargs.get("task_type", "general"),
            "attempts": kwargs.get("attempts", 1),
            "what_changed": kwargs.get("what_changed", ""),
        }

        if self._callback is not None:
            try:
                await self._callback(event)
            except Exception as exc:
                return f"Task reported (consolidation error: {exc})"

        status = event["status"]
        status_labels = {
            "success": "logged as successful workflow",
            "failure": "logged as failure lesson",
            "correction": "correction applied to memory",
            "decision": "decision logged",
            "pattern": "pattern extracted",
            "skill_created": "skill registered",
        }
        label = status_labels.get(status, "logged")
        return f"Acknowledged: {label}. Summary: {event['summary'][:120]}"
