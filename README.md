# hive-office-agents

Autonomous AI agent system. **The Queen manages. Workers execute.**

Running 24/7 on a VPS. Multi-channel (Discord, Telegram, CLI). Security-first. Cost-aware.

---

## Quick Start

The gateway runs as a supervised systemd service.

```bash
# Restart & check logs
sudo systemctl restart hive-gateway
journalctl -u hive-gateway -n 20 --no-pager
```

---

## How to Interact

The Queen is your manager, not a task-bot. Use Telegram or Discord to give her high-level objectives.

- **Workers:** She spawns background workers for heavy tasks. Talk to the Queen — not the workers.
- **Approvals:** Gated actions (like host commands) require `APPROVE <category>` from your `admin` channel.
- **Isolation:** Each channel/chat gets its own isolated memory project automatically.

---

## CLI Reference

| Command | Description |
|---|---|
| `hive gateway` | Start gateway (channels + cron + heartbeat) |
| `hive agent` | Interactive terminal chat |
| `hive agent -m "..."` | Single message |
| `hive onboard` | Initialize config & workspace |
| `hive status` | Show config & provider status |
| `hive channels status` | Show channel connection status |
| `hive cron list` | List scheduled jobs |

---

## Configuration

```
~/.hive/config.json        # API keys, bot tokens, channel config — chmod 600
~/.hive/workspace/         # Queen's working directory (SOUL.md, memory/, skills/)
~/.hive/sessions/          # Conversation history (JSONL DAG)
```

Minimal config:
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

## Tests

```bash
# Full unit suite
pytest tests/ --ignore=tests/integration

# Skip Docker sandbox tests
pytest -m "not docker"

# E2E tests (hits real Gemini API, slow)
pytest tests/integration/
```

Build the worker Docker image (needed for sandbox tests):
```bash
docker build -f worker.Dockerfile -t hive-worker:latest .
```

---

## Build Status

| Milestone | Description | Status |
|---|---|---|
| S0 | Scaffold + Telegram | ✅ Complete |
| S1 | JSONL DAG memory | ✅ Complete |
| S2 | Memory architecture | ✅ Complete |
| S3 | Docker executor | ✅ Complete |
| SA | Audit layer | ✅ Complete |
| SB | Security Boundaries | ✅ Complete |
| S4 | Hive Manager (worker spawning) | ✅ Complete |
| S5 | Skill Forge | ✅ Complete |
| S6 | Safety Rails | ✅ Complete |
| **S7** | **Emission stream** | **🔲 Next** |

504/504 tests passing · Phase 1 closes at S7.

---

## Developer Docs

| Document | Purpose |
|---|---|
| [ANTIGRAVITY.md](ANTIGRAVITY.md) | **Read first** — builder entry point, NO-GO list, architecture, all lessons |
| [VISION.md](VISION.md) | Product vision, architecture, design philosophy |
| [STATUS.md](STATUS.md) | Living roadmap — current build state, next steps |
| [SECURITY.md](SECURITY.md) | Security architecture reference |
| [HISTORY.md](HISTORY.md) | Build narrative — decisions and lessons per milestone |
