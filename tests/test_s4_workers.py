import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from hive.agent.worker.registry import WorkerRegistry
from hive.agent.worker.loop import WorkerLoop
from hive.agent.worker.schema import WorkerOrder, WorkerStatus
from hive.config.schema import Config


async def _drain_tasks(additional_sleep: float = 0.2) -> None:
    """Yield control to the event loop enough times for fire-and-forget tasks to complete.

    asyncio.create_task() schedules a coroutine but doesn't run it until we
    give up control. A short sleep forces pending tasks to advance. We loop a
    few times to allow tasks that themselves schedule sub-tasks to finish.
    """
    for _ in range(5):
        await asyncio.sleep(0.0)
    if additional_sleep > 0:
        await asyncio.sleep(additional_sleep)

@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    config.agents = MagicMock()
    config.agents.workers = MagicMock()
    config.agents.workers.max_active_workers = 2
    config.agents.workers.max_worker_iterations = 3
    config.agents.defaults = MagicMock()
    config.agents.defaults.model = "test-model"
    config.workspace_path = "/tmp"
    return config

@pytest_asyncio.fixture
async def worker_registry(mock_config):
    registry = WorkerRegistry(mock_config)
    # Bind fake loop context
    registry.bind_loop_context(bus=AsyncMock())
    yield registry
    await registry.shutdown_all()

@pytest.mark.asyncio
async def test_worker_registry_concurrency_limits(worker_registry):
    """Test that the registry correctly caps concurrent workers."""
    
    # Fake loop factory
    async def fake_execute(*args, **kwargs):
        await asyncio.sleep(0.1) # Simulate work
        return MagicMock(status=WorkerStatus.COMPLETED)
        
    def mock_loop_factory():
        loop = MagicMock(spec=WorkerLoop)
        loop.execute_order = AsyncMock(side_effect=fake_execute)
        return loop
        
    order1 = WorkerOrder(name="worker1", task="task 1")
    order2 = WorkerOrder(name="worker2", task="task 2")
    order3 = WorkerOrder(name="worker3", task="task 3")
    
    # Spawn 1
    report1 = await worker_registry.spawn_worker(order1, mock_loop_factory)
    assert report1.status == WorkerStatus.PENDING
    
    # Spawn 2
    report2 = await worker_registry.spawn_worker(order2, mock_loop_factory)
    assert report2.status == WorkerStatus.PENDING
    
    # Spawn 3 - Should fail
    report3 = await worker_registry.spawn_worker(order3, mock_loop_factory)
    assert report3.status == WorkerStatus.FAILED
    assert "full" in report3.error
    
    # Wait for workers to finish
    await asyncio.sleep(0.2)
    
    # Registry should be empty again
    assert worker_registry.get_active_count() == 0

@pytest.mark.asyncio
async def test_worker_registry_name_collision(worker_registry):
    """Test that two workers cannot have the same name."""
    async def fake_execute(*args, **kwargs):
        await asyncio.sleep(0.1)
        return MagicMock()
        
    def mock_loop_factory():
        loop = MagicMock(spec=WorkerLoop)
        loop.execute_order = AsyncMock(side_effect=fake_execute)
        return loop
        
    order = WorkerOrder(name="dupe", task="task")
    await worker_registry.spawn_worker(order, mock_loop_factory)
    
    # Second spawn with same name should fail immediately
    report = await worker_registry.spawn_worker(order, mock_loop_factory)
    assert report.status == WorkerStatus.FAILED
    assert "already running" in report.error

def test_worker_loop_stripped_tools():
    """Test that WorkerLoop strips dangerous tools from its registry."""
    # Create a base AgentLoop fake
    mock_provider = MagicMock()
    mock_bus = MagicMock()
    
    loop = WorkerLoop(
        bus=mock_bus,
        provider=mock_provider,
        workspace=Path("/tmp"),
        model="test-model"
    )
    
    # WorkerLoop should only have safe tools.
    # It specifically should NOT have 'exec', 'spawn', 'message'
    available_tools = list(loop.tools._tools.keys())
    
    # These should be definitely missing
    assert "exec" not in available_tools
    assert "spawn" not in available_tools
    assert "message" not in available_tools
    
    # These should be present
    assert "read_file" in available_tools
    assert "docker_exec" in available_tools


# ---------------------------------------------------------------------------
# New tests for spawn_worker_and_wait and SpawnPipelineTool context fix
# ---------------------------------------------------------------------------


