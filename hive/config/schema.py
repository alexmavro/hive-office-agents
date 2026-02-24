"""Configuration schema using Pydantic."""

from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, SecretStr
from pydantic_settings import BaseSettings


class WhatsAppConfig(BaseModel):
    """WhatsApp channel configuration."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    role: Literal["user", "admin", "notification"] = "user"  # SB.2: channel trust level
    bridge_url: str = "ws://localhost:3001"
    bridge_token: SecretStr = SecretStr("")  # Shared token for bridge auth (optional, recommended)
    allow_from: list[str] = Field(default_factory=list)  # Allowed phone numbers


class TelegramConfig(BaseModel):
    """Telegram channel configuration."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    role: Literal["user", "admin", "notification"] = "user"  # SB.2: channel trust level
    token: SecretStr = SecretStr("")  # Bot token from @BotFather
    allow_from: list[str] = Field(default_factory=list)  # Allowed user IDs or usernames
    proxy: str | None = None  # HTTP/SOCKS5 proxy URL, e.g. "http://127.0.0.1:7890" or "socks5://127.0.0.1:1080"
    notification_chat_id: str = ""  # Persistent target for proactive messages (user's Telegram chat ID)


class FeishuConfig(BaseModel):
    """Feishu/Lark channel configuration using WebSocket long connection."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    role: Literal["user", "admin", "notification"] = "user"  # SB.2: channel trust level
    app_id: str = ""  # App ID from Feishu Open Platform
    app_secret: SecretStr = SecretStr("")  # App Secret from Feishu Open Platform
    encrypt_key: SecretStr = SecretStr("")  # Encrypt Key for event subscription (optional)
    verification_token: SecretStr = SecretStr("")  # Verification Token for event subscription (optional)
    allow_from: list[str] = Field(default_factory=list)  # Allowed user open_ids


class DingTalkConfig(BaseModel):
    """DingTalk channel configuration using Stream mode."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    role: Literal["user", "admin", "notification"] = "user"  # SB.2: channel trust level
    client_id: str = ""  # AppKey
    client_secret: SecretStr = SecretStr("")  # AppSecret
    allow_from: list[str] = Field(default_factory=list)  # Allowed staff_ids


