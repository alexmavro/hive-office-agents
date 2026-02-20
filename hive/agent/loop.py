"""Agent loop: the core processing engine."""

import asyncio
from contextlib import AsyncExitStack
import json
import json_repair
import re
import time
from pathlib import Path
from typing import Any, TYPE_CHECKING

from loguru import logger

from hive.bus.events import InboundMessage, OutboundMessage
from hive.bus.queue import MessageBus
from hive.providers.base import LLMProvider
from hive.agent.context import ContextBuilder
from hive.agent.tools.registry import ToolRegistry
from hive.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from hive.agent.tools.shell import ExecTool
from hive.agent.tools.web import WebSearchTool, WebFetchTool
from hive.agent.tools.message import MessageTool
from hive.agent.tools.spawn import SpawnTool
from hive.agent.tools.cron import CronTool
from hive.agent.tools.report_task import ReportTaskTool
from hive.agent.tools.docker_exec import DockerExecTool
from hive.agent.memory import MemoryStore, initialize_memory_hierarchy
from hive.agent.consolidation import detect_signal, consolidate
from hive.agent.onboarding import OnboardingFlow, get_document_intake_prompt, get_link_intake_prompt
from hive.agent.admin import factory_reset, CONFIRM_PHRASE
from hive.agent.subagent import SubagentManager
from hive.session.dag import MessageEntry
from hive.session.manager import Session, SessionManager

if TYPE_CHECKING:
    from hive.audit import AuditLogger

