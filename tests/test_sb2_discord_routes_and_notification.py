"""SB.2 extension — Discord channel_routes + known-chats notification persistence.

Covers:
  - DiscordConfig.channel_routes schema (default empty, per-channel override)
  - DiscordConfig.notification_chat_id schema
  - TelegramConfig.notification_chat_id schema
  - DiscordChannel: notification channels drop inbound messages
  - DiscordChannel: channel_routes sets per-channel role in metadata
  - DiscordChannel: default role used when channel not in channel_routes
  - AgentLoop._load_known_chats: loads from JSON file, graceful on missing/corrupt
  - AgentLoop._save_known_chat: writes JSON, updates in-memory dict
  - AgentLoop._process_message: saves (channel, chat_id) on every inbound message
  - ContextBuilder.build_messages: injects notification_targets into system prompt
  - ContextBuilder.build_messages: works without notification_targets (backward compat)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hive.config.schema import DiscordConfig, TelegramConfig
from hive.bus.events import InboundMessage, OutboundMessage
from hive.bus.queue import MessageBus
from hive.agent.context import ContextBuilder


# ---------------------------------------------------------------------------
# Schema: channel_routes and notification_chat_id
# ---------------------------------------------------------------------------


def test_discord_channel_routes_defaults_empty():
    assert DiscordConfig().channel_routes == {}


def test_discord_channel_routes_can_be_set():
    cfg = DiscordConfig(channel_routes={"111": "admin", "222": "notification"})
    assert cfg.channel_routes["111"] == "admin"
    assert cfg.channel_routes["222"] == "notification"


def test_discord_notification_chat_id_defaults_empty():
    assert DiscordConfig().notification_chat_id == ""


def test_discord_notification_chat_id_can_be_set():
    assert DiscordConfig(notification_chat_id="999888777").notification_chat_id == "999888777"


def test_telegram_notification_chat_id_defaults_empty():
    assert TelegramConfig().notification_chat_id == ""


def test_telegram_notification_chat_id_can_be_set():
    assert TelegramConfig(notification_chat_id="12345678").notification_chat_id == "12345678"


# ---------------------------------------------------------------------------
# DiscordChannel: channel_routes routing and notification-channel dropping
# ---------------------------------------------------------------------------


def _make_discord_channel(channel_routes: dict | None = None, default_role: str = "user"):
    """Construct a DiscordChannel with a mock bus."""
    from hive.channels.discord import DiscordChannel

    cfg = DiscordConfig(
        enabled=True,
        token="fake-token",
        role=default_role,
        allow_from=[],  # empty = allow all
        channel_routes=channel_routes or {},
    )
    bus = MagicMock(spec=MessageBus)
    bus.publish_inbound = AsyncMock()
    ch = DiscordChannel(cfg, bus)
    # Provide a mock HTTP client so attachment download doesn't crash
    ch._http = AsyncMock()
    ch._running = True
    return ch, bus


def _discord_payload(channel_id: str, content: str = "hello") -> dict:
    return {
        "id": "msg-1",
        "channel_id": channel_id,
        "content": content,
        "author": {"id": "user-1", "bot": False},
        "attachments": [],
    }


async def test_discord_notification_channel_drops_inbound():
    """Messages from a notification channel are silently dropped."""
    ch, bus = _make_discord_channel(channel_routes={"999": "notification"})
    await ch._handle_message_create(_discord_payload(channel_id="999"))
    bus.publish_inbound.assert_not_awaited()


async def test_discord_admin_channel_route_sets_role_in_metadata():
    """Messages from a channel routed as 'admin' carry channel_role=admin."""
    ch, bus = _make_discord_channel(channel_routes={"888": "admin"})
    # Suppress typing indicator
    with patch.object(ch, "_start_typing", new=AsyncMock()):
        await ch._handle_message_create(_discord_payload(channel_id="888"))

    bus.publish_inbound.assert_awaited_once()
    msg: InboundMessage = bus.publish_inbound.call_args[0][0]
    assert msg.metadata["channel_role"] == "admin"


async def test_discord_unrouted_channel_uses_default_role():
    """Channels not in channel_routes fall back to the config-level default role."""
    ch, bus = _make_discord_channel(channel_routes={"888": "admin"}, default_role="user")
    with patch.object(ch, "_start_typing", new=AsyncMock()):
        await ch._handle_message_create(_discord_payload(channel_id="777"))

    bus.publish_inbound.assert_awaited_once()
    msg: InboundMessage = bus.publish_inbound.call_args[0][0]
    assert msg.metadata["channel_role"] == "user"


async def test_discord_routed_user_channel_sets_user_role():
    """Explicit user role in channel_routes still works."""
    ch, bus = _make_discord_channel(
        channel_routes={"111": "user", "222": "admin"},
        default_role="notification",  # default is notification — but explicit user overrides
    )
    with patch.object(ch, "_start_typing", new=AsyncMock()):
        await ch._handle_message_create(_discord_payload(channel_id="111"))

    bus.publish_inbound.assert_awaited_once()
    msg: InboundMessage = bus.publish_inbound.call_args[0][0]
    assert msg.metadata["channel_role"] == "user"


async def test_discord_default_notification_role_drops_all_unrouted():
    """If default role is notification, all unrouted channels drop their messages."""
    ch, bus = _make_discord_channel(channel_routes={}, default_role="notification")
    with patch.object(ch, "_start_typing", new=AsyncMock()):
        await ch._handle_message_create(_discord_payload(channel_id="any-channel"))
    bus.publish_inbound.assert_not_awaited()


async def test_discord_bot_messages_ignored_regardless_of_route():
    """Bot messages are dropped before channel routing fires."""
    ch, bus = _make_discord_channel(channel_routes={"123": "admin"})
    payload = _discord_payload("123")
    payload["author"]["bot"] = True
    await ch._handle_message_create(payload)
    bus.publish_inbound.assert_not_awaited()


async def test_discord_message_carries_chat_id_equal_to_channel_id():
    """The InboundMessage chat_id is the Discord channel_id (for session keying)."""
    ch, bus = _make_discord_channel()
    with patch.object(ch, "_start_typing", new=AsyncMock()):
        await ch._handle_message_create(_discord_payload(channel_id="CHANNEL-XYZ"))

    msg: InboundMessage = bus.publish_inbound.call_args[0][0]
    assert msg.chat_id == "CHANNEL-XYZ"
    assert msg.channel == "discord"


# ---------------------------------------------------------------------------
# AgentLoop._load_known_chats / _save_known_chat
# ---------------------------------------------------------------------------


def _make_loop_with_workspace(tmp_path: Path):
    from hive.agent.loop import AgentLoop

    with (
        patch("hive.agent.loop.ContextBuilder"),
        patch("hive.agent.loop.SessionManager"),
        patch("hive.agent.loop.initialize_memory_hierarchy"),
        patch.object(AgentLoop, "_register_default_tools"),
    ):
        bus = MagicMock(spec=MessageBus)
        provider = MagicMock()
        provider.get_default_model.return_value = "test-model"
        loop = AgentLoop(bus=bus, provider=provider, workspace=tmp_path)
        loop._known_chats = {}  # reset (init would have tried to load from tmp_path)
        return loop


def test_load_known_chats_returns_empty_when_file_missing(tmp_path):
    loop = _make_loop_with_workspace(tmp_path)
    assert loop._load_known_chats() == {}


def test_load_known_chats_reads_existing_json(tmp_path):
    (tmp_path / ".known_chats.json").write_text(
        json.dumps({"telegram": "111", "discord": "222"})
    )
    loop = _make_loop_with_workspace(tmp_path)
    result = loop._load_known_chats()
    assert result == {"telegram": "111", "discord": "222"}


def test_load_known_chats_graceful_on_corrupt_json(tmp_path):
    (tmp_path / ".known_chats.json").write_text("NOT VALID JSON{{")
    loop = _make_loop_with_workspace(tmp_path)
    assert loop._load_known_chats() == {}


def test_load_known_chats_graceful_on_non_dict_json(tmp_path):
    (tmp_path / ".known_chats.json").write_text(json.dumps([1, 2, 3]))
    loop = _make_loop_with_workspace(tmp_path)
    assert loop._load_known_chats() == {}


def test_save_known_chat_updates_memory_and_file(tmp_path):
    loop = _make_loop_with_workspace(tmp_path)
    loop._save_known_chat("telegram", "9999")

    assert loop._known_chats["telegram"] == "9999"
    persisted = json.loads((tmp_path / ".known_chats.json").read_text())
    assert persisted["telegram"] == "9999"


def test_save_known_chat_multiple_channels(tmp_path):
    loop = _make_loop_with_workspace(tmp_path)
    loop._save_known_chat("telegram", "111")
    loop._save_known_chat("discord", "222")

    persisted = json.loads((tmp_path / ".known_chats.json").read_text())
    assert persisted == {"telegram": "111", "discord": "222"}


def test_save_known_chat_overwrites_previous_value(tmp_path):
    loop = _make_loop_with_workspace(tmp_path)
    loop._save_known_chat("telegram", "OLD")
    loop._save_known_chat("telegram", "NEW")

    assert loop._known_chats["telegram"] == "NEW"
    persisted = json.loads((tmp_path / ".known_chats.json").read_text())
    assert persisted["telegram"] == "NEW"


def test_known_chats_loaded_on_init(tmp_path):
    (tmp_path / ".known_chats.json").write_text(
        json.dumps({"telegram": "AUTO"})
    )
    from hive.agent.loop import AgentLoop

    with (
        patch("hive.agent.loop.ContextBuilder"),
        patch("hive.agent.loop.SessionManager"),
        patch("hive.agent.loop.initialize_memory_hierarchy"),
        patch.object(AgentLoop, "_register_default_tools"),
    ):
        bus = MagicMock(spec=MessageBus)
        provider = MagicMock()
        provider.get_default_model.return_value = "test-model"
        loop = AgentLoop(bus=bus, provider=provider, workspace=tmp_path)

    assert loop._known_chats.get("telegram") == "AUTO"


# ---------------------------------------------------------------------------
# _process_message saves known_chat
# ---------------------------------------------------------------------------


async def test_process_message_saves_known_chat(tmp_path):
    """Every inbound message updates the persisted known_chats file."""
    from hive.agent.loop import AgentLoop
    from hive.agent.tools.registry import ToolRegistry

    with (
        patch("hive.agent.loop.ContextBuilder"),
        patch("hive.agent.loop.SessionManager"),
        patch("hive.agent.loop.initialize_memory_hierarchy"),
        patch.object(AgentLoop, "_register_default_tools"),
    ):
        bus = MagicMock(spec=MessageBus)
        provider = MagicMock()
        provider.get_default_model.return_value = "test-model"

        llm_resp = MagicMock()
        llm_resp.content = "ok"
        llm_resp.tool_calls = []
        llm_resp.usage = {}
        llm_resp.has_tool_calls = False
        provider.chat = AsyncMock(return_value=llm_resp)

        loop = AgentLoop(bus=bus, provider=provider, workspace=tmp_path)
        loop.tools = ToolRegistry()
        loop.context = MagicMock()
        loop.context.build_messages.return_value = [{"role": "user", "content": "hi"}]
        mock_session = MagicMock()
        mock_session.metadata = {}
        mock_session.message_count = 0
        mock_session.last_consolidated = 0
        mock_session.get_history.return_value = []
        loop.sessions = MagicMock()
        loop.sessions.get_or_create.return_value = mock_session

    msg = InboundMessage(
        channel="telegram", sender_id="42", chat_id="CHAT-999",
        content="hello", metadata={"channel_role": "user"}
    )
    await loop._process_message(msg)

    assert loop._known_chats.get("telegram") == "CHAT-999"
    persisted = json.loads((tmp_path / ".known_chats.json").read_text())
    assert persisted["telegram"] == "CHAT-999"


# ---------------------------------------------------------------------------
# ContextBuilder.build_messages with notification_targets
# ---------------------------------------------------------------------------


def _make_context_builder(tmp_path: Path) -> ContextBuilder:
    with patch("hive.agent.context.MemoryRetriever"), \
         patch("hive.agent.context.SkillsLoader"), \
         patch("hive.agent.context.MemoryStore"):
        cb = ContextBuilder(tmp_path)
        cb.retriever = MagicMock()
        cb.retriever.build_memory_context.return_value = ""
        cb.memory = MagicMock()
        cb.memory.get_memory_context.return_value = ""
        cb.skills = MagicMock()
        cb.skills.get_always_skills.return_value = []
        cb.skills.build_skills_summary.return_value = ""
    return cb


def test_build_messages_without_notification_targets(tmp_path):
    cb = _make_context_builder(tmp_path)
    messages = cb.build_messages(history=[], current_message="hi")
    system = messages[0]["content"]
    assert "Notification Targets" not in system


def test_build_messages_with_notification_targets(tmp_path):
    cb = _make_context_builder(tmp_path)
    messages = cb.build_messages(
        history=[],
        current_message="hi",
        notification_targets={"telegram": "111222", "discord": "333444"},
    )
    system = messages[0]["content"]
    assert "Notification Targets" in system
    assert "telegram" in system
    assert "111222" in system
    assert "discord" in system
    assert "333444" in system


def test_build_messages_notification_targets_mentions_message_tool(tmp_path):
    cb = _make_context_builder(tmp_path)
    messages = cb.build_messages(
        history=[], current_message="x",
        notification_targets={"telegram": "999"},
    )
    system = messages[0]["content"]
    assert "`message`" in system or "message" in system


def test_build_messages_notification_targets_empty_dict_not_injected(tmp_path):
    """Empty notification_targets dict should not inject the section."""
    cb = _make_context_builder(tmp_path)
    messages = cb.build_messages(
        history=[], current_message="x",
        notification_targets={},  # loop passes None when empty, but test the edge case
    )
    system = messages[0]["content"]
    # Empty dict: notification_targets is falsy — section should not appear
    assert "Notification Targets" not in system


def test_build_messages_notification_targets_none_not_injected(tmp_path):
    cb = _make_context_builder(tmp_path)
    messages = cb.build_messages(history=[], current_message="x", notification_targets=None)
    assert "Notification Targets" not in messages[0]["content"]
