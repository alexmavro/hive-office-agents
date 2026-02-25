"""
E2E integration tests for the spawn and spawn_pipeline tools.

These tests exercise the FULL path from an InboundMessage through the AgentLoop,
LLM planning, tool execution (spawn / spawn_pipeline), WorkerRegistry, WorkerLoop,
and final WorkerReport — all the way back to a completion bus message.

Run with:
    ./.venv/bin/pytest tests/integration/test_e2e_spawn.py -m e2e -v --timeout=180

Cost: ~$0.05-0.15 per run (Gemini Flash). Run deliberately.
"""

import asyncio
import pytest
from pathlib import Path

from hive.bus.events import InboundMessage, OutboundMessage
from hive.agent.worker.schema import WorkerStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _wait_for_registry_result(
    registry,
    worker_name: str,
    timeout: float = 90.0,
    poll_interval: float = 1.0,
) -> bool:
    """Poll the WorkerRegistry until a result appears or timeout expires."""
    elapsed = 0.0
    while elapsed < timeout:
        if worker_name in registry._results:
            return True
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    return False


async def _wait_for_all_registry_results(
    registry,
    worker_names: list[str],
    timeout: float = 120.0,
    poll_interval: float = 1.0,
) -> bool:
    """Poll until ALL named workers appear in _results, or timeout expires."""
    elapsed = 0.0
    while elapsed < timeout:
        if all(name in registry._results for name in worker_names):
            return True
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    return False


# ---------------------------------------------------------------------------
# Test 1: Single worker spawn — registry confirms COMPLETED
# ---------------------------------------------------------------------------

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_single_spawn_completes_and_registry_confirmed(gateway, event_bus):
    """The Queen must spawn a single worker that finishes and is recorded as COMPLETED
    in the WorkerRegistry. This proves the full spawn→execute→complete→store path works.
    """
    test_content = (
        "This is an automated E2E test. "
        "Spawn a background worker named 'e2e_fact_checker' with the task: "
        "'Write exactly one sentence confirming you are a worker and are online.' "
        "Do NOT use the message tool. Return only the spawn tool call."
    )

    msg = InboundMessage(
        channel="cli",
        chat_id="test_spawn_complete",
        sender_id="e2e_tester",
        content=test_content,
        metadata={"channel_role": "admin"},
    )

    loop = asyncio.get_running_loop()
    future_ack = loop.create_future()

    async def capture_queen_ack(event: OutboundMessage):
        """Capture the Queen's acknowledgement that she spawned."""
        if event.chat_id == "test_spawn_complete" and not future_ack.done():
            future_ack.set_result(event)

    event_bus.subscribe_outbound("cli", capture_queen_ack)

    # Inject message
    await event_bus.publish_inbound(msg)

    # 1. Queen must acknowledge the spawn in reasonable time
    queen_ack = await asyncio.wait_for(future_ack, timeout=45.0)
    assert queen_ack is not None, "Queen did not respond to spawn instruction"

    # 2. Wait for the worker to complete and appear in the registry
    finished = await _wait_for_registry_result(
        gateway.worker_registry, "e2e_fact_checker", timeout=90.0
    )
    assert finished, (
        "Worker 'e2e_fact_checker' did not complete within 90 seconds. "
        f"Registry results: {list(gateway.worker_registry._results.keys())}"
    )

    report = gateway.worker_registry._results["e2e_fact_checker"]
    assert report.status == WorkerStatus.COMPLETED, (
        f"Worker finished with unexpected status '{report.status.value}'. "
        f"Error: {report.error}"
    )
    assert report.output, "Worker completed but produced no output"

    # Cleanup subscriber
    event_bus._outbound_subscribers.get("cli", []).remove(capture_queen_ack)


