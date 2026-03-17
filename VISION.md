# VISION.md — Hive-Office Agents

**Last updated:** 2026-02-25
**Read this when:** You want to understand what we're building, why, and what the rules of the machine are.
**For current build status and roadmap → see [STATUS.md](STATUS.md)**
**For security architecture → see [SECURITY.md](SECURITY.md)**
**For builder lessons and traps → see [ANTIGRAVITY.md](ANTIGRAVITY.md)**

---

## What We're Building

**hive-office-agents** — an autonomous AI agent system. A Hive.

> The Queen manages. Workers execute.

Not "OpenClaw but Python." What OpenClaw should have been:

- **Security-first**: AST filter + Docker isolation. OpenClaw has a known RCE (Feb 2026). We don't.
- **Quality over volume**: 10 battle-tested skills > 1,700 unvetted. Queen writes her own.
- **3 channels that work perfectly** > 15 that sort-of work (Discord, Telegram, CLI — more when right)
- **Safety Rails**: Token tracking, USD budget gates, SHA256 circuit breakers. No surprise bills.
- **Modular and packageable**: each layer is independently deployable and replaceable.

**Strategy:**
- Phase 1 = match OpenClaw core (S0-S7). Foundation.
- Phase 2 = exceed on workflows (A/B/HT tracks — real office work).
- Phase 3 = open the tool format.
- Phase 4 = network effects.

Reference: `docs-alex-vision-DO_NOT_EDIT_READ_ONLY/`

---

## Architecture

```
Hive-Queen  (LAW, root, crowned)
├── Hive-Teams  (highest class — specialised multi-worker collaborative workflows)
│   ├── Research-Team   (STORM-powered, multi-source, cited articles)
│   ├── Writing-Team    (co-writer-hive integration, RAG-powered content)
│   └── ... (each team = defined workflow + team-level learning)
├── Workers
│   ├── Temps       — ephemeral. Queen spawns → executes → dies.
│   └── Consorts    — stateful. Promoted temps. Long-term domain specialists.
└── Skill Forge (S5)
    └── Queen creates reusable skills → saved to ~/.hive/workspace/skills/
```

**The Queen is a manager, not a worker.** She plans, delegates, quality-checks, learns, and is user-centric — not task-focused. This distinction is fundamental. Without it, it's just a chatbot.

**Queen's explicit responsibilities:**
- Delegates all execution — does not do heavy work herself
- QA and fact-checks all output from workers and teams
- Pauses/kills workers when server resources demand it
- Proactively notifies user of worker status — never makes them ask "what's happening?"
- Future: token budget monitoring, flow integrity checks, suggests better approaches

---

## Data Flow

```
Channel → InboundMessage → Bus → Agent Loop → LLM → Tool Exec → OutboundMessage → Bus → Channel
```

**Execution layers (two distinct things):**

| Mode | Tool | What | When |
|---|---|---|---|
| Host shell (root) | `exec` | System commands, hive CLI, restart | Queen only. Every call is gated. |
| Isolated sandbox | `docker_exec` | Code, pip install, file processing | Workers + Queen. Container IS the gate. |

`exec` runs as root on the live host. Mistakes are permanent.
`docker_exec` runs in a fresh ephemeral container. Kill it, rerun it, nothing changes on the host.

---

## Core vs Personal Data

Before building anything, ask: **would a factory reset erase this? Does it change per deployment?**

| Thing | Type | Location |
|---|---|---|
| Queen's type ("Hive Queen") | Core | `workspace/SOUL.md` |
| Queen's personal name (user-given) | Personal data | `memory/identity/user.md` |
| Operational rules | Core | `workspace/SOUL.md` |
| User's name, preferences, constraints | Personal data | `memory/identity/` |
| Memory hierarchy templates | Core | `templates/memory/` |
| Memory hierarchy content | Personal data | `~/.hive/workspace/memory/` |
| Tool definitions | Core | `hive/agent/tools/` |
| System-bundled skills | Core | `hive/skills/` |
| User-created / Queen-written skills | Personal data | `~/.hive/workspace/skills/` |
| Session history | Personal data | `~/.hive/sessions/` |
| API keys, bot tokens | Personal data | `~/.hive/config.json` |

**Principle:** Core ships with every Queen instance. Personal data belongs to the user and wipes cleanly.

---

## Server Layout