class DiscordConfig(BaseModel):
    """Discord channel configuration."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    role: Literal["user", "admin", "notification"] = "user"  # SB.2: default role for all channels
    token: SecretStr = SecretStr("")  # Bot token from Discord Developer Portal
    allow_from: list[str] = Field(default_factory=list)  # Allowed user IDs
    gateway_url: str = "wss://gateway.discord.gg/?v=10&encoding=json"
    intents: int = 37377  # GUILDS + GUILD_MESSAGES + DIRECT_MESSAGES + MESSAGE_CONTENT
    notification_chat_id: str = ""  # Persistent target for proactive messages (a Discord channel ID)
    channel_routes: dict[str, Literal["user", "admin", "notification"]] = Field(
        default_factory=dict,
        description=(
            "Per Discord-channel role overrides. Key = Discord channel ID (string), "
            "value = role. Overrides the top-level 'role' for that specific channel. "
            "Notification channels are outbound-only — inbound messages are dropped."
        ),
    )

class EmailConfig(BaseModel):
    """Email channel configuration (IMAP inbound + SMTP outbound)."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    role: Literal["user", "admin", "notification"] = "user"  # SB.2: channel trust level
    consent_granted: bool = False  # Explicit owner permission to access mailbox data

    # IMAP (receive)
    imap_host: str = ""
    imap_port: int = Field(993, ge=1, le=65535)
    imap_username: str = ""
    imap_password: SecretStr = SecretStr("")
    imap_mailbox: str = "INBOX"
    imap_use_ssl: bool = True

    # SMTP (send)
    smtp_host: str = ""
    smtp_port: int = Field(587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    from_address: str = ""

    # Behavior
    auto_reply_enabled: bool = True  # If false, inbound email is read but no automatic reply is sent
    poll_interval_seconds: int = Field(30, ge=5, le=3600)
    mark_seen: bool = True
    max_body_chars: int = Field(12000, ge=100, le=1000000)
    subject_prefix: str = "Re: "
    allow_from: list[str] = Field(default_factory=list)  # Allowed sender email addresses


class MochatMentionConfig(BaseModel):
    """Mochat mention behavior configuration."""
    require_in_groups: bool = False


class MochatGroupRule(BaseModel):
    """Mochat per-group mention requirement."""
    require_mention: bool = False


class MochatConfig(BaseModel):
    """Mochat channel configuration."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    role: Literal["user", "admin", "notification"] = "user"  # SB.2: channel trust level
    base_url: str = "https://mochat.io"
    socket_url: str = ""
    socket_path: str = "/socket.io"
    socket_disable_msgpack: bool = False
    socket_reconnect_delay_ms: int = 1000
    socket_max_reconnect_delay_ms: int = 10000
    socket_connect_timeout_ms: int = 10000
    refresh_interval_ms: int = 30000
    watch_timeout_ms: int = 25000
    watch_limit: int = 100
    retry_delay_ms: int = 500
    max_retry_attempts: int = 0  # 0 means unlimited retries
    claw_token: SecretStr = SecretStr("")
    agent_user_id: str = ""
    sessions: list[str] = Field(default_factory=list)
    panels: list[str] = Field(default_factory=list)
    allow_from: list[str] = Field(default_factory=list)
    mention: MochatMentionConfig = Field(default_factory=MochatMentionConfig)
    groups: dict[str, MochatGroupRule] = Field(default_factory=dict)
    reply_delay_mode: Literal["off", "non-mention"] = "non-mention"
    reply_delay_ms: int = 120000


class SlackDMConfig(BaseModel):
    """Slack DM policy configuration."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = True
    policy: Literal["open", "allowlist"] = "open"
    allow_from: list[str] = Field(default_factory=list)  # Allowed Slack user IDs


class SlackConfig(BaseModel):
    """Slack channel configuration."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    role: Literal["user", "admin", "notification"] = "user"  # SB.2: channel trust level
    mode: Literal["socket"] = "socket"
    webhook_path: str = "/slack/events"
    bot_token: SecretStr = SecretStr("")  # xoxb-...
    app_token: SecretStr = SecretStr("")  # xapp-...
    user_token_read_only: bool = True
    group_policy: Literal["mention", "open", "allowlist"] = "mention"
    group_allow_from: list[str] = Field(default_factory=list)  # Allowed channel IDs if allowlist
    dm: SlackDMConfig = Field(default_factory=SlackDMConfig)


class QQConfig(BaseModel):
    """QQ channel configuration using botpy SDK."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    role: Literal["user", "admin", "notification"] = "user"  # SB.2: channel trust level
    app_id: str = ""  # 机器人 ID (AppID) from q.qq.com
    secret: SecretStr = SecretStr("")  # 机器人密钥 (AppSecret) from q.qq.com
    allow_from: list[str] = Field(default_factory=list)  # Allowed user openids (empty = public access)


class ChannelsConfig(BaseModel):
    """Configuration for chat channels."""
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    mochat: MochatConfig = Field(default_factory=MochatConfig)
    dingtalk: DingTalkConfig = Field(default_factory=DingTalkConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    qq: QQConfig = Field(default_factory=QQConfig)


class AgentDefaults(BaseModel):
    """Default agent configuration."""
    model_config = ConfigDict(extra='forbid')
    workspace: str = "~/.hive/workspace"
    model: str = "anthropic/claude-opus-4-5"
    max_tokens: int = Field(8192, ge=1, le=200000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    fallbacks: list[str] = Field(default_factory=list)
    max_tool_iterations: int = Field(20, ge=1, le=200)
    memory_window: int = Field(50, ge=1, le=10000)
    daily_usd_budget: float = Field(10.0, ge=0.0, description="Global daily USD budget for all LLM calls")


class WorkersConfig(BaseModel):
    """Worker sub-agent configuration."""
    model_config = ConfigDict(extra='forbid')
    max_active_workers: int = Field(5, ge=1, le=20)
    max_worker_iterations: int = Field(15, ge=1, le=50)
    worker_usd_limit: float = Field(0.50, ge=0.0, description="Max USD budget per individual worker run")


class AgentsConfig(BaseModel):
    """Agent configuration."""
    defaults: AgentDefaults = Field(default_factory=AgentDefaults)
    workers: WorkersConfig = Field(default_factory=WorkersConfig)


class ProviderConfig(BaseModel):
    """LLM provider configuration."""
    api_key: SecretStr = SecretStr("")
    api_base: str | None = None
    extra_headers: dict[str, str] | None = None  # Custom headers (e.g. APP-Code for AiHubMix)


class ProvidersConfig(BaseModel):
    """Configuration for LLM providers."""
    custom: ProviderConfig = Field(default_factory=ProviderConfig)  # Any OpenAI-compatible endpoint
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)
    deepseek: ProviderConfig = Field(default_factory=ProviderConfig)
    groq: ProviderConfig = Field(default_factory=ProviderConfig)
    zhipu: ProviderConfig = Field(default_factory=ProviderConfig)
    dashscope: ProviderConfig = Field(default_factory=ProviderConfig)  # 阿里云通义千问
    vllm: ProviderConfig = Field(default_factory=ProviderConfig)
    gemini: ProviderConfig = Field(default_factory=ProviderConfig)
    moonshot: ProviderConfig = Field(default_factory=ProviderConfig)
    minimax: ProviderConfig = Field(default_factory=ProviderConfig)
    aihubmix: ProviderConfig = Field(default_factory=ProviderConfig)  # AiHubMix API gateway
    github_copilot: ProviderConfig = Field(default_factory=ProviderConfig)  # Github Copilot (OAuth)


class GatewayConfig(BaseModel):
    """Gateway/server configuration."""
    model_config = ConfigDict(extra='forbid')
    host: str = "0.0.0.0"
    port: int = Field(18790, ge=1, le=65535)


class WebSearchConfig(BaseModel):
    """Web search tool configuration."""
    model_config = ConfigDict(extra='forbid')
    api_key: SecretStr = SecretStr("")  # Brave Search API key
    max_results: int = 5


class WebToolsConfig(BaseModel):
    """Web tools configuration."""
    model_config = ConfigDict(extra='forbid')
    search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class ExecToolConfig(BaseModel):
    """Shell exec tool configuration."""
    model_config = ConfigDict(extra='forbid')
    timeout: int = 60


class ApprovalConfig(BaseModel):
    """Approval gate configuration (SB.1 — Security Boundaries).

    Controls the ToolRegistry tiered permission gate. The gate fires at
    execution time for every tool call. Tier 0 is always hard-rejected.
    Tier 1 requires session pre-approval or SB.2 admin-channel YES.
    Tier 2 is always free.
    """
    enabled: bool = True
    timeout_seconds: float = 300.0  # reserved for SB.2 async approval (5-min default)


class MCPServerConfig(BaseModel):
    """MCP server connection configuration (stdio or HTTP)."""
    command: str = ""  # Stdio: command to run (e.g. "npx")
    args: list[str] = Field(default_factory=list)  # Stdio: command arguments
    env: dict[str, SecretStr] = Field(default_factory=dict)  # Stdio: extra env vars
    url: str = ""  # HTTP: streamable HTTP endpoint URL


class ToolsConfig(BaseModel):
    """Tools configuration."""
    web: WebToolsConfig = Field(default_factory=WebToolsConfig)
    exec: ExecToolConfig = Field(default_factory=ExecToolConfig)
    restrict_to_workspace: bool = False  # If true, restrict all tool access to workspace directory
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)  # SB.1 gate config


class AuditConfig(BaseModel):
    """Structured audit log configuration.

    Audit logging captures system events (tool calls, LLM calls, channel metadata,
    gateway lifecycle) to JSONL files for transparency and retrospective analysis.

    IMPORTANT: This logs system events only — not personal data.
    See STATUS.md (SA section) for future reworks required before public deployment.
    """
    model_config = ConfigDict(extra='forbid')
    enabled: bool = True
    retention_days: int = Field(30, ge=1, le=3650)       # Days before active logs are moved to archive/
    max_size_gb: float = Field(5.0, ge=0.1, le=1000.0)       # Queen flags user when total size exceeds this
    report_hour: int = Field(9, ge=0, le=23)           # UTC hour to generate daily MD report (SA.3)


class Config(BaseSettings):
    """Root configuration for hive."""
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    
    @property
    def workspace_path(self) -> Path:
        """Get expanded workspace path."""
        return Path(self.agents.defaults.workspace).expanduser()
    
    def _match_provider(self, model: str | None = None) -> tuple["ProviderConfig | None", str | None]:
        """Match provider config and its registry name. Returns (config, spec_name)."""
        from hive.providers.registry import PROVIDERS
        model_lower = (model or self.agents.defaults.model).lower()

        # Match by keyword (order follows PROVIDERS registry)
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and any(kw in model_lower for kw in spec.keywords):
                if spec.is_oauth or p.api_key.get_secret_value():
                    return p, spec.name

        # Fallback: gateways first, then others (follows registry order)
        # OAuth providers are NOT valid fallbacks — they require explicit model selection
        for spec in PROVIDERS:
            if spec.is_oauth:
                continue
            p = getattr(self.providers, spec.name, None)
            if p and p.api_key.get_secret_value():
                return p, spec.name
        return None, None

    def get_provider(self, model: str | None = None) -> ProviderConfig | None:
        """Get matched provider config (api_key, api_base, extra_headers). Falls back to first available."""
        p, _ = self._match_provider(model)
        return p

    def get_provider_name(self, model: str | None = None) -> str | None:
        """Get the registry name of the matched provider (e.g. "deepseek", "openrouter")."""
        _, name = self._match_provider(model)
        return name

    def get_api_key(self, model: str | None = None) -> str | None:
        """Get API key for the given model. Falls back to first available key."""
        p = self.get_provider(model)
        if not p:
            return None
        secret = p.api_key.get_secret_value()
        return secret if secret else None
    
    def get_api_base(self, model: str | None = None) -> str | None:
        """Get API base URL for the given model. Applies default URLs for known gateways."""
        from hive.providers.registry import find_by_name
        p, name = self._match_provider(model)
        if p and p.api_base:
            return p.api_base
        # Only gateways get a default api_base here. Standard providers
        # (like Moonshot) set their base URL via env vars in _setup_env
        # to avoid polluting the global litellm.api_base.
        if name:
            spec = find_by_name(name)
            if spec and spec.is_gateway and spec.default_api_base:
                return spec.default_api_base
        return None
    
    model_config = ConfigDict(
        env_prefix="HIVE_",
        env_nested_delimiter="__"
    )