# ---------------------------------------------------------------------------
# Test 2: Pipeline — stage 2 must receive stage 1 output
# ---------------------------------------------------------------------------

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_pipeline_chains_stage_output(gateway, event_bus):
    """A 2-stage pipeline must chain outputs: stage 2 receives stage 1's result.

    Stage 1 outputs a secret code word. Stage 2 is instructed to include that
    code word in its output. If the code word appears in the final pipeline
    completion message, we know chaining worked.
    """
    # A short, deterministic marker the first worker must produce
    # and the second worker must reference.
    secret_token = "PIPELINE_CHAIN_VERIFIED"

    test_content = (
        "This is an automated E2E test for pipeline chaining. "
        "Use spawn_pipeline with pipeline_name='e2e_chain_test' and these EXACT two tasks: "
        f"Task 1: name='stage_one', task='Output exactly this text and nothing else: {secret_token}' "
        f"Task 2: name='stage_two', task='You will receive input from a previous stage. "
        f"Your job is to repeat back whatever text was passed to you from the previous stage, "
        f"verbatim, with no modifications.' "
        "Do NOT use any other tools. Return only the spawn_pipeline call."
    )

    msg = InboundMessage(
        channel="cli",
        chat_id="test_pipeline_chain",
        sender_id="e2e_tester",
        content=test_content,
        metadata={"channel_role": "admin"},
    )

    loop = asyncio.get_running_loop()
    future_ack = loop.create_future()

    async def capture_ack(event: OutboundMessage):
        if event.chat_id == "test_pipeline_chain" and not future_ack.done():
            future_ack.set_result(event)

    event_bus.subscribe_outbound("cli", capture_ack)
    await event_bus.publish_inbound(msg)

    # Queen acknowledges pipeline launch
    ack = await asyncio.wait_for(future_ack, timeout=45.0)
    assert "e2e_chain_test" in (ack.content or "").lower() or "pipeline" in (ack.content or "").lower(), (
        f"Queen's ack did not mention the pipeline: {ack.content[:200]}"
    )

    # Both workers must complete
    finished = await _wait_for_all_registry_results(
        gateway.worker_registry,
        ["stage_one", "stage_two"],
        timeout=120.0,
    )
    assert finished, (
        "Pipeline stages did not complete in 120 seconds. "
        f"Registry: {list(gateway.worker_registry._results.keys())}"
    )

    stage1_report = gateway.worker_registry._results["stage_one"]
    stage2_report = gateway.worker_registry._results["stage_two"]

    assert stage1_report.status == WorkerStatus.COMPLETED, (
        f"Stage 1 failed: {stage1_report.error}"
    )
    assert stage2_report.status == WorkerStatus.COMPLETED, (
        f"Stage 2 failed: {stage2_report.error}"
    )

    # The secret token must appear in stage 1's output (it produced it)
    assert secret_token in (stage1_report.output or ""), (
        f"Stage 1 did not produce the expected token. Output: {stage1_report.output}"
    )

    # Stage 2 must have received stage 1's output via chaining
    # (the pipeline appends prior output to stage 2's task prompt)
    assert secret_token in (stage2_report.output or ""), (
        f"Stage 2 did not echo the chained token — output chaining is broken. "
        f"Stage 2 output: {stage2_report.output}"
    )

    event_bus._outbound_subscribers.get("cli", []).remove(capture_ack)


# ---------------------------------------------------------------------------
# Test 3: Pipeline completion message routes to the CORRECT origin channel
# ---------------------------------------------------------------------------

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_pipeline_completion_routes_to_origin_channel(gateway, event_bus):
    """Pipeline bus messages must contain the correct origin channel/chat_id.

    Before the fix, SpawnPipelineTool defaulted self.channel='cli' and
    self.chat_id='direct', so all completion messages were routed to 'cli:direct'
    — a dead destination. After the fix, set_context() is called per-message
    and the pipeline uses the real channel/chat_id.

    We verify this by inspecting the system InboundMessage chat_id format
    ('cli:test_pipeline_routing') rather than the dead 'cli:direct'.
    """
    test_content = (
        "This is an automated E2E test. "
        "Use spawn_pipeline with pipeline_name='e2e_routing_test' and tasks: "
        "Task 1: name='routing_worker', task='Output exactly: ROUTING_CONFIRMED' "
        "Task 2: name='routing_worker_2', task='Output exactly: ROUTING_CONFIRMED_STAGE2' "
        "Do NOT use any other tools."
    )

    msg = InboundMessage(
        channel="cli",
        chat_id="test_pipeline_routing",
        sender_id="e2e_tester",
        content=test_content,
        metadata={"channel_role": "admin"},
    )

    loop = asyncio.get_running_loop()
    future_ack = loop.create_future()
    captured_system_messages: list[InboundMessage] = []

    # Intercept system-channel messages BEFORE they reach the AgentLoop.
    # We do this by monkey-patching publish_inbound temporarily.
    original_publish = event_bus.publish_inbound

    async def intercepting_publish(event: InboundMessage):
        if isinstance(event, InboundMessage) and event.channel == "system":
            captured_system_messages.append(event)
        await original_publish(event)

    event_bus.publish_inbound = intercepting_publish

    async def capture_ack(event: OutboundMessage):
        if event.chat_id == "test_pipeline_routing" and not future_ack.done():
            future_ack.set_result(event)

    event_bus.subscribe_outbound("cli", capture_ack)
    await event_bus.publish_inbound(msg)

    await asyncio.wait_for(future_ack, timeout=45.0)

    # Wait for the pipeline to finish its background task
    finished = await _wait_for_all_registry_results(
        gateway.worker_registry,
        ["routing_worker", "routing_worker_2"],
        timeout=120.0,
    )
    assert finished, (
        "Pipeline did not complete in 120 seconds. "
        f"Registry keys: {list(gateway.worker_registry._results.keys())}"
    )

    # Restore original publish
    event_bus.publish_inbound = original_publish
    event_bus._outbound_subscribers.get("cli", []).remove(capture_ack)

    # Validate system messages have correct chat_id
    pipeline_msgs = [
        m for m in captured_system_messages
        if "e2e_routing_test" in m.content or "routing_worker" in m.content
    ]
    assert pipeline_msgs, (
        "No system messages were published for the pipeline. "
        "Pipeline may have crashed before sending any bus notifications."
    )

    for sys_msg in pipeline_msgs:
        assert sys_msg.chat_id == "cli:test_pipeline_routing", (
            f"System message routed to wrong destination: '{sys_msg.chat_id}'. "
            f"Expected 'cli:test_pipeline_routing'. "
            f"This means set_context() was not called before orchestrate_pipeline ran. "
            f"Message content: {sys_msg.content[:150]}"
        )
