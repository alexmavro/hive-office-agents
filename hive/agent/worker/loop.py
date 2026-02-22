"""WorkerLoop — restricted execution engine for background jobs.

This extends AgentLoop but forces strict constraints:
1. Stripped ToolRegistry (no host exec, no message, no spawn).
2. Different termination: instead of stopping silently on max_iterations,
   it synthesizes a WorkerReport.
"""

from typing import Any
import asyncio
import traceback

from pydantic import ValidationError

from hive.agent.loop import AgentLoop
from hive.agent.tools.registry import ToolRegistry
from hive.agent.worker.schema import WorkerOrder, WorkerReport, WorkerStatus
from hive.session.manager import Session


class WorkerLoop(AgentLoop):
    """Restricted execution loop for background workers."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._step_trace: list[str] = []
        
        # Override the ToolRegistry immediately.
        # We strip out ExecTool, SpawnTool, MessageTool, etc.
        restricted_registry = ToolRegistry(
            workspace=self.workspace,
            audit=self._audit,
            session_id=self._session_id
        )
        
        # We must manually re-add only the safe tools that we want to allow.
        # This prevents accidental privilege escalation if new tools are added to base loop.
        safe_tool_names = ["read_file", "write_file", "edit_file", "list_dir", "web_search", "web_fetch", "docker_exec"]
        
        for name in safe_tool_names:
            if name in self.tools:
                # We extract the underlying function/class and register it
                # depending on whether it's an object with an .execute method or just a callable.
                tool_instance = self.tools._tools[name]
                func = getattr(tool_instance, "execute", tool_instance)
                restricted_registry.register(name=name, func=func, schema=tool_instance.schema)
                
        self.tools = restricted_registry

    async def execute_order(self, order: WorkerOrder, session: Session) -> WorkerReport:
        """Execute a WorkerOrder and return a strict WorkerReport."""
        self._session_id = f"worker:{order.name}"
        self.tools._session_id = self._session_id
        
        # Insert the task as a user message
        session.append_message("user", order.task)
        self._step_trace.append(f"**Task Initiated:** {order.task}")

        iterations = 0
        final_output = None
        status = WorkerStatus.RUNNING
        error_msg = None
        token_usage_total = 0
        
        try:
            while iterations < self.max_iterations:
                iterations += 1
                messages = await self._build_messages(session, channel="worker")
                
                # Model swap support from WorkerOrder
                model_to_use = order.model or self.model
                
                response = await self.provider.complete(
                    messages=messages,
                    model=model_to_use,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    tools=[t.schema for t in self.tools._tools.values()],
                    session_id=self._session_id,
                )
                
                if getattr(response, "usage", None):
                    token_usage_total += response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
                
                if response.content:
                    session.append_message("assistant", response.content)
                    # We log the thought process to the trace
                    self._step_trace.append(f"**Thought:** {response.content.strip()[:200]}...")

                if not response.tool_calls:
                    # The worker has concluded its work without calling tools.
                    # We treat its final conversational output as the deliverable.
                    final_output = response.content
                    status = WorkerStatus.COMPLETED
                    break
                    
                # Handle tool calls
                session.append_message(
                    "assistant",
                    "",  # The tool call message itself
                    tool_calls=[tc.model_dump() for tc in response.tool_calls]
                )
                
                for tc in response.tool_calls:
                    self._step_trace.append(f"**Tool Call:** `{tc.name}({tc.arguments})`")
                    result = await self.tools.execute(tc.name, tc.arguments)
                    session.append_message("tool", str(result), name=tc.name, tool_call_id=tc.id)
            
            else:
                # Max iterations hit (While loop else-clause triggers if no break occurred)
                # Graceful degradation (provide_final_answer pattern)
                status = WorkerStatus.FAILED
                error_msg = f"Worker reached maximum iterations ({self.max_iterations})."
                self._step_trace.append(f"**Error:** {error_msg}")
                
                # Do a forced synthesis
                session.append_message("user", "You have run out of time (max loop iterations). You MUST summarize what you've found so far immediately, without using any more tools.")
                messages = await self._build_messages(session, channel="worker")
                synthesis = await self.provider.complete(
                    messages=messages,
                    model=model_to_use,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    session_id=self._session_id,
                )
                
                if synthesis.content:
                    final_output = f"[PARTIAL/TIMEOUT SYNTHESIS]\n{synthesis.content}"
                    
        except Exception as e:
            status = WorkerStatus.FAILED
            error_msg = str(e)
            self._step_trace.append(f"**Exception Crash:** {error_msg}")
            
            # Print full traceback to console/logs for debugging, but we only send string error to DMZ
            if self._audit:
                await self._audit.log_system_event(
                    component="worker_loop",
                    event="crash",
                    details={"error": error_msg, "traceback": traceback.format_exc()}
                )

        return WorkerReport(
            worker_name=order.name,
            status=status,
            output=final_output,
            error=error_msg,
            step_summary="\n".join(self._step_trace),
            token_usage_total=token_usage_total
        )