# Simple prompt-injection signal patterns — matched on raw inbound content.
# We do NOT store the content; we only flag its presence in the audit log.
_INJECTION_PATTERNS = re.compile(
    r"ignore\s+(all\s+)?previous\s+instructions"
    r"|disregard\s+(all\s+)?previous"
    r"|forget\s+(all\s+)?previous"
    r"|you\s+are\s+now\s+"
    r"|new\s+instructions?\s*:"
    r"|pretend\s+(you\s+are|to\s+be)"
    r"|\boverride\s+(all\s+)?(instructions|rules|guidelines)"
    r"|\bsystem\s+prompt\b",
    re.IGNORECASE,
)


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 20,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        memory_window: int = 50,
        brave_api_key: str | None = None,
        exec_config: "ExecToolConfig | None" = None,
        cron_service: "CronService | None" = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        mcp_servers: dict | None = None,
        audit: "AuditLogger | None" = None,
    ):
        from hive.config.schema import ExecToolConfig
        from hive.cron.service import CronService
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_window = memory_window
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace
        self._audit = audit

        # Initialise memory/ hierarchy from templates on first boot (idempotent)
        _templates_dir = Path(__file__).parent.parent.parent / "templates" / "memory"
        initialize_memory_hierarchy(workspace, _templates_dir if _templates_dir.exists() else None)

        self.context = ContextBuilder(workspace)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry(audit=audit)
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            brave_api_key=brave_api_key,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
        )
        
        self._running = False
        self._mcp_servers = mcp_servers or {}
        self._mcp_stack: AsyncExitStack | None = None
        self._mcp_connected = False
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        # File tools (restrict to workspace if configured)
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        self.tools.register(ReadFileTool(allowed_dir=allowed_dir))
        self.tools.register(WriteFileTool(allowed_dir=allowed_dir))
        self.tools.register(EditFileTool(allowed_dir=allowed_dir))
        self.tools.register(ListDirTool(allowed_dir=allowed_dir))
        
        # Shell tool
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
        ))
        
        # Web tools
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())
        
        # Message tool
        message_tool = MessageTool(send_callback=self.bus.publish_outbound)
        self.tools.register(message_tool)
        
        # Spawn tool (for subagents)
        spawn_tool = SpawnTool(manager=self.subagents)
        self.tools.register(spawn_tool)
        
        # Cron tool (for scheduling)
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))

        # Signal tool — triggers memory consolidation on meaningful events
        self.tools.register(ReportTaskTool(consolidation_callback=self._handle_signal))

        # Docker sandbox — only if image is built
        if DockerExecTool.is_available():
            self.tools.register(DockerExecTool())
        else:
            logger.debug(
                "docker_exec tool not registered: hive-worker image not found. "
                "Run: docker build -f worker.Dockerfile -t hive-worker:latest ."
            )
    
    async def _connect_mcp(self) -> None:
        """Connect to configured MCP servers (one-time, lazy)."""
        if self._mcp_connected or not self._mcp_servers:
            return
        self._mcp_connected = True
        from hive.agent.tools.mcp import connect_mcp_servers
        self._mcp_stack = AsyncExitStack()
        await self._mcp_stack.__aenter__()
        await connect_mcp_servers(self._mcp_servers, self.tools, self._mcp_stack)

    def _set_tool_context(self, channel: str, chat_id: str) -> None:
        """Update context for all tools that need routing info."""
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.set_context(channel, chat_id)

        if spawn_tool := self.tools.get("spawn"):
            if isinstance(spawn_tool, SpawnTool):
                spawn_tool.set_context(channel, chat_id)

        if cron_tool := self.tools.get("cron"):
            if isinstance(cron_tool, CronTool):
                cron_tool.set_context(channel, chat_id)

    async def _run_agent_loop(self, initial_messages: list[dict]) -> tuple[str | None, list[str]]:
        """
        Run the agent iteration loop.

        Args:
            initial_messages: Starting messages for the LLM conversation.

        Returns:
            Tuple of (final_content, list_of_tools_used).
        """
        messages = initial_messages
        iteration = 0
        final_content = None
        tools_used: list[str] = []

        while iteration < self.max_iterations:
            iteration += 1

            _t0_llm = time.monotonic()
            _llm_error: str | None = None
            _llm_usage: dict = {}
            _llm_tool_calls: list = []
            try:
                response = await self.provider.chat(
                    messages=messages,
                    tools=self.tools.get_definitions(),
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                _llm_usage = response.usage or {}
                _llm_tool_calls = response.tool_calls
            except Exception as _exc:
                _llm_error = str(_exc)[:200]
                raise
            finally:
                if self._audit:
                    _duration_ms = (time.monotonic() - _t0_llm) * 1000
                    _tool_names = [tc.name for tc in _llm_tool_calls] if _llm_tool_calls else None
                    await self._audit.log_llm_call(
                        model=self.model,
                        tokens_in=_llm_usage.get("prompt_tokens", 0),
                        tokens_out=_llm_usage.get("completion_tokens", 0),
                        tool_calls_n=len(_llm_tool_calls),
                        duration_ms=_duration_ms,
                        tool_names=_tool_names,
                        session_id=self.tools._session_id,
                        error=_llm_error,
                    )

            if response.has_tool_calls:
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )

                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info(f"Tool call: {tool_call.name}({args_str[:200]})")
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
                messages.append({"role": "user", "content": "Reflect on the results and decide next steps."})
            else:
                final_content = response.content
                break

        return final_content, tools_used

    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        await self._connect_mcp()
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )
                try:
                    response = await self._process_message(msg)
                    if response:
                        await self.bus.publish_outbound(response)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"Sorry, I encountered an error: {str(e)}"
                    ))
            except asyncio.TimeoutError:
                continue
    
    async def close_mcp(self) -> None:
        """Close MCP connections."""
        if self._mcp_stack:
            try:
                await self._mcp_stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass  # MCP SDK cancel scope cleanup is noisy but harmless
            self._mcp_stack = None

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")
    
    async def _process_message(self, msg: InboundMessage, session_key: str | None = None) -> OutboundMessage | None:
        """
        Process a single inbound message.
        
        Args:
            msg: The inbound message to process.
            session_key: Override session key (used by process_direct).
        
        Returns:
            The response message, or None if no response needed.
        """
        # System messages route back via chat_id ("channel:chat_id")
        if msg.channel == "system":
            return await self._process_system_message(msg)
        
        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info(f"Processing message from {msg.channel}:{msg.sender_id}: {preview}")

        key = session_key or msg.session_key
        self.tools._session_id = key
        if self._audit:
            injection_signal = bool(_INJECTION_PATTERNS.search(msg.content))
            await self._audit.log_channel_event(
                direction="in",
                channel=msg.channel,
                session_id=key,
                content_length=len(msg.content),
                injection_signal=injection_signal,
            )

        session = self.sessions.get_or_create(key)
        
        # Handle slash commands
        cmd = msg.content.strip().lower()
        if cmd == "/new":
            # Snapshot the current dag before clearing (clear() creates a fresh in-memory dag)
            old_dag = session._dag
            session.clear()
            self.sessions.save(session)
            self.sessions.invalidate(session.key)

            async def _consolidate_and_cleanup():
                temp_session = Session(key=session.key)
                temp_session._dag = old_dag
                await self._consolidate_memory(temp_session, archive_all=True)

            asyncio.create_task(_consolidate_and_cleanup())
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="New session started. Memory consolidation in progress.")
        if cmd == "/reset":
            # Hard reset: delete session file entirely, no memory consolidation.
            self.sessions.delete(session.key)
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="Session deleted. Fresh start — no history, no consolidation.")
        if cmd == "/help":
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="🐝 hive commands:\n/new — New conversation (saves memory)\n/reset — Hard reset (deletes session entirely)\n/onboard — Set up your profile\n/help — Show this")

        # Onboarding: /onboard triggers an LLM-driven intake interview.
        # The mission prompt is injected as the "current message" so the Queen
        # sees it, interprets it, and responds with her first question.
        # No message interception — all subsequent messages go through the normal LLM loop.
        if cmd == "/onboard":
            onboarding = OnboardingFlow(self.workspace / "memory")
            mission = onboarding.start()
            self._set_tool_context(msg.channel, msg.chat_id)
            initial_messages = self.context.build_messages(
                history=session.get_history(max_messages=self.memory_window),
                current_message=mission,
                channel=msg.channel,
                chat_id=msg.chat_id,
            )
            final_content, tools_used = await self._run_agent_loop(initial_messages)
            if final_content is None:
                final_content = "Starting onboarding — I'll ask you a few questions to set up your profile."
            session.add_message("user", "/onboard")
            session.add_message("assistant", final_content,
                                tools_used=tools_used if tools_used else None)
            self.sessions.save(session)
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=final_content)

        # Factory reset: /factory-reset or /factory_reset (Telegram uses underscores in command menu)
        if cmd in ("/factory-reset", "/factory_reset"):
            warning = await factory_reset(
                workspace=self.workspace,
                templates_dir=None,  # resolved below if available
                sessions_dir=self.workspace.parent / "sessions",
                confirm=False,
            )
            session.metadata["awaiting_factory_reset_confirm"] = True
            session.add_message("user", msg.content)
            session.add_message("assistant", warning)
            self.sessions.save(session)
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=warning)

        if session.metadata.get("awaiting_factory_reset_confirm") and msg.content.strip() == CONFIRM_PHRASE:
            session.metadata.pop("awaiting_factory_reset_confirm")
            # Resolve templates_dir relative to this file's package root
            templates_dir = Path(__file__).parent.parent.parent / "templates" / "memory"
            if not templates_dir.exists():
                templates_dir = None
            result = await factory_reset(
                workspace=self.workspace,
                templates_dir=templates_dir,
                sessions_dir=self.workspace.parent / "sessions",
                confirm=True,
            )
            # Sessions dir was wiped — recreate it before writing
            (self.workspace.parent / "sessions").mkdir(parents=True, exist_ok=True)
            fresh_session = self.sessions.get_or_create(key)
            fresh_session.add_message("user", msg.content)
            fresh_session.add_message("assistant", result)
            self.sessions.save(fresh_session)
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=result)

        # Proactive compaction: keep context bounded and memory files current.
        # Fire when session exceeds memory_window AND at least memory_window // 2
        # new messages have arrived since the last compaction — prevents
        # both context overflow and compacting on every single message after 50.
        _new_since_last = session.message_count - session.last_consolidated
        if session.message_count > self.memory_window and _new_since_last >= self.memory_window // 2:
            asyncio.create_task(self._consolidate_memory(session))

        # Profile intake: detect uploaded documents or bare URLs and inject a structured
        # mission so the Queen reads the content, shows a summary, and waits for
        # confirmation before writing anything to memory.
        import re as _re
        _IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        _AUDIO_EXTS = {".ogg", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".opus"}
        _URL_ONLY = _re.compile(r"^https?://\S+$")

        uploaded_docs = [
            p for p in (msg.media or [])
            if Path(p).suffix.lower() not in _IMAGE_EXTS
            and Path(p).suffix.lower() not in _AUDIO_EXTS
        ]
        audio_files = [
            p for p in (msg.media or [])
            if Path(p).suffix.lower() in _AUDIO_EXTS
        ]
        if audio_files:
            # Cannot transcribe audio yet — acknowledge gracefully, keep context
            current_message = (
                "The user sent a voice message (audio file). "
                "You cannot transcribe or play audio files yet. "
                "Acknowledge that you received the voice note, tell them you can't process audio yet, "
                "and ask them to type their message instead. "
                "Do NOT ask 'yes to what?' or pretend you don't know what they sent."
            )
        elif uploaded_docs:
            # Strip auto-generated [file: ...] / [image: ...] markers to get clean user text
            user_text = _re.sub(r"\[[^\]]+:[^\]]+\]", "", msg.content).strip()
            current_message = get_document_intake_prompt(uploaded_docs, self.workspace, user_text)
        elif _URL_ONLY.match(msg.content.strip()):
            # Bare URL with no other content — treat as a profile/link to intake
            current_message = get_link_intake_prompt(msg.content.strip(), self.workspace)
        else:
            current_message = msg.content

        self._set_tool_context(msg.channel, msg.chat_id)
        initial_messages = self.context.build_messages(
            history=session.get_history(max_messages=self.memory_window),
            current_message=current_message,
            media=msg.media if msg.media else None,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )
        final_content, tools_used = await self._run_agent_loop(initial_messages)

        if final_content is None:
            final_content = "I've completed processing but have no response to give."
        
        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info(f"Response to {msg.channel}:{msg.sender_id}: {preview}")
        
        session.add_message("user", msg.content)
        session.add_message("assistant", final_content,
                            tools_used=tools_used if tools_used else None)
        self.sessions.save(session)

        if self._audit:
            await self._audit.log_channel_event(
                direction="out",
                channel=msg.channel,
                session_id=key,
                content_length=len(final_content),
            )

        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            metadata=msg.metadata or {},  # Pass through for channel-specific needs (e.g. Slack thread_ts)
        )
    
    async def _process_system_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        Process a system message (e.g., subagent announce).
        
        The chat_id field contains "original_channel:original_chat_id" to route
        the response back to the correct destination.
        """
        logger.info(f"Processing system message from {msg.sender_id}")
        
        # Parse origin from chat_id (format: "channel:chat_id")
        if ":" in msg.chat_id:
            parts = msg.chat_id.split(":", 1)
            origin_channel = parts[0]
            origin_chat_id = parts[1]
        else:
            # Fallback
            origin_channel = "cli"
            origin_chat_id = msg.chat_id
        
        session_key = f"{origin_channel}:{origin_chat_id}"
        session = self.sessions.get_or_create(session_key)
        self._set_tool_context(origin_channel, origin_chat_id)
        initial_messages = self.context.build_messages(
            history=session.get_history(max_messages=self.memory_window),
            current_message=msg.content,
            channel=origin_channel,
            chat_id=origin_chat_id,
        )
        final_content, _ = await self._run_agent_loop(initial_messages)

        if final_content is None:
            final_content = "Background task completed."
        
        session.add_message("user", f"[System: {msg.sender_id}] {msg.content}")
        session.add_message("assistant", final_content)
        self.sessions.save(session)
        
        return OutboundMessage(
            channel=origin_channel,
            chat_id=origin_chat_id,
            content=final_content
        )
    
    async def _consolidate_memory(self, session, archive_all: bool = False) -> None:
        """Consolidate old messages into MEMORY.md and a DAG CompactionEntry.

        Args:
            archive_all: If True, archive the entire session path (used by /new command).
                       If False, archive only newly accumulated messages.
        """
        memory = MemoryStore(self.workspace)
        path = session._dag.get_path()

        if archive_all:
            old_entries = path
            keep_count = 0
            logger.info(f"Memory consolidation (archive_all): {len(path)} entries archived")
        else:
            keep_count = self.memory_window // 2
            if session.message_count <= keep_count:
                logger.debug(f"Session {session.key}: No consolidation needed (messages={session.message_count}, keep={keep_count})")
                return

            messages_to_process = session.message_count - session.last_consolidated
            if messages_to_process <= 0:
                logger.debug(f"Session {session.key}: No new messages to consolidate (last_consolidated={session.last_consolidated}, total={session.message_count})")
                return

            old_entries = path[session.last_consolidated:-keep_count]
            if not old_entries:
                return
            logger.info(f"Memory consolidation started: {session.message_count} total, {len(old_entries)} new to consolidate, {keep_count} keep")

        lines = []
        for e in old_entries:
            if not isinstance(e, MessageEntry) or not e.content:
                continue
            tools = f" [tools: {', '.join(e.tools_used)}]" if e.tools_used else ""
            lines.append(f"[{e.timestamp[:16]}] {e.role.upper()}{tools}: {e.content}")
        conversation = "\n".join(lines)
        current_memory = memory.read_long_term()

        prompt = f"""You are a memory consolidation agent. Process this conversation and return a JSON object with exactly two keys:

