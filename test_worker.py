import asyncio
from pathlib import Path

from hive.bus.queue import MessageBus
from hive.cli.commands import _make_provider as make_provider
from hive.config.loader import load_config
from hive.agent.loop import AgentLoop
from hive.session.manager import SessionManager
from hive.agent.worker.registry import WorkerRegistry
from hive.bus.events import InboundMessage

async def main():
    print("Starting manual test runtime...")
    config = load_config()
    bus = MessageBus()
    provider = make_provider(config)
    session_manager = SessionManager(config.workspace_path)
    worker_registry = WorkerRegistry(config)
    
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        max_iterations=5,
        temperature=0.7,
        max_tokens=2048,
        session_manager=session_manager,
        worker_registry=worker_registry,
    )
    
    # Send a message manually on the bus.
    msg = InboundMessage(
        channel="cli",
        sender_id="user1",
        chat_id="global",
        content="Please spawn a worker named 'test_worker' to calculate 25 * 25 and write it to current directory test_calc.txt",
        metadata={"channel_role": "admin"}
    )
    
    print("Simulating inbound user message to spawn a worker...")
    await agent.process_direct(msg.content, session_key="user1")
    
    print("Sent! Waiting 15 seconds to observe the worker lifecycle...")
    await asyncio.sleep(15)
    
if __name__ == "__main__":
    asyncio.run(main())