```
/root/
├── queen-alpha/                   # ← GIT REPO (the codebase)
│   ├── hive/                      # Core Python package
│   │   ├── agent/                 # loop.py, context.py, memory.py, retrieval.py,
│   │   │                          #   consolidation.py, onboarding.py, admin.py,
│   │   │                          #   skills.py, audit.py, budget.py, circuit_breaker.py
│   │   │                          #   tools/ (exec, docker_exec, spawn, web, file, etc.)
│   │   ├── channels/              # 9 chat integrations (telegram, discord, etc.)
│   │   ├── bus/                   # Async pub/sub message routing
│   │   ├── config/                # Pydantic config models + JSON loader
│   │   ├── providers/             # LLM providers via LiteLLM
│   │   ├── cron/                  # Scheduled task service
│   │   ├── heartbeat/             # Proactive agent wake-up
│   │   ├── session/               # JSONL DAG conversation storage
│   │   ├── skills/                # Bundled skills (github, weather, tmux, etc.)
│   │   └── cli/                   # hive CLI
│   ├── templates/                 # Memory hierarchy templates (no user data)
│   ├── workspace/                 # Template workspace (SOUL.md, AGENTS.md, TOOLS.md)
│   ├── tests/                     # pytest suite (504 tests as of 2026-02-25)
│   ├── ANTIGRAVITY.md             # ← READ THIS FIRST (builder entry point)
│   ├── VISION.md                  # This file — product vision and architecture
│   ├── STATUS.md                  # Living roadmap — current build state
│   └── SECURITY.md                # Security architecture reference
│
├── .hive/                         # ← RUNTIME DATA (back up manually)
│   ├── config.json                # API keys, bot token, channel config (chmod 600)
│   ├── sessions/                  # Conversation history (JSONL DAG)
│   ├── logs/
│   │   ├── audit/                 # YYYY-MM-DD.jsonl — structured event log (SA)
│   │   └── reports/               # YYYY-MM-DD.md — daily audit summaries
│   └── workspace/                 # Queen's working directory
│       ├── SOUL.md, AGENTS.md     # Core behavior rules
│       ├── memory/                # Everything the Queen knows
│       │   ├── identity/          # user.md, constraints.md, preferences.md
│       │   ├── systems/           # infrastructure.md, tools.md
│       │   ├── projects/          # per-channel working memory
│       │   ├── procedural/        # workflows/ and fixes/
│       │   ├── lessons/           # failures.md, patterns.md, corrections.md
│       │   └── skills/            # skills_registry.json
│       └── skills/                # Queen-created skills
│
└── reference-repos/               # Read-only references (no backup needed)
    ├── smolagents-main/
    ├── n8n-workflows-main/
    └── ...
```

---

## Tool Rights

| Actor | exec | docker_exec | spawn | web_search | read/write_file | message | workers |
|---|---|---|---|---|---|---|---|
| Queen | ✅ (gated SB.1) | ✅ (free) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Worker (Temp) | ❌ | ✅ (free) | ❌ | ✅ | ✅ | ❌ | ❌ |

`exec` (host shell, root) stays with Queen only. Workers cannot touch the host, cannot message the user directly, cannot spawn other workers.

---

## Worker Lifecycle

```
Queen calls spawn(name, task, tools, max_iterations)
  → WorkerRegistry.register(worker)
  → WorkerLoop starts in background asyncio task
  → Queen sends: "Started [name]. I'll notify you when done."

WorkerLoop runs:
  → On complete: completion_callback → bus.publish → Telegram
  → On timeout (max_iterations): provide_final_answer() synthesis → notify → die
  → On error: error summary + step trace → notify → die
```

**Concurrency cap:** `maxWorkers` (default 3). At cap, Queen queues or rejects — always explains.
**Consort promotion:** `memory/workers/{name}/` created for promoted workers. Future runs inherit context.

---

## Model Strategy

| Role | Model | Notes |
|---|---|---|
| Queen | `gemini/gemini-3-pro-preview` | Thinking model. `maxTokens: 65536` (thinking overhead). |
| Workers | Gemini Flash or Qwen via OpenRouter | Cheaper acceptable — workers do bounded tasks |
| Queen (future) | Stable Gemini 3 Pro when out of preview | Drop `-preview` suffix, same key |

---

## Design Constraints

- Do NOT rewrite the core agent loop. Extend it.
- Do NOT introduce heavy dependencies (no LangChain, no CrewAI, no vector DBs).
- Keep new files under 500 lines each (ask otherwise).
- All file IPC uses write-then-rename pattern (atomic writes).
- Never say "I fixed it" unless you verified the output.
- Scripts must survive re-runs (idempotency).
- No temp files left behind after any task.

---

## Commit Discipline

- One commit per logical change
- Message format: `type(scope): description` (e.g., `fix(S4): resolve pipeline deadlock`)
- Gate commits at phase boundaries: `feat(SX): GATE commit`
- Git tags at critical milestones: `queen-alpha_SX_name`

---

## How We Work

This is an agile project. The build plan is a living document, not a contract.
- Plan amended whenever we learn something that changes the approach
- The builder (Antigravity) is always free to suggest different approaches
- Two-layer testing: automated pytest + Alex testing live on Telegram
- Docs: `ANTIGRAVITY.md` for builder lessons and traps, `STATUS.md` for current state

**Rule:** If a new session can't figure out what to do next from `ANTIGRAVITY.md` + `STATUS.md`, we failed at documentation.

---

## Smolagents Reference (reviewed 2026-02-19)

Location: `/root/reference-repos/smolagents-main`

**Borrowed:**
- Agent-as-tool interface: sub-agent exposes `inputs = {task: str, ...}`, appears as named tool
- `provide_final_answer()` grace exit: on max_steps, one extra LLM call synthesises before dying
- `provide_run_summary` pattern: worker appends step trace — orchestrator gets full visibility
- `reset=False` resume: re-summon a Consort and it continues from memory

**Not taken:**
- `LocalPythonExecutor` — we have Docker (stronger isolation)
- `CodeAgent` (LLM writes Python strings) — doesn't fit our tool-call architecture
- Sync blocking `run()` — we're async-native
- Hub serialisation / Gradio UI — irrelevant
