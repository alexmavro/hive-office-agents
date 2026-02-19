# hive-office-agents

Autonomous AI agent system. **The Queen manages. Workers execute.**

Built for real office work: Telegram-native, security-first, cost-aware. Running 24/7 on a VPS.

> **For full project context:** see [CLAUDE.md](CLAUDE.md)
> **Build status & decisions:** see [STATUS.md](STATUS.md)

---

## Quick Start

```bash
source /root/queen-alpha/.venv/bin/activate
```

**Start the gateway** (Telegram + cron + heartbeat):

```bash
nohup hive gateway >> /root/queen-alpha/gateway.log 2>&1 &
sleep 4 && tail -20 /root/queen-alpha/gateway.log
```

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `hive gateway` | Start gateway (channels + cron + heartbeat) |
| `hive agent` | Interactive terminal chat |
| `hive agent -m "..."` | Single message |
| `hive onboard` | Initialize config & workspace |
| `hive status` | Show config & provider status |
| `hive channels status` | Show channel connection status |
| `hive cron list` | List scheduled jobs |
| `hive cron add` | Add a scheduled job |

---

## Configuration

```
~/.hive/config.json        # API keys, bot token, channel config — chmod 600
~/.hive/workspace/         # Queen's working directory (SOUL.md, memory/, skills/)
~/.hive/sessions/          # Conversation history (JSONL DAG)
```

Minimal config example:

```json
{
  "providers": {
    "gemini": { "apiKey": "YOUR_GEMINI_KEY" }
  },
  "agents": {
    "defaults": { "model": "gemini/gemini-3-pro-preview", "maxTokens": 65536 }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

---

## Architecture

```
Hive-Queen  (LAW, root, crowned)
├── Workers
│   ├── Temps       — ephemeral, spawned per task, auto-terminated  (S4)
│   └── Consorts    — stateful, promoted temps, long-lived          (S4)
└── Hive-Teams      — multi-worker collaborative workflows          (post-S7)
```

Data flow:
```
Channel → Bus → Agent Loop → LLM → Tool Exec → Bus → Channel
```

**Execution layers:**
- `exec` — host shell (Queen only, root access)
- `docker_exec` — sandboxed code (AST filter + ephemeral container, 512MB/1CPU)

---

## Project Structure

```
hive/
├── agent/        # Loop, context, memory, retrieval, consolidation, onboarding, tools/
├── channels/     # Telegram (active) + 8 integrations (future)
├── bus/          # Async pub/sub message routing
├── config/       # Pydantic config models
├── providers/    # LLM providers via LiteLLM
├── cron/         # Scheduled task service
├── heartbeat/    # Proactive agent wake-up
├── session/      # JSONL DAG conversation storage
├── skills/       # Bundled skills (github, weather, tmux, ...)
└── cli/          # hive CLI

workspace/        # Template workspace files (SOUL.md, AGENTS.md)
templates/memory/ # Memory hierarchy templates
bridge/           # WhatsApp bridge (TypeScript/Node.js — deprioritized)
```

---

## Tests

```bash
pytest tests/             # All tests
pytest -m "not docker"    # Skip tests requiring the hive-worker Docker image
```

Build the Docker image for sandbox tests:
```bash
docker build -f worker.Dockerfile -t hive-worker:latest .
```

---

## Build Status

| Step | Goal | Status |
|------|------|--------|
| S0 | Scaffold + Telegram | ✅ Complete |
| S1 | JSONL DAG memory | ✅ Complete |
| S2 | Memory architecture | ✅ Complete — 182 tests |
| S3 | Docker executor | ✅ Complete — 257 tests |
| **S4** | **Hive Manager (worker spawning)** | **Next** |
| S5 | Skill forge | Not started |
| S6 | Safety rails | Not started |
| S7 | Emission stream | Not started |

---

## Attribution

Built on [nanobot](https://github.com/HKUDS/nanobot) v0.1.3.post7 (MIT License).
See [NANOBOT_BASELINE.md](NANOBOT_BASELINE.md) for upstream attribution details.
