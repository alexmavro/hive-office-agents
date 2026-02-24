import asyncio
import pytest
from pathlib import Path
import json

from hive.bus.events import InboundMessage, OutboundMessage

# Run with: pytest tests/integration/test_e2e_safety.py -m e2e

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_circuit_breaker_trips(gateway, event_bus):
    """Test that the agent circuit breaker trips and halts execution when the LLM
    gets stuck in an infinite loop calling the exact same tool repeatedly.
    """
    # Instruct the LLM to get stuck in a loop
    test_content = (
        "This is an automated test. I need you to prove the circuit breaker works. "
        "Call the `list_dir` tool on the current directory repeatedly without ever stopping. "
        "Do not synthesize a final answer, just keep calling the tool forever."
    )
    
    msg = InboundMessage(
        channel="cli", 
        chat_id="test_breaker",
        sender_id="user123",
        content=test_content,
        metadata={"channel_role": "admin"}
    )
    
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    async def capture_outbound(event: OutboundMessage):
        if event.chat_id == "test_breaker" and not future.done():
            # We are looking for the circuit breaker halt string
            if "CIRCUIT BREAKER" in event.content:
                future.set_result(event)
            
    event_bus.subscribe_outbound("cli", capture_outbound)
    
    await event_bus.publish_inbound(msg)
    
    # Wait for the LLM to loop enough times to trip the breaker (N=3)
    try:
        outbound = await asyncio.wait_for(future, timeout=45.0)
        assert outbound is not None
        assert "CIRCUIT BREAKER" in outbound.content
        assert "Repeated identical tool call" in outbound.content
    finally:
        if capture_outbound in event_bus._outbound_subscribers.get("cli", []):
            event_bus._outbound_subscribers["cli"].remove(capture_outbound)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_budget_gate_trips(gateway, event_bus, monkeypatch):
    """Test that the agent budget gate trips and halts execution when the 
    global USD limits are exceeded.
    """
    
    # Force the gateway's budget tracker to have a very low limit for the test
    gateway.loop.budget_tracker.daily_limit = 0.0001
    
    test_content = (
        "This is an automated test. Tell me a long, detailed story about a space faring bee "
        "to consume a few tokens and trigger the budget gate."
    )
    
    msg = InboundMessage(
        channel="cli", 
        chat_id="test_budget",
        sender_id="user123",
        content=test_content,
        metadata={"channel_role": "admin"}
    )
    
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    async def capture_outbound(event: OutboundMessage):
        if event.chat_id == "test_budget" and not future.done():
            future.set_result(event)
            
    event_bus.subscribe_outbound("cli", capture_outbound)
    
    # We might need to make two calls if the first message alone doesn't trip the gate immediately
    # (since the gate checks *before* the call, and actual cost is recorded *after*).
    # Turn 1: Add cost
    await event_bus.publish_inbound(msg)
    
    # Wait for response 1
    outbound1 = await asyncio.wait_for(future, timeout=30.0)
    assert outbound1 is not None
    
    # The first call might succeed or might hit the limit depending on previous test state.
    # Let's ensure the budget is definitively exhausted.
    await gateway.loop.budget_tracker.add_cost(None, 10.0)
    
    # Turn 2: Try again, should hit the gate
    future2 = loop.create_future()
    async def capture_outbound2(event: OutboundMessage):
        if event.chat_id == "test_budget" and not future2.done():
            if "BUDGET ALERT" not in event.content: # Ignore proactive alerts for the future
                future2.set_result(event)

    event_bus.subscribe_outbound("cli", capture_outbound2)
    
    msg2 = InboundMessage(
        channel="cli", 
        chat_id="test_budget",
        sender_id="user123",
        content="Tell me another story.",
        metadata={"channel_role": "admin"}
    )
    
    await event_bus.publish_inbound(msg2)
    
    try:
        outbound2 = await asyncio.wait_for(future2, timeout=30.0)
        assert outbound2 is not None
        assert "SYSTEM HALT: Budget Exceeded" in outbound2.content
    finally:
        if capture_outbound in event_bus._outbound_subscribers.get("cli", []):
            event_bus._outbound_subscribers["cli"].remove(capture_outbound)
        if capture_outbound2 in event_bus._outbound_subscribers.get("cli", []):
            event_bus._outbound_subscribers["cli"].remove(capture_outbound2)