def _make_completing_loop_factory(
    output: str = "done",
    status: WorkerStatus = WorkerStatus.COMPLETED,
    delay: float = 0.05,
) -> callable:
    """Return a loop_factory that produces a WorkerLoop mock completing with given status."""

    def factory():
        from hive.agent.worker.schema import WorkerReport
        loop = MagicMock(spec=WorkerLoop)

        async def _execute(order, session):
            await asyncio.sleep(delay)
            return WorkerReport(
                worker_name=order.name,
                status=status,
                output=output,
                error=None if status == WorkerStatus.COMPLETED else "simulated failure",
                step_summary="**Task Initiated:** test",
            )

        loop.execute_order = AsyncMock(side_effect=_execute)
        return loop

    return factory


@pytest.mark.asyncio
async def test_spawn_and_wait_returns_completed(worker_registry):
    """spawn_worker_and_wait() must block and return a COMPLETED report, never PENDING."""
    order = WorkerOrder(name="stage_a", task="write something")

    report = await worker_registry.spawn_worker_and_wait(
        order=order,
        loop_factory=_make_completing_loop_factory(output="Stage A output"),
    )

    # Critical: status must be terminal — PENDING means the bug is back
    assert report.status == WorkerStatus.COMPLETED, (
        f"Expected COMPLETED but got {report.status.value}. "
        "spawn_worker_and_wait() returned before the worker finished."
    )
    assert report.output == "Stage A output"
    # Worker must have been cleaned up from the active task registry
    assert "stage_a" not in worker_registry._active_tasks


@pytest.mark.asyncio
async def test_spawn_and_wait_propagates_failure(worker_registry):
    """spawn_worker_and_wait() must return FAILED if the worker crashes — not swallow it."""
    order = WorkerOrder(name="crashing_worker", task="crash")

    report = await worker_registry.spawn_worker_and_wait(
        order=order,
        loop_factory=_make_completing_loop_factory(
            output=None, status=WorkerStatus.FAILED, delay=0.05
        ),
    )

    assert report.status == WorkerStatus.FAILED
    assert report.error is not None


@pytest.mark.asyncio
async def test_spawn_and_wait_rejected_returns_failed(worker_registry):
    """When the registry cap is hit, spawn_worker_and_wait() must return FAILED immediately."""
    # Fill the registry to capacity (max_active_workers = 2 in mock_config)
    slow_factory = _make_completing_loop_factory(delay=5.0)
    await worker_registry.spawn_worker(WorkerOrder(name="blocker_1", task="t"), slow_factory)
    await worker_registry.spawn_worker(WorkerOrder(name="blocker_2", task="t"), slow_factory)

    # Next call should be rejected before creating a task
    report = await worker_registry.spawn_worker_and_wait(
        order=WorkerOrder(name="overflow", task="overflow"),
        loop_factory=_make_completing_loop_factory(),
    )

    assert report.status == WorkerStatus.FAILED
    assert "full" in (report.error or "").lower()

    # Cleanup
    await worker_registry.shutdown_all()


@pytest.mark.asyncio
async def test_pipeline_executes_all_stages_and_chains_output():
    """The pipeline orchestrator must run every stage and pass prior output forward.

    This test exercises the full SpawnPipelineTool.execute() path using a real
    WorkerRegistry with mocked WorkerLoops. No LLM is called.
    """
    from unittest.mock import AsyncMock as AM, MagicMock as MM, patch
    from hive.agent.tools.worker_tools import SpawnPipelineTool
    from hive.agent.worker.schema import WorkerReport
    from hive.bus.events import InboundMessage

    # --- Build a minimal WorkerRegistry backed by controlled loop factories ---
    mock_config = MM()
    mock_config.agents.workers.max_active_workers = 5
    mock_config.agents.workers.max_worker_iterations = 3

    registry = WorkerRegistry(mock_config)

    # Track what tasks received (to verify chaining)
    received_tasks: list[str] = []

    def make_factory(reply: str):
        def factory(_model=None):
            loop = MM(spec=WorkerLoop)

            async def _execute(order, session):
                received_tasks.append(order.task)
                return WorkerReport(
                    worker_name=order.name,
                    status=WorkerStatus.COMPLETED,
                    output=reply,
                    error=None,
                    step_summary="",
                )

            loop.execute_order = AM(side_effect=_execute)
            return loop

        return factory

    # Capture bus publishes
    published: list[InboundMessage] = []

    async def fake_publish(msg):
        published.append(msg)

    fake_bus = MM()
    fake_bus.publish_inbound = AM(side_effect=fake_publish)

    registry.bind_loop_context(
        bus=fake_bus,
        provider=MM(),
        workspace=Path("/tmp"),  # Must be a Path — AgentLoop does workspace / "memory"
        model="test-model",
        temperature=0.0,
        max_tokens=512,
        audit=None,
    )

    # Patch spawn_worker_and_wait to use our per-stage factories
    stage_factories = [make_factory("output_stage_1"), make_factory("output_stage_2")]
    stage_idx = {"n": 0}
    original_swaw = registry.spawn_worker_and_wait

    async def routed_swaw(order, loop_factory, on_complete=None):
        idx = stage_idx["n"]
        stage_idx["n"] += 1
        return await original_swaw(order, stage_factories[idx], on_complete)

    # --- Build tool ---
    tool = SpawnPipelineTool(worker_registry=registry)
    tool.set_context("telegram", "12345")

    tasks = [
        {"name": "researcher", "task": "Find information about Rome."},
        {"name": "writer", "task": "Write a summary."},
    ]

    with patch.object(registry, "spawn_worker_and_wait", side_effect=routed_swaw):
        result = await tool.execute(pipeline_name="test_pipeline", tasks=tasks)
        # tool.execute() fires orchestrate_pipeline as a background asyncio.create_task.
        # We need to drain the event loop to let that task run to completion.
        await _drain_tasks(additional_sleep=0.3)

    assert "test_pipeline" in result
    # Pipeline start message must have been published
    start_msgs = [m for m in published if "STARTED" in m.content]
    assert start_msgs, "Pipeline must publish a START message to the bus"

    # Pipeline completion message must have been published
    done_msgs = [m for m in published if "COMPLETED ALL" in m.content]
    assert done_msgs, "Pipeline must publish a COMPLETED ALL STAGES message after finishing"

    # The final output should reference the last stage's output
    final = done_msgs[-1]
    assert "output_stage_2" in final.content