1. "history_entry": A paragraph (2-5 sentences) summarizing the key events/decisions/topics. Start with a timestamp like [YYYY-MM-DD HH:MM]. Include enough detail to be useful when found by grep search later.

2. "memory_update": The updated long-term memory content. Add any new facts: user location, preferences, personal info, habits, project context, technical decisions, tools/services used. If nothing new, return the existing content unchanged.

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{conversation}

Respond with ONLY valid JSON, no markdown fences."""

        try:
            response = await self.provider.chat(
                messages=[
                    {"role": "system", "content": "You are a memory consolidation agent. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
            )
            text = (response.content or "").strip()
            if not text:
                logger.warning("Memory consolidation: LLM returned empty response, skipping")
                return
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json_repair.loads(text)
            if not isinstance(result, dict):
                logger.warning(f"Memory consolidation: unexpected response type, skipping. Response: {text[:200]}")
                return

            if summary := result.get("history_entry"):
                # Write summary as a CompactionEntry in the DAG (replaces HISTORY.md)
                first_kept_id = path[-keep_count].id if keep_count > 0 and path else ""
                session._dag.compact(summary=summary, first_kept_entry_id=first_kept_id)

            if update := result.get("memory_update"):
                if update != current_memory:
                    memory.write_long_term(update)

            if archive_all:
                session.last_consolidated = 0
            else:
                session.last_consolidated = session.message_count - keep_count
            logger.info(f"Memory consolidation done: {session.message_count} messages, last_consolidated={session.last_consolidated}")
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")

    async def _handle_signal(self, event: dict) -> None:
        """Handle a signal from the report_task tool.

        Detects the signal type and fires consolidation as an asyncio task.
        The current session is retrieved from the tool context stored on the loop.
        """
        signal_type = detect_signal(event)
        if not signal_type:
            logger.debug(f"_handle_signal: no signal for event status={event.get('status')!r}")
            return

        # Retrieve current session from context (set per-message via _set_tool_context)
        channel = getattr(self, "_current_channel", "cli")
        chat_id = getattr(self, "_current_chat_id", "direct")
        session = self.sessions.get_or_create(f"{channel}:{chat_id}")
        memory_dir = self.workspace / "memory"

        logger.info(f"Signal detected: {signal_type} (status={event.get('status')})")
        asyncio.create_task(
            consolidate(
                signal_type=signal_type,
                event=event,
                memory_dir=memory_dir,
                provider=self.provider,
                model=self.model,
                session=session,
            )
        )

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
    ) -> str:
        """
        Process a message directly (for CLI or cron usage).
        
        Args:
            content: The message content.
            session_key: Session identifier (overrides channel:chat_id for session lookup).
            channel: Source channel (for tool context routing).
            chat_id: Source chat ID (for tool context routing).
        
        Returns:
            The agent's response.
        """
        await self._connect_mcp()
        msg = InboundMessage(
            channel=channel,
            sender_id="user",
            chat_id=chat_id,
            content=content
        )
        
        response = await self._process_message(msg, session_key=session_key)
        return response.content if response else ""
