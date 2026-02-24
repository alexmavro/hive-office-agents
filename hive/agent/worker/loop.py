"""WorkerLoop — restricted execution engine for background jobs.

This extends AgentLoop but forces strict constraints:
1. Stripped ToolRegistry (no host exec, no message, no spawn).
2. Different termination: instead of stopping silently on max_iterations,
   it synthesizes a WorkerReport.
"""

from typing import Any
import asyncio
import traceback

import json
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
        self._session_id = "worker:init"
        
        # Override the ToolRegistry immediately.
        # We strip out ExecTool, SpawnTool, MessageTool, etc.
        restricted_registry = ToolRegistry(
            workspace=self.workspace,
            audit=self._audit
        )
        
        # We must manually re-add only the safe tools that we want to allow.
        # This prevents accidental privilege escalation if new tools are added to base loop.
        safe_tool_names = ["read_file", "write_file", "edit_file", "list_dir", "web_search", "web_fetch", "docker_exec"]
        
        for name in safe_tool_names:
            if name in self.tools:
                tool_instance = self.tools._tools[name]
                restricted_registry.register(tool_instance)
                
        self.tools = restricted_registry

    async def execute_order(self, order: WorkerOrder, session: Session) -> WorkerReport:
        """Execute a WorkerOrder and return a strict WorkerReport."""
        self._session_id = f"worker:{order.name}"
        self.tools._session_id = self._session_id
        
        # Insert the task as a user message
        session.add_message("user", order.task)
        self._step_trace.append(f"**Task Initiated:** {order.task}")

        iterations = 0
        final_output = None
        status = WorkerStatus.RUNNING
        error_msg = None
        token_usage_total = 0
        
        try:
            # Build initial context with the task
            messages = self.context.build_messages(
                history=session.get_history(max_messages=self.memory_window),
                current_message=None,
                channel="worker",
                chat_id=self._session_id,
            )
            
            while iterations < self.max_iterations:
                iterations += 1
                
                # Model swap support from WorkerOrder
                model_to_use = order.model or self.model
                
                response = await self.provider.chat(
                    messages=messages,
                    model=model_to_use,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    tools=self.tools.get_definitions(),
                )
                
                if getattr(response, "usage", None):
                    token_usage_total += response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
                
                if response.content:
                    session.add_message("assistant", response.content)
                    self._step_trace.append(f"**Thought:** {response.content.strip()[:200]}...")

                if not response.tool_calls:
                    # Concluded without calling tools (final deliverable)
                    final_output = response.content
                    status = WorkerStatus.COMPLETED
                    break
                    
                # We have tools to execute. First, log the assistant message to the context window.
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=getattr(response, "reasoning_content", None)
                )
                
                # Also commit to the persistent DAG session
                session.add_message(
                    "assistant",
                    response.content or "",
                    tools_used=[tc.model_dump() for tc in response.tool_calls]
                )
                
                # Execute tools sequentially
                for tc in response.tool_calls:
                    args_str = json.dumps(tc.arguments, ensure_ascii=False)
                    self._step_trace.append(f"**Tool Call:** `{tc.name}({args_str})`")
                    
                    result = await self.tools.execute(tc.name, tc.arguments)
                    
                    # Update local context window
                    messages = self.context.add_tool_result(
                        messages, tc.id, tc.name, str(result)
                    )
                    # Update persistent session
                    session.add_message("tool", str(result), name=tc.name, tool_call_id=tc.id)
                    
            else:
                # Max iterations hit gracefully
                status = WorkerStatus.FAILED
                error_msg = f"Worker reached maximum iterations ({self.max_iterations})."
                self._step_trace.append(f"**Error:** {error_msg}")
                
                # Forced synthesis
                timeout_msg = "You have run out of time (max loop iterations). You MUST summarize what you've found so far immediately, without using any more tools."
                session.add_message("user", timeout_msg)
                messages.append({"role": "user", "content": timeout_msg})
                
                synthesis = await self.provider.chat(
                    messages=messages,
                    model=model_to_use,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                
                if synthesis.content:
                    final_output = f"[PARTIAL/TIMEOUT SYNTHESIS]\n{synthesis.content}"
                    session.add_message("assistant", final_output)
                    
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
