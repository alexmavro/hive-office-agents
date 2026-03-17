"""Worker management tools for the Queen."""
from __future__ import annotations

import asyncio
from typing import Any

from pydantic import Field

from hive.agent.tools.base import Tool
from hive.agent.worker.schema import WorkerOrder, PipelineOrder, WorkerStatus


class SpawnTool(Tool):
    """Spawns a background worker to accomplish a specific task."""
    
    @property
    def name(self) -> str:
        return "spawn"
        
    @property
    def description(self) -> str:
        return (
            "Spawns an isolated background worker to complete a complex or long-running objective. "
            "The worker executes concurrently while you continue talking to the user. "
            "IMPORTANT: You MUST NOT tell the user 'I am doing this myself' — always say "
            "'I am spawning a worker called [name] to handle this.'"
        )
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "worker_name": {
                    "type": "string",
                    "description": "Unique name for the worker (e.g. 'research_agent')",
                },
                "task": {
                    "type": "string",
                    "description": "The objective the worker needs to accomplish. Be extremely detailed.",
                },
                "model": {
                    "type": "string",
                    "description": "Optional LLM string override (e.g. 'gemini-3.1-flash')",
                }
            },
            "required": ["worker_name", "task"],
        }
        
    def __init__(self, worker_registry: Any = None):
        self.worker_registry = worker_registry
        self.channel = "cli"
        self.chat_id = "direct"

    def set_context(self, channel: str, chat_id: str) -> None:
        self.channel = channel
        self.chat_id = chat_id

    async def execute(self, **kwargs: Any) -> str:
        worker_name = kwargs["worker_name"]
        task = kwargs["task"]
        model = kwargs.get("model")
        
        from hive.agent.worker.schema import WorkerOrder
        from hive.agent.worker.loop import WorkerLoop
        
        if not self.worker_registry:
            return "Error: WorkerRegistry is not available in this environment."
            
        def loop_factory() -> WorkerLoop:
            kwargs = self.worker_registry._loop_kwargs
            return WorkerLoop(
                bus=kwargs["bus"],
                provider=kwargs["provider"],
                workspace=kwargs["workspace"],
                model=model or kwargs["model"],
                fallbacks=kwargs.get("fallbacks", []),
                max_iterations=self.worker_registry.config.agents.workers.max_worker_iterations,
                temperature=kwargs["temperature"],
                max_tokens=kwargs["max_tokens"],
                audit=kwargs["audit"],
                daily_usd_budget=kwargs.get("daily_usd_budget", 10.0),
                worker_usd_limit=kwargs.get("worker_usd_limit", 0.50),
            )

        order = WorkerOrder(name=worker_name, task=task, model=model)
        
        # Define the async callback that fires when the worker finishes
        async def on_complete(report):
            from hive.bus.events import InboundMessage
            # We publish a system message back into the DAG so the Queen sees it
            msg = InboundMessage(
                channel="system",
                sender_id="worker_registry",
                chat_id=f"{self.channel}:{self.chat_id}",
                content=f"[WORKER {report.worker_name} COMPLETED]\nStatus: {report.status.value}\nResult:\n{report.output}",
            )
            await self.worker_registry._loop_kwargs["bus"].publish_inbound(msg)

        report = await self.worker_registry.spawn_worker(
            order=order,
            loop_factory=loop_factory,
            on_complete=on_complete
        )
        
        if report.status.value == "failed":
            return f"Failed to spawn worker: {report.error}"
            
        return str(report.output)


