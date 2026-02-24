import asyncio
import json
import shutil
from pathlib import Path

import pytest
import pytest_asyncio
from hive.config.loader import load_config
from hive.bus.queue import MessageBus
from hive.providers.litellm_provider import LiteLLMProvider
from hive.agent.loop import AgentLoop
from hive.agent.worker.registry import WorkerRegistry
from hive.session.manager import SessionManager


# Add a custom marker for e2e tests
def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end integration test running a real LLM")


@pytest_asyncio.fixture(scope="function")
async def e2e_workspace(tmp_path: Path):
    """Creates an ephemeral workspace and config for E2E tests."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    
    # We need to copy the base templates so the memory hierarchy works
    templates_dir = Path("/root/queen-alpha/templates/memory")
    if templates_dir.exists():
        shutil.copytree(templates_dir, ws / "memory")
        
    config_file = tmp_path / "config.json"
    
    # Read the real system config to grab the API key for testing
    real_config_path = Path.home() / ".hive" / "config.json"
    api_key = "dummy_key"
    if real_config_path.exists():
        try:
            real_data = json.loads(real_config_path.read_text())
            api_key = real_data.get("providers", {}).get("gemini", {}).get("apiKey", "dummy_key")
        except Exception:
            pass
            
    # Create a minimal config using the fast Flash model for testing to save costs/time
    config_data = {
        "providers": {
            "gemini": {"apiKey": api_key}
        },
        "agents": {
            "defaults": {
                "model": "gemini/gemini-2.5-flash", 
                "maxTokens": 8192,
                "temperature": 0.0
            }
        },
        "gateway": {
            "host": "127.0.0.1",
            "port": 18799  # Run on a different port to avoid conflicts
        }
    }
    
    config_file.write_text(json.dumps(config_data))
    
    yield tmp_path, ws, config_file
    
    # Teardown: no explicit cleanup needed, tmp_path handles it


@pytest_asyncio.fixture(scope="function")
async def gateway(e2e_workspace):
    """Yields a fully booted HiveGateway instance."""
    tmp_path, ws, config_file = e2e_workspace
    
    # Override the config path logic for testing by temporarily 
    # setting a module-level variable or manipulating the environment
    import os
    original_home = os.environ.get("HOME")
    
    # Create an object to hold our test gateway components
    class TestGateway:
        pass
        
    gw = TestGateway()
    gw.config = None
    gw.bus = MessageBus()
    gw.loop = None
    gw.worker_registry = None

    try:
        # The gateway loads from ~/.hive/config.json, so we point HOME to tmp_path
        os.environ["HOME"] = str(tmp_path)
        
        # We need to move the config file into the right place
        hive_dir = tmp_path / ".hive"
        hive_dir.mkdir()
        shutil.copy(config_file, hive_dir / "config.json")
        
        gw.config = load_config()
        gw.config.agents.defaults.workspace = str(ws)
        
        from hive.cli.commands import _make_provider
        provider = _make_provider(gw.config)
        
        gw.worker_registry = WorkerRegistry(gw.config)
        sm = SessionManager(gw.config.workspace_path)
        
        gw.loop = AgentLoop(
            bus=gw.bus,
            provider=provider,
            workspace=gw.config.workspace_path,
            model=gw.config.agents.defaults.model,
            fallbacks=gw.config.agents.defaults.fallbacks,
            temperature=gw.config.agents.defaults.temperature,
            max_tokens=gw.config.agents.defaults.max_tokens,
            max_iterations=gw.config.agents.defaults.max_tool_iterations,
            memory_window=gw.config.agents.defaults.memory_window,
            brave_api_key=gw.config.tools.web.search.api_key.get_secret_value() if gw.config.tools.web.search.api_key else None,
            exec_config=gw.config.tools.exec,
            restrict_to_workspace=gw.config.tools.restrict_to_workspace,
            session_manager=sm,
            mcp_servers=gw.config.tools.mcp_servers,
            audit=None,
            worker_registry=gw.worker_registry,
        )
        
        # Start core services
        dispatch_task = asyncio.create_task(gw.bus.dispatch_outbound())
        
        # Start the loop in the background
        loop_task = asyncio.create_task(gw.loop.run())
        
        yield gw
        
        # Teardown
        gw.bus.stop()
        loop_task.cancel()
        dispatch_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass
        try:
            await dispatch_task
        except asyncio.CancelledError:
            pass
        
    finally:
        if original_home:
            os.environ["HOME"] = original_home
        else:
            del os.environ["HOME"]


@pytest_asyncio.fixture(scope="function")
async def event_bus(gateway):
    """Provides direct access to the gateway's event bus for injection/assertion."""
    return gateway.bus