@pytest.mark.asyncio
async def test_pipeline_aborts_on_stage_failure():
    """The pipeline must publish a FAILED message and not run further stages after one fails."""
    from unittest.mock import AsyncMock as AM, MagicMock as MM, patch
    from hive.agent.tools.worker_tools import SpawnPipelineTool
    from hive.agent.worker.schema import WorkerReport
    from hive.bus.events import InboundMessage

    mock_config = MM()
    mock_config.agents.workers.max_active_workers = 5
    mock_config.agents.workers.max_worker_iterations = 3

    registry = WorkerRegistry(mock_config)

    published: list[InboundMessage] = []

    async def fake_publish(msg):
        published.append(msg)

    fake_bus = MM()
    fake_bus.publish_inbound = AM(side_effect=fake_publish)
    registry.bind_loop_context(
        bus=fake_bus, provider=MM(), workspace=Path("/tmp"),  # Path, not str
        model="test-model", temperature=0.0, max_tokens=512, audit=None,
    )

    # First stage FAILS
    async def failing_swaw(order, loop_factory, on_complete=None):
        return WorkerReport(
            worker_name=order.name,
            status=WorkerStatus.FAILED,
            output=None,
            error="Stage 1 crashed",
            step_summary="",
        )

    tool = SpawnPipelineTool(worker_registry=registry)
    tool.set_context("telegram", "12345")

    tasks = [
        {"name": "bad_stage", "task": "fail"},
        {"name": "stage_2_should_not_run", "task": "should not execute"},
    ]

    with patch.object(registry, "spawn_worker_and_wait", side_effect=failing_swaw):
        result = await tool.execute(pipeline_name="fail_pipe", tasks=tasks)
        # Drain the event loop: orchestrate_pipeline runs in a background create_task.
        await _drain_tasks(additional_sleep=0.1)

    # Tool return must acknowledge pipeline launch
    assert "fail_pipe" in result

    # A FAILED message must have been published to the bus
    fail_msgs = [m for m in published if "FAILED" in m.content]
    assert fail_msgs, "Pipeline must publish a FAILED message when a stage fails"
    assert "bad_stage" in fail_msgs[0].content

    # Stage 2 must NOT have been called — only 1 spawn call (for bad_stage)
    all_contents = " ".join(m.content for m in published)
    assert "stage_2_should_not_run" not in all_contents


def test_spawn_pipeline_context_set_before_execute():
    """set_context() must update the channel and chat_id on SpawnPipelineTool."""
    from hive.agent.tools.worker_tools import SpawnPipelineTool

    tool = SpawnPipelineTool(worker_registry=MagicMock())
    # Default values
    assert tool.channel == "cli"
    assert tool.chat_id == "direct"

    tool.set_context("telegram", "abc123")
    assert tool.channel == "telegram"
    assert tool.chat_id == "abc123"

    # Should be overwritable (called every message)
    tool.set_context("discord", "chan_999")
    assert tool.channel == "discord"
    assert tool.chat_id == "chan_999"

