import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock

from hive.agent.worker.registry import WorkerRegistry
from hive.agent.worker.loop import WorkerLoop
from hive.agent.worker.schema import WorkerOrder, WorkerStatus
from hive.config.schema import Config
from pathlib import Path

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
