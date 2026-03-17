import asyncio
import pytest
from pathlib import Path

from hive.bus.events import InboundMessage, OutboundMessage

# These E2E tests hit the real Gemini API.
# Run them with: pytest tests/integration/ -m e2e

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_basic_chat(gateway, event_bus):
    """Test 1: The simplest possible flow. Can the Queen receive a message, 
    process it with the real LLM, and send an OutboundMessage back?
    """
    
    # We want a highly constrained prompt so we don't waste tokens and 
    # we get a predictable response we can assert against.
    test_content = (
        "This is an automated E2E test. I need you to prove you are online. "
        "Reply EXACTLY with the phrase 'SYSTEM_ONLINE_ACK' using the message tool. "
        "Do not invoke any other tools. Do not add any conversational padding."
    )
    
    msg = InboundMessage(
        channel="cli", 
        chat_id="test_chat",
        sender_id="user123",
        content=test_content,
        metadata={"channel_role": "admin"}
    )
    
    # Create a future to capture the outbound message emitted by the bus
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    async def capture_outbound(event: OutboundMessage):
        if event.chat_id == "test_chat" and not future.done():
            future.set_result(event)
            
    event_bus.subscribe_outbound("cli", capture_outbound)
    
    # Inject into the system
    await event_bus.publish_inbound(msg)
    
    # Wait for the LLM to process and reply (timeout prevents hanging tests)
    outbound = await asyncio.wait_for(future, timeout=30.0)
    
    assert outbound is not None
    assert "SYSTEM_ONLINE_ACK" in outbound.content


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_gated_execution(gateway, event_bus, tmp_path):
    """Test 2: Prove that the execution gate successfully defers dangerous commands,
    and that the session_approve tool correctly unlocks them on the next turn.
    """
    
    target_file = tmp_path / "workspace" / "secret.txt"
    target_file.write_text("do not delete")
    
    assert target_file.exists()
    
    # We need to simulate a multi-turn conversation
    loop = asyncio.get_running_loop()
    
    # --- TURN 1: Attempt dangerous action ---
    future1 = loop.create_future()
    
    async def capture_turn1(event: OutboundMessage):
        if event.chat_id == "test_gate" and not future1.done():
            future1.set_result(event)
            
    event_bus.subscribe_outbound("cli", capture_turn1)
    
    msg1 = InboundMessage(
        channel="cli", 
        chat_id="test_gate",
        sender_id="user123", 
        # Using a target path outside the workspace (technically we map it, 
        # but let's test a host-level command like bash to guarantee Tier 1)
        content=(
            "This is an automated test. Call the `exec` tool to run: "
            f"rm {target_file}. Do nothing else."
        ),
        metadata={"channel_role": "user"}  # User role ensures no implicit admin bypass
    )
    
    await event_bus.publish_inbound(msg1)
    outbound1 = await asyncio.wait_for(future1, timeout=30.0)
    
    # The gate MUST have blocked this
    assert "approv" in outbound1.content.lower() or "privilege" in outbound1.content.lower()
    assert target_file.exists()  # The file must survive
    
    event_bus._outbound_subscribers.get("cli", []).remove(capture_turn1)
    
    # --- TURN 2: Approve the action ---
    future2 = loop.create_future()
    
    async def capture_turn2(event: OutboundMessage):
        if event.chat_id == "test_gate" and not future2.done():
            future2.set_result(event)
            
    event_bus.subscribe_outbound("cli", capture_turn2)
    
    msg2 = InboundMessage(
        channel="cli", 
        chat_id="test_gate",
        sender_id="user123", 
        content=(
            "Yes, I approve the exec category for this task. "
            "First, call `session_approve` with category='exec' and reason='test'. "
            "Then, call `exec` again to run `rm " + str(target_file) + "`."
        ),
        # Must be admin role to approve
        metadata={"channel_role": "admin"} 
    )
    
    await event_bus.publish_inbound(msg2)
    outbound2 = await asyncio.wait_for(future2, timeout=45.0)  # Takes longer: 2 tool calls
    
    # The file should be gone now
    assert not target_file.exists(), f"File should be deleted by LLM tools"
    
    event_bus._outbound_subscribers.get("cli", []).remove(capture_turn2)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_worker_spawn(gateway, event_bus):
    """Test 3: Autonomy & Delegation. The Queen must be able to spawn a worker 
    and let the worker run independently.
    """
    
    # We instruct the Queen to spawn a worker. We don't care *what* the worker 
    # does as long as it starts executing its sub-loop and returns.
    test_content = (
        "This is an automated E2E test. Call the `spawn` tool to spawn a worker "
        "named 'test_historian' to write a 1-sentence summary of Rome. Do nothing else. "
        "Do not invoke the message tool, only spawn."
    )
    
    msg = InboundMessage(
        channel="cli", 
        chat_id="test_worker",
        sender_id="user123", 
        content=test_content,
        metadata={"channel_role": "admin"}
    )
    
    loop = asyncio.get_running_loop()
    
    # 1. We want to catch the Queen's acknowledgement of spawning.
    future_ack = loop.create_future()
    # 2. We want to catch the worker's completion message injected into the system channel.
    future_worker_done = loop.create_future()
    
    async def capture_events(event):
        if isinstance(event, OutboundMessage):
            # The Queen saying "I spawned it"
            if event.chat_id == "test_worker" and not future_ack.done():
                future_ack.set_result(event)
                
        elif isinstance(event, InboundMessage):
            # The Registry saying "WORKER COMPLETED"
            if event.channel == "system" and "COMPLETED" in event.content and not future_worker_done.done():
                future_worker_done.set_result(event)
                
    event_bus.subscribe_outbound("cli", capture_events)
    # The system messages are actually inbound messages, but MessageBus doesn't have an `inbound_subscribe`.
    # Let's poll for inbound messages instead or rely solely on the outbound ACK.
    # Actually, pipelines and spawned workers send a message on `system` channel via inbound queue.
    # Since we can't subscribe to inbound without stealing them from the AgentLoop, we'll
    # just look at what the WorkerRegistry stored in _results. Wait, the queen also
    # says something back directly. So we can just check if she says she spawned it.
    
    # Inject into the system
    await event_bus.publish_inbound(msg)
    
    # Wait for the Queen to ack the spawn
    outbound_ack = await asyncio.wait_for(future_ack, timeout=30.0)
    assert outbound_ack is not None
    assert "test_historian" in outbound_ack.content or "spawn" in outbound_ack.content.lower()
    
    # Wait for the worker to finish by polling the registry
    worker_finished = False
    for _ in range(60):
        if "test_historian" in gateway.worker_registry._results:
            worker_finished = True
            break
        await asyncio.sleep(1.0)
        
    assert worker_finished, "Worker failed to complete in 60 seconds"
    report = gateway.worker_registry._results["test_historian"]
    assert report.status.value == "completed" or report.output
    
    event_bus._outbound_subscribers.get("cli", []).remove(capture_events)
