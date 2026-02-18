# hive-office-agents — Project Knowledge Base

## Project Identity

**hive-office-agents** — autonomous AI agents for VPS management.
The first agent is the **Queen** — she will own and operate this server.

Built on **nanobot** v0.1.3.post7 (see [NANOBOT_BASELINE.md](NANOBOT_BASELINE.md) for upstream attribution).
GitHub: `Lexi-Energy/hive-office-agents` (private)

## Repository Layout

```
/root/queen-alpha/                 # Project root
├── nanobot/                       # Core Python package (from nanobot upstream, 3,668 lines)
│   ├── agent/                     # Agent loop, context builder, memory, skills, subagents
│   │   ├── loop.py                # ReAct loop (LLM <-> tool execution, max 20 iterations)
│   │   ├── context.py             # System prompt assembly (SOUL/AGENTS/USER.md + memory + skills)
│   │   ├── memory.py              # Two-layer: MEMORY.md (facts) + HISTORY.md (event log)
│   │   ├── skills.py              # Progressive skill loader (always-loaded vs on-demand)
│   │   ├── subagent.py            # Background task execution in isolated contexts
│   │   └── tools/                 # Built-in tools (registry, filesystem, shell, web, message, spawn, cron, mcp)
│   ├── channels/                  # 9 chat integrations (telegram, whatsapp, discord, slack, email, feishu, qq, dingtalk, mochat)
│   ├── bus/                       # Async pub/sub message routing (inbound/outbound queues)
│   ├── config/                    # Pydantic config models + JSON loader
│   ├── providers/                 # 16 LLM providers via LiteLLM
│   ├── cron/                      # Scheduled task service (at/every/cron)
│   ├── heartbeat/                 # Proactive agent wake-up (HEARTBEAT.md every 30 min)
│   ├── session/                   # JSONL conversation storage
│   ├── skills/                    # Bundled skills (github, weather, tmux, summarize, etc.)
│   ├── cli/                       # Typer CLI (onboard, agent, gateway, status, channels, cron)
│   └── utils/                     # Shared utilities
├── bridge/                        # WhatsApp bridge (TypeScript/Node.js, Baileys)
├── workspace/                     # Template workspace files (copied to ~/.nanobot/workspace/)
├── tests/                         # pytest suite (55 tests)
├── pyproject.toml                 # Package: hive-office-agents v0.1.0
├── Dockerfile                     # Container build (uv + Node.js 20)
├── NANOBOT_BASELINE.md            # Upstream nanobot attribution & snapshot info
└── CLAUDE.md                      # This file — project knowledge for Claude Code
```

## Environment (Verified 2026-02-18)

| Component | Version / Path | Status |
|-----------|---------------|--------|
| OS | Linux 6.8.0-100-generic (Ubuntu) | Running |
| Python | 3.12.3 | System |
| Virtual env | `/root/queen-alpha/.venv/` | All deps installed (editable mode) |
| Node.js | 20.20.0 | Working |
| npm | 10.8.2 | Working |
| nanobot CLI | `nanobot` (via `pip install -e ".[dev]"`) | Working |
| Config | `~/.nanobot/config.json` | Initialized via `nanobot onboard` |
| Workspace | `~/.nanobot/workspace/` | Created (AGENTS.md, SOUL.md, USER.md, memory/) |
| WhatsApp bridge | `/root/queen-alpha/bridge/dist/` | Built, 0 vulnerabilities |
| Test suite | 55/55 passed | All green |
| GitHub CLI | `gh` authenticated as Lexi-Energy | Working |
| Repo | `Lexi-Energy/hive-office-agents` (private) | Pushed |

## How to Activate

```bash
source /root/queen-alpha/.venv/bin/activate
```

## Architecture Quick Reference

### Data Flow
```
Channel -> InboundMessage -> Bus -> Agent Loop -> LLM -> Tool Exec -> OutboundMessage -> Bus -> Channel
```

### Key Systems
- **Agent Loop** (`agent/loop.py`): ReAct pattern, 20 iter cap, auto memory consolidation at 50 msgs
- **Memory** (`agent/memory.py`): MEMORY.md (LLM-updated facts) + HISTORY.md (append-only event log)
- **Context** (`agent/context.py`): Assembles system prompt from bootstrap files + memory + skills
- **Providers** (`providers/registry.py`): 16 providers via ProviderSpec, LiteLLM routing
- **Tools** (`agent/tools/`): exec, read/write/edit_file, list_dir, web_search/fetch, message, spawn, cron, MCP
- **Skills** (`agent/skills.py`): YAML frontmatter, progressive loading, dependency checking
- **Channels** (`channels/`): Abstract base, ChannelManager dispatches outbound

### Config
`~/.nanobot/config.json` — sections: `agents`, `channels`, `providers`, `gateway`, `tools`

## What's Done

- [x] Base nanobot codebase explored and understood
- [x] All Python + Node.js dependencies installed
- [x] WhatsApp bridge built
- [x] 55/55 tests passing
- [x] Own git repo initialized (clean history)
- [x] GitHub repo created (Lexi-Energy/hive-office-agents, private)
- [x] Upstream attribution documented (NANOBOT_BASELINE.md)
- [x] Project renamed to hive-office-agents

## What's Next

- [ ] Configure an LLM provider (API key in ~/.nanobot/config.json)
- [ ] Shape Queen identity (SOUL.md, AGENTS.md, USER.md)
- [ ] Define VPS management capabilities and custom skills
- [ ] Set up communication channels (Telegram, Discord, etc.)
- [ ] Security hardening for production operation

## Commands Reference

```bash
nanobot onboard           # Initialize config & workspace
nanobot agent             # Interactive chat
nanobot agent -m "..."    # Single message
nanobot gateway           # Start gateway (channels + cron + heartbeat)
nanobot status            # Show config status
nanobot channels status   # Show channel status
nanobot cron list         # List scheduled jobs
```
