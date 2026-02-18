# hive-office-agents — Project Knowledge Base

## Project Identity

**hive-office-agents** — autonomous AI agents for VPS management.
The first agent is the **Queen** — she will own and operate this server.

Built on **nanobot** v0.1.3.post7 (see [NANOBOT_BASELINE.md](NANOBOT_BASELINE.md) for upstream attribution).
GitHub: `Lexi-Energy/hive-office-agents` (private)

## How We Work

**This is an agile project.** The build plan (see below) is a living document, not a contract.
- The plan gets amended whenever we learn something that changes the approach
- The builder (Claude Code) is ALWAYS free to suggest different approaches
- Daily recap and test sessions are the checkpoint for plan adjustments
- Alex (the user) tests via Telegram for experience quality; Claude Code tests via pytest for correctness
- Two-layer testing protocol: see `docs/hive_office_test_protocol.md`

## Constraints

- Do NOT rewrite nanobot's core loop. Extend it.
- Do NOT introduce heavy dependencies (no LangChain, no CrewAI, no vector DBs).
- Keep new files under 300 lines each.
- Use nanobot's existing skill system for new tools.
- All file IPC uses write-then-rename pattern (atomic writes).
- Never say "I fixed it" unless you verified the output.
- Scripts must survive re-runs (idempotency).
- No temp files left behind after any task.

## Commit Discipline

- One commit per logical change
- Message format: `SX.Y: description` (e.g., `S1.2: implement get_path traversal`)
- Gate commits at phase boundaries: `SX GATE: description`
- Snapshots (git tags) at critical milestones: `queen-alpha_SX_name`

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
│   ├── channels/                  # 9 chat integrations (telegram, whatsapp, discord, slack, email, etc.)
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
├── docs/                          # Planning & reference documents
│   ├── hive_office_revised_plan_v03.md    # Build plan (S0-S7)
│   ├── hive_office_test_protocol.md       # Two-layer testing protocol
│   ├── PIMONO_DAG_REFERENCE_v2.md         # JSONL DAG spec + Python port code (for S1)
│   └── hive_office_brainstorm_archive.md  # Archived vision docs (not actionable)
├── workspace/                     # Template workspace files (copied to ~/.nanobot/workspace/)
├── tests/                         # pytest suite (55 tests)
├── pyproject.toml                 # Package: hive-office-agents v0.1.0
├── Dockerfile                     # Container build (uv + Node.js 20)
├── NANOBOT_BASELINE.md            # Upstream nanobot attribution & snapshot info
├── STATUS.md                      # Current build progress, blockers, decisions
└── CLAUDE.md                      # This file
```

## Build Plan (S0–S7)

Full details in `docs/hive_office_revised_plan_v03.md`. Summary:

### Dependency Chain
```
S0 (scaffold + Telegram)
 |
S1 (DAG memory) <-- everything depends on this
 |
 +-- S2 (identity + diagnostic commands)
 |
 +-- S5 (skill forge) -- can run parallel with S3/S4
 |
S3 (Docker executor)
 |
S4 (hive manager) <-- depends on S3
 |
S6 (safety rails) <-- depends on S1
 |
S7 (emission stream) <-- last, needs everything stable
```

### Step Status

| Step | Goal | Status |
|------|------|--------|
| **S0** | Scaffold + Telegram verified | **In progress** — repo done, deps installed, tests green. Telegram + LLM provider not yet configured. |
| **S1** | JSONL DAG memory (replace HISTORY.md) | Not started. Spec ready in `docs/PIMONO_DAG_REFERENCE_v2.md`. |
| **S2** | Identity/persona + Telegram diagnostics (/status /tree /budget /workers /health) | Not started |
| **S3** | Docker executor (sandboxed Python execution, AST filter) | Not started |
| **S4** | Hive manager (worker spawning, IPC, registry) | Not started. Depends on S3. |
| **S5** | Skill forge (Queen creates her own tools) | Not started. Can parallel S3/S4. |
| **S6** | Safety rails (circuit breaker, budget gate, depth limits) | Not started. Depends on S1. |
| **S7** | Emission stream (WebSocket live observation) | Not started. Last step. |

### Model Strategy

| Role | Model | Notes |
|------|-------|-------|
| Builder (Claude Code) | Claude Opus via subscription | Architecture work |
| Queen (dev/test) | Gemini 2.0 Flash via API | EUR 200 in credits, fast + cheap |
| Queen (production) | Gemini 2.5 Pro or Claude Sonnet | Upgrade when stable |
| Workers | Gemini Flash or Haiku via OpenRouter | Narrow tasks, small models |

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
| Git identity | Lexi-Energy (noreply email) | Configured |

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
- **Agent Loop** (`nanobot/agent/loop.py`): ReAct pattern, 20 iter cap, auto memory consolidation at 50 msgs
- **Memory** (`nanobot/agent/memory.py`): MEMORY.md (LLM-updated facts) + HISTORY.md (event log) — HISTORY.md will be replaced by DAG in S1
- **Context** (`nanobot/agent/context.py`): Assembles system prompt from bootstrap files + memory + skills
- **Providers** (`nanobot/providers/registry.py`): 16 providers via ProviderSpec, LiteLLM routing
- **Tools** (`nanobot/agent/tools/`): exec, read/write/edit_file, list_dir, web_search/fetch, message, spawn, cron, MCP
- **Skills** (`nanobot/agent/skills.py`): YAML frontmatter, progressive loading, dependency checking
- **Channels** (`nanobot/channels/`): Abstract base, ChannelManager dispatches outbound

### Config
`~/.nanobot/config.json` — sections: `agents`, `channels`, `providers`, `gateway`, `tools`

## Reference Documents

| Document | When to read |
|----------|-------------|
| `docs/PIMONO_DAG_REFERENCE_v2.md` | Before starting S1. Full Python port code for JSONL DAG. |
| `docs/hive_office_test_protocol.md` | Before every step. Two-layer testing (automated + Alex via Telegram). |
| `docs/hive_office_revised_plan_v03.md` | The build plan. Living document. |
| `docs/hive_office_brainstorm_archive.md` | Future ideas only. Not actionable unless directed. |

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
