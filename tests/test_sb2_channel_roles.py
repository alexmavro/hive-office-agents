"""SB.2 — Channel role config and admin-channel approval dispatch tests.

Covers:
  - Role field defaults and overrides on all channel config models
  - BaseChannel.role property
  - channel_role in InboundMessage metadata (via _handle_message)
  - AgentLoop._handle_admin_approval: valid/invalid/all approval commands
  - Admin-channel intercept in _process_message bypasses the LLM
  - Non-admin channel APPROVE messages are NOT intercepted
  - SB.1 fix: ToolRegistry initialised with workspace in AgentLoop
  - SB.1 fix: SessionApproveTool registered in AgentLoop tool list
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hive.config.schema import (
    TelegramConfig, DiscordConfig, FeishuConfig, DingTalkConfig,
    SlackConfig, EmailConfig, MochatConfig, QQConfig, WhatsAppConfig,
    ChannelsConfig,
)
from hive.channels.base import BaseChannel
from hive.bus.events import InboundMessage, OutboundMessage
from hive.bus.queue import MessageBus


# ---------------------------------------------------------------------------
# Channel config role field defaults
# ---------------------------------------------------------------------------


def test_telegram_role_defaults_to_user():
    assert TelegramConfig().role == "user"


def test_discord_role_defaults_to_user():
    assert DiscordConfig().role == "user"


def test_feishu_role_defaults_to_user():
    assert FeishuConfig().role == "user"


def test_dingtalk_role_defaults_to_user():
    assert DingTalkConfig().role == "user"


def test_slack_role_defaults_to_user():
    assert SlackConfig().role == "user"


def test_email_role_defaults_to_user():
    assert EmailConfig().role == "user"


def test_mochat_role_defaults_to_user():
    assert MochatConfig().role == "user"


def test_qq_role_defaults_to_user():
    assert QQConfig().role == "user"


def test_whatsapp_role_defaults_to_user():
    assert WhatsAppConfig().role == "user"


def test_telegram_role_can_be_admin():
    cfg = TelegramConfig(role="admin")
    assert cfg.role == "admin"


def test_telegram_role_can_be_notification():
    cfg = TelegramConfig(role="notification")
    assert cfg.role == "notification"


def test_discord_role_can_be_admin():
    assert DiscordConfig(role="admin").role == "admin"


def test_channels_config_contains_all_channel_models():
    """ChannelsConfig correctly bundles all channel configs."""
    cfg = ChannelsConfig()
    assert hasattr(cfg, "telegram")
    assert hasattr(cfg, "discord")
    assert hasattr(cfg, "feishu")
    assert hasattr(cfg, "dingtalk")
    assert hasattr(cfg, "slack")
    assert hasattr(cfg, "email")
    assert hasattr(cfg, "mochat")
    assert hasattr(cfg, "qq")
    assert hasattr(cfg, "whatsapp")


# ---------------------------------------------------------------------------
# BaseChannel.role property
# ---------------------------------------------------------------------------


class _MinimalChannel(BaseChannel):
    """Minimal concrete BaseChannel for testing."""

    name = "test"

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send(self, msg: OutboundMessage) -> None:
        pass


def _make_bus() -> MessageBus:
    bus = MagicMock(spec=MessageBus)
    bus.publish_inbound = AsyncMock()
    return bus


def test_base_channel_role_reads_from_config():
    cfg = TelegramConfig(role="admin")
    ch = _MinimalChannel(cfg, _make_bus())
    assert ch.role == "admin"


def test_base_channel_role_defaults_user_when_config_has_no_role():
    """Graceful fallback for configs without a role attribute."""

    class _NoRoleConfig:
        allow_from: list = []

    ch = _MinimalChannel(_NoRoleConfig(), _make_bus())
    assert ch.role == "user"


# ---------------------------------------------------------------------------
# channel_role injected into InboundMessage metadata via _handle_message
# ---------------------------------------------------------------------------


async def test_handle_message_includes_channel_role_user():
    cfg = TelegramConfig(role="user", allow_from=[])
    bus = _make_bus()
    ch = _MinimalChannel(cfg, bus)

    await ch._handle_message(sender_id="42", chat_id="42", content="hello")

    bus.publish_inbound.assert_awaited_once()
    published: InboundMessage = bus.publish_inbound.call_args[0][0]
    assert published.metadata["channel_role"] == "user"


async def test_handle_message_includes_channel_role_admin():
    cfg = TelegramConfig(role="admin", allow_from=[])
    bus = _make_bus()
    ch = _MinimalChannel(cfg, bus)

    await ch._handle_message(sender_id="42", chat_id="42", content="APPROVE exec")

    bus.publish_inbound.assert_awaited_once()
    published: InboundMessage = bus.publish_inbound.call_args[0][0]
    assert published.metadata["channel_role"] == "admin"


async def test_handle_message_merges_caller_metadata_with_channel_role():
    cfg = TelegramConfig(role="notification", allow_from=[])
    bus = _make_bus()
    ch = _MinimalChannel(cfg, bus)

    await ch._handle_message(
        sender_id="1", chat_id="1", content="ping",
        metadata={"user_id": 999, "extra": "x"}
    )

    published: InboundMessage = bus.publish_inbound.call_args[0][0]
    assert published.metadata["channel_role"] == "notification"
    assert published.metadata["user_id"] == 999
    assert published.metadata["extra"] == "x"


async def test_handle_message_caller_cannot_override_channel_role():
    """The channel role from config always wins — callers cannot spoof it."""
    cfg = TelegramConfig(role="user", allow_from=[])
    bus = _make_bus()
    ch = _MinimalChannel(cfg, bus)

    # Caller passes channel_role="admin" — should be overwritten by the real config role
    await ch._handle_message(
        sender_id="1", chat_id="1", content="evil",
        metadata={"channel_role": "admin"}
    )

    published: InboundMessage = bus.publish_inbound.call_args[0][0]
    assert published.metadata["channel_role"] == "user"


# ---------------------------------------------------------------------------
# AgentLoop._handle_admin_approval unit tests
# ---------------------------------------------------------------------------


def _make_loop():
    """Return an AgentLoop with all heavy dependencies mocked out."""
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
        workspace = Path("/tmp/test-workspace")

        loop = AgentLoop(bus=bus, provider=provider, workspace=workspace)
        # Replace tools with a real ToolRegistry for approval testing
        loop.tools = ToolRegistry()
        return loop


def test_handle_admin_approval_unknown_token_returns_error():
    loop = _make_loop()
    result = loop._handle_admin_approval("APPROVE foobar")
    assert result is not None
    assert "Unknown approval category" in result
    assert "foobar" in result


def test_handle_admin_approval_returns_none_for_non_approve_message():
    loop = _make_loop()
    assert loop._handle_admin_approval("hello there") is None
    assert loop._handle_admin_approval("approve") is None  # no space + category
    assert loop._handle_admin_approval("YES") is None
    assert loop._handle_admin_approval("NO") is None
    assert loop._handle_admin_approval("") is None


def test_handle_admin_approval_exec():
    loop = _make_loop()
    result = loop._handle_admin_approval("APPROVE exec")
    assert result is not None
    assert "exec" in result
    assert "exec" in loop.tools._pre_approved


def test_handle_admin_approval_write():
    loop = _make_loop()
    result = loop._handle_admin_approval("APPROVE write")
    assert result is not None
    assert "write" in loop.tools._pre_approved


def test_handle_admin_approval_git():
    loop = _make_loop()
    result = loop._handle_admin_approval("APPROVE git")
    assert "git" in loop.tools._pre_approved


def test_handle_admin_approval_packages():
    loop = _make_loop()
    result = loop._handle_admin_approval("APPROVE packages")
    assert "packages" in loop.tools._pre_approved


def test_handle_admin_approval_spawn():
    loop = _make_loop()
    result = loop._handle_admin_approval("APPROVE spawn")
    assert "spawn" in loop.tools._pre_approved


def test_handle_admin_approval_all():
    loop = _make_loop()
    result = loop._handle_admin_approval("APPROVE ALL")
    assert result is not None
    assert "ALL" in result or "all" in result.lower()
    # Every category must be pre-approved
    for cat in {"exec", "write", "git", "packages", "spawn"}:
        assert cat in loop.tools._pre_approved


def test_handle_admin_approval_case_insensitive():
    loop = _make_loop()
    result = loop._handle_admin_approval("approve Exec")
    assert result is not None
    assert "exec" in loop.tools._pre_approved


def test_handle_admin_approval_trims_whitespace():
    loop = _make_loop()
    result = loop._handle_admin_approval("  APPROVE   write  ")
    assert result is not None
    assert "write" in loop.tools._pre_approved


# ---------------------------------------------------------------------------
# Admin-channel intercept in _process_message
# ---------------------------------------------------------------------------


def _make_inbound(content: str, channel_role: str = "user", channel: str = "telegram") -> InboundMessage:
    return InboundMessage(
        channel=channel,
        sender_id="999",
        chat_id="999",
        content=content,
        metadata={"channel_role": channel_role},
    )


async def test_process_message_admin_channel_approve_bypasses_llm():
    """APPROVE exec from admin channel is handled without calling the LLM."""
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
        provider.chat = AsyncMock()  # Should not be called

        loop = AgentLoop(bus=bus, provider=provider, workspace=Path("/tmp/ws"))
        loop.tools = ToolRegistry()
        # Stub out session management
        mock_session = MagicMock()
        mock_session.metadata = {}
        mock_session.message_count = 0
        mock_session.last_consolidated = 0
        loop.sessions = MagicMock()
        loop.sessions.get_or_create.return_value = mock_session

        msg = _make_inbound("APPROVE exec", channel_role="admin")
        response = await loop._process_message(msg)

        # LLM should NOT have been called
        provider.chat.assert_not_awaited()

        # Registry should be pre-approved
        assert "exec" in loop.tools._pre_approved

        # Response should be an OutboundMessage
        assert response is not None
        assert isinstance(response, OutboundMessage)
        assert "exec" in response.content


async def test_process_message_user_channel_approve_goes_to_llm():
    """APPROVE exec from a user-role channel is NOT intercepted — goes to LLM."""
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

        # Minimal LLM response so the loop doesn't crash
        llm_response = MagicMock()
        llm_response.content = "Noted."
        llm_response.tool_calls = []
        llm_response.usage = {}
        provider.chat = AsyncMock(return_value=llm_response)

        loop = AgentLoop(bus=bus, provider=provider, workspace=Path("/tmp/ws"))
        loop.tools = ToolRegistry()
        mock_session = MagicMock()
        mock_session.metadata = {}
        mock_session.message_count = 0
        mock_session.last_consolidated = 0
        mock_session.get_history.return_value = []
        loop.sessions = MagicMock()
        loop.sessions.get_or_create.return_value = mock_session
        loop.context = MagicMock()
        loop.context.build_messages.return_value = [{"role": "user", "content": "APPROVE exec"}]

        msg = _make_inbound("APPROVE exec", channel_role="user")
        await loop._process_message(msg)

        # Registry must NOT be pre-approved (not intercepted)
        assert "exec" not in loop.tools._pre_approved
        # LLM should have been called
        provider.chat.assert_awaited()


# ---------------------------------------------------------------------------
# SB.1 regression checks (bug fixes wired in this session)
# ---------------------------------------------------------------------------


def test_agent_loop_registry_has_workspace():
    """ToolRegistry in AgentLoop is initialised with the workspace path."""
    from hive.agent.loop import AgentLoop
    from hive.agent.tools.registry import ToolRegistry

    workspace = Path("/tmp/test-hive-workspace")

    with (
        patch("hive.agent.loop.ContextBuilder"),
        patch("hive.agent.loop.SessionManager"),
        patch("hive.agent.loop.initialize_memory_hierarchy"),
        patch.object(AgentLoop, "_register_default_tools"),
    ):
        bus = MagicMock(spec=MessageBus)
        provider = MagicMock()
        provider.get_default_model.return_value = "test-model"

        loop = AgentLoop(bus=bus, provider=provider, workspace=workspace)

    assert isinstance(loop.tools, ToolRegistry)
    assert loop.tools._workspace == workspace


def test_agent_loop_registers_session_approve_tool():
    """SessionApproveTool is registered in the default tool set."""
    from hive.agent.loop import AgentLoop
    from hive.agent.tools.session_approve import SessionApproveTool

    with (
        patch("hive.agent.loop.ContextBuilder"),
        patch("hive.agent.loop.SessionManager"),
        patch("hive.agent.loop.initialize_memory_hierarchy"),
        # Do NOT mock _register_default_tools — we want the real registration
        patch("hive.agent.tools.docker_exec.DockerExecTool.is_available", return_value=False),
        patch("hive.agent.loop.CronTool"),  # cron_service is None, so CronTool won't register; mock to avoid import issues
    ):
        bus = MagicMock(spec=MessageBus)
        provider = MagicMock()
        provider.get_default_model.return_value = "test-model"

        loop = AgentLoop(bus=bus, provider=provider, workspace=Path("/tmp/ws"))

    tool = loop.tools.get("session_approve")
    assert tool is not None
    assert isinstance(tool, SessionApproveTool)


async def test_agent_loop_propagates_channel_role_to_tool_registry():
    """AgentLoop sets self.tools._channel_role from InboundMessage metadata."""
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
        # Dummy provider to prevent errors during message loop
        provider.chat = AsyncMock(return_value=MagicMock(content="Hello", tool_calls=[], usage={}))

        loop = AgentLoop(bus=bus, provider=provider, workspace=Path("/tmp/ws"))
        loop.tools = ToolRegistry()
        
        # Stub session management to not interfere
        mock_session = MagicMock()
        mock_session.metadata = {}
        mock_session.message_count = 0
        mock_session.last_consolidated = 0
        mock_session.get_history.return_value = []
        loop.sessions = MagicMock()
        loop.sessions.get_or_create.return_value = mock_session
        
        loop.context = MagicMock()
        loop.context.build_messages.return_value = [{"role": "user", "content": "hello"}]

        # 1. Admin role message
        msg_admin = _make_inbound("hello", channel_role="admin")
        await loop._process_message(msg_admin)
        assert loop.tools._channel_role == "admin"

        # 2. User role message
        msg_user = _make_inbound("ping", channel_role="user")
        await loop._process_message(msg_user)
        assert loop.tools._channel_role == "user"
