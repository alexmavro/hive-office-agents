from enum import Enum
from pydantic import BaseModel, Field


class WorkerStatus(str, Enum):
    """Status of a background worker."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerOrder(BaseModel):
    """Strict IPC schema for spawning a single background worker."""
    name: str = Field(..., description="A unique identifier for this worker instance (e.g. 'researcher-01')")
    task: str = Field(..., description="The objective the worker needs to accomplish")
    model: str | None = Field(None, description="Optional LLM model override for this specific task (e.g. 'gemini-3.1-flash')")


class PipelineOrder(BaseModel):
    """Strict IPC schema for spawning a sequential chain of background workers.
    
    The final output of index N is automatically appended to the `task` prompt of index N+1.
    """
    pipeline_name: str = Field(..., description="Name representing the overall workflow chain")
    tasks: list[WorkerOrder] = Field(..., min_length=2, description="The sequential tasks to execute")


class WorkerReport(BaseModel):
    """Strict IPC schema representing a worker returning from its loop."""
    worker_name: str
    status: WorkerStatus
    output: str | None = Field(None, description="The final answer or deliverable from the worker")
    error: str | None = Field(None, description="The fatal exception string if the worker crashed")
    step_summary: str = Field(..., description="A condensed markdown trace of all thoughts and tool names the worker executed")
    token_usage_total: int = 0
