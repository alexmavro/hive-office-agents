import asyncio
from typing import Callable, Coroutine, Any

from loguru import logger

from hive.agent.worker.schema import WorkerOrder, WorkerReport, WorkerStatus
from hive.agent.worker.loop import WorkerLoop
from hive.config.schema import Config


class WorkerRegistry:
    """Manages active background workers and enforces concurrency limits."""
    
    def __init__(self, config: Config):
        self.config = config
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._results: dict[str, WorkerReport] = {}
        self._loop_kwargs: dict[str, Any] = {}
        
    def bind_loop_context(self, **kwargs: Any) -> None:
        """Bind the active AgentLoop context (bus, provider, workspace, etc) to be used by loop_factory."""
        self._loop_kwargs = kwargs
        
    @property
    def max_workers(self) -> int:
        return self.config.agents.workers.max_active_workers

    def get_active_count(self) -> int:
        return len(self._active_tasks)

    def is_full(self) -> bool:
        return self.get_active_count() >= self.max_workers

    def get_status_report(self) -> str:
        """Return a formatted string of current worker status for the Queen."""
        if not self._active_tasks and not self._results:
            return "No recent or active workers in the registry."
            
        lines = ["**Active Workers:**"]
        for name in self._active_tasks:
            lines.append(f"- `{name}`: [RUNNING]")
            
        if not self._active_tasks:
            lines.append(" *(none)*")
            
        lines.append("\n**Recent Results:**")
        for name, report in self._results.items():
            lines.append(f"- `{name}`: [{report.status.value.upper()}]")
            
        if not self._results:
            lines.append(" *(none)*")
            
        return "\n".join(lines)

    async def spawn_worker_and_wait(
        self,
        order: WorkerOrder,
        loop_factory: Callable[[], WorkerLoop],
        on_complete: Callable[[WorkerReport], Coroutine[Any, Any, None]] | None = None,
    ) -> WorkerReport:
        """Spawn a worker and block until it fully completes.

        Used by pipeline orchestrators that need to chain outputs sequentially.
        Unlike :meth:`spawn_worker`, this method does not return until the worker
        task has finished (COMPLETED, FAILED, or CANCELLED).

        Args:
            order: The execution instructions for the worker.
            loop_factory: A callable that returns a pre-configured WorkerLoop.
            on_complete: Optional async callback fired when the worker finishes.

        Returns:
            The terminal WorkerReport (status is never PENDING on return).
        """
        # Delegate launch + registration to the existing fire-and-forget API.
        # If spawning is rejected (cap hit, name collision) we get FAILED back immediately.
        pending_report = await self.spawn_worker(order, loop_factory, on_complete)
        if pending_report.status == WorkerStatus.FAILED:
            # Rejected before a background task was ever created — return as-is.
            return pending_report

        # The task was registered. Await it to completion.
        # Use asyncio.shield so that if *our* caller is cancelled the worker
        # still runs to completion and its completion callback still fires.
        task = self._active_tasks.get(order.name)
        if task:
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                # Our awaiter was cancelled, but the shielded task keeps running.
                # Return the best report we have — it may be PENDING if the worker
                # finishes after we return, but that is acceptable for a cancelled pipeline.
                return self._results.get(
                    order.name,
                    WorkerReport(
                        worker_name=order.name,
                        status=WorkerStatus.CANCELLED,
                        error="Pipeline was cancelled while waiting for this stage.",
                        step_summary="Interrupted.",
                    ),
                )

        # By the time we reach here, _run_worker_task has popped the active task
        # and written the final report into _results.
        return self._results.get(
            order.name,
            WorkerReport(
                worker_name=order.name,
                status=WorkerStatus.FAILED,
                error="Worker finished but no result was recorded.",
                step_summary="",
            ),
        )

    async def spawn_worker(
        self,
        order: WorkerOrder,
        loop_factory: Callable[[], WorkerLoop],
        on_complete: Callable[[WorkerReport], Coroutine[Any, Any, None]] | None = None
    ) -> WorkerReport:
        """Spawn a new worker. If max concurrency is reached, this rejects immediately.
        
        Args:
            order: The execution instructions
            loop_factory: A function that returns a pre-configured WorkerLoop
            on_complete: Optional callback fired when the worker finishes
            
        Returns:
            A WorkerReport confirming startup, or a FAILED report if rejected.
        """
        if self.is_full():
            msg = f"WorkerRegistry is full (max {self.max_workers}). Cannot spawn '{order.name}'."
            logger.warning(msg)
            return WorkerReport(
                worker_name=order.name,
                status=WorkerStatus.FAILED,
                error=msg,
                step_summary="Rejected before execution due to concurrency limits."
            )
            
        if order.name in self._active_tasks:
            msg = f"A worker named '{order.name}' is already running."
            logger.warning(msg)
            return WorkerReport(
                worker_name=order.name,
                status=WorkerStatus.FAILED,
                error=msg,
                step_summary="Rejected due to name collision."
            )

        # Clear old result if reusing a name
        self._results.pop(order.name, None)

        loop = loop_factory()
        
        # We need a fresh Session object for the worker.
        # It's an ephemeral DAG branch just for this task.
        from hive.session.manager import SessionManager
        from pathlib import Path
        
        # Temporary in-memory session
        sm = SessionManager(Path("/tmp"))
        session = sm.get_or_create("worker")
        
        task = asyncio.create_task(
            self._run_worker_task(order, loop, session, on_complete),
            name=f"worker-{order.name}"
        )
        self._active_tasks[order.name] = task
        
        logger.info(f"Spawned worker '{order.name}'. Active: {self.get_active_count()}/{self.max_workers}")
        
        return WorkerReport(
            worker_name=order.name,
            status=WorkerStatus.PENDING,
            output=f"Successfully started in background. I will notify you when '{order.name}' completes.",
            step_summary=""
        )

    async def _run_worker_task(
        self,
        order: WorkerOrder,
        loop: WorkerLoop,
        session,
        on_complete: Callable[[WorkerReport], Coroutine[Any, Any, None]] | None
    ):
        """The actual background coroutine that awaits the loop."""
        try:
            report = await loop.execute_order(order, session)
        except asyncio.CancelledError:
            report = WorkerReport(
                worker_name=order.name,
                status=WorkerStatus.CANCELLED,
                error="Worker was forcefully cancelled.",
                step_summary="Execution interrupted."
            )
        except Exception as e:
            logger.exception(f"Worker '{order.name}' unhandled crash")
            report = WorkerReport(
                worker_name=order.name,
                status=WorkerStatus.FAILED,
                error=f"Unhandled crash: {e}",
                step_summary="Internal trace failed."
            )
            
        # Cleanup
        self._active_tasks.pop(order.name, None)
        self._results[order.name] = report
        
        logger.info(f"Worker '{order.name}' finished with status: {report.status.value}")
        
        # Fire callback to notify user/Queen
        if on_complete:
            try:
                await on_complete(report)
            except Exception as e:
                logger.error(f"Failed to run worker completion callback: {e}")

    def cancel_worker(self, name: str) -> bool:
        """Force cancel a running worker."""
        task = self._active_tasks.get(name)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def shutdown_all(self):
        """Cancel all workers and wait for them to finish."""
        for name in list(self._active_tasks.keys()):
            self.cancel_worker(name)
            
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