class SpawnPipelineTool(Tool):
    """Spawns a sequential pipeline of background workers."""
    
    @property
    def name(self) -> str:
        return "spawn_pipeline"
        
    @property
    def description(self) -> str:
        return (
            "Spawns a sequential pipeline of background workers. The output of worker 1 "
            "will automatically be appended to the task instructions for worker 2, and so on. "
            "Use this for complex, multi-stage workflows (e.g. search -> extract -> draft)."
        )
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pipeline_name": {
                    "type": "string",
                    "description": "Name representing the overall pipeline",
                },
                "tasks": {
                    "type": "array",
                    "description": "A list of objects, each containing: `name` (str), `task` (str), and optional `model` (str)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "task": {"type": "string"},
                            "model": {"type": "string"}
                        },
                        "required": ["name", "task"]
                    }
                }
            },
            "required": ["pipeline_name", "tasks"],
        }
        
    def __init__(self, worker_registry: Any = None):
        self.worker_registry = worker_registry
        self.channel = "cli"
        self.chat_id = "direct"

    def set_context(self, channel: str, chat_id: str) -> None:
        self.channel = channel
        self.chat_id = chat_id

    async def execute(self, **kwargs: Any) -> str:
        pipeline_name = kwargs["pipeline_name"]
        tasks = kwargs["tasks"]
        
        from hive.agent.worker.schema import WorkerOrder
        from hive.agent.worker.loop import WorkerLoop
        
        if not self.worker_registry:
            return "Error: WorkerRegistry is not available in this environment."
            
        if len(tasks) < 2:
            return "Error: A pipeline must have at least 2 tasks."

        def loop_factory(model_override: str | None = None) -> WorkerLoop:
            kwargs = self.worker_registry._loop_kwargs
            return WorkerLoop(
                bus=kwargs["bus"],
                provider=kwargs["provider"],
                workspace=kwargs["workspace"],
                model=model_override or kwargs["model"],
                fallbacks=kwargs.get("fallbacks", []),
                max_iterations=self.worker_registry.config.agents.workers.max_worker_iterations,
                temperature=kwargs["temperature"],
                max_tokens=kwargs["max_tokens"],
                audit=kwargs["audit"],
                daily_usd_budget=kwargs.get("daily_usd_budget", 10.0),
                worker_usd_limit=kwargs.get("worker_usd_limit", 0.50),
            )

        # We don't await the whole pipeline here, we launch a background orchestrator coroutine
        # so the Queen can return to the user immediately.
        async def orchestrate_pipeline():
            from hive.bus.events import InboundMessage

            start_msg = InboundMessage(
                channel="system",
                sender_id="worker_registry",
                chat_id=f"{self.channel}:{self.chat_id}",
                content=f"[PIPELINE '{pipeline_name}' STARTED] Executing {len(tasks)} stages.",
            )
            await self.worker_registry._loop_kwargs["bus"].publish_inbound(start_msg)
            
            previous_output = ""
            for i, task_data in enumerate(tasks):
                name = task_data.get("name", f"{pipeline_name}-stage-{i+1}")
                task_prompt = task_data.get("task", "")
                model = task_data.get("model")
                
                if previous_output:
                    task_prompt += f"\n\n--- OUTPUT FROM PREVIOUS STAGE ---\n{previous_output}"
                    
                order = WorkerOrder(name=name, task=task_prompt, model=model)
                
                # Block until this stage finishes before advancing to the next.
                # spawn_worker_and_wait() awaits the real background task — it never
                # returns PENDING, only COMPLETED / FAILED / CANCELLED.
                report = await self.worker_registry.spawn_worker_and_wait(
                    order=order,
                    loop_factory=lambda m=model: loop_factory(m),
                    on_complete=None,  # Pipeline handles bus messages inline
                )

                if report.status != WorkerStatus.COMPLETED:
                    fail_msg = InboundMessage(
                        channel="system",
                        sender_id="worker_registry",
                        chat_id=f"{self.channel}:{self.chat_id}",
                        content=(
                            f"[PIPELINE '{pipeline_name}' FAILED at stage '{name}']\n"
                            f"Status: {report.status.value}\n"
                            f"Error: {report.error}"
                        ),
                    )
                    await self.worker_registry._loop_kwargs["bus"].publish_inbound(fail_msg)
                    return

                previous_output = str(report.output)
                
            # Pipeline success
            end_msg = InboundMessage(
                channel="system",
                sender_id="worker_registry",
                chat_id=f"{self.channel}:{self.chat_id}",
                content=f"[PIPELINE '{pipeline_name}' COMPLETED ALL STAGES]\nFinal Output:\n{previous_output}",
            )
            await self.worker_registry._loop_kwargs["bus"].publish_inbound(end_msg)

        # Fire and forget the orchestrator
        asyncio.create_task(orchestrate_pipeline(), name=f"pipeline-{pipeline_name}")
        
        return f"Successfully launched background pipeline '{pipeline_name}' with {len(tasks)} stages. I will notify you when it completes."


class WorkersListTool(Tool):
    """Lists currently active background workers."""
    
    @property
    def name(self) -> str:
        return "workers"
        
    @property
    def description(self) -> str:
        return "Lists all currently active or recently completed background workers."
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }
        
    def __init__(self, worker_registry: Any = None):
        self.worker_registry = worker_registry
        
    async def execute(self, **kwargs: Any) -> str:
        if not self.worker_registry:
            return "Error: WorkerRegistry is not available in this environment."
        return str(self.worker_registry.get_status_report())
