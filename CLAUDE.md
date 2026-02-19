# hive-office-agents — Project Knowledge Base

## Project Identity

**hive-office-agents** — autonomous AI agent system. The Hive.
The Queen manages. Workers execute. The architecture is collaborative and modular by design.

The Queen is a *manager*, not a worker. She plans, delegates, quality-checks, learns, and is user-centric — not task-focused. This distinction is fundamental. Without it, it's just a chatbot.

Built on **nanobot** v0.1.3.post7 (see [NANOBOT_BASELINE.md](NANOBOT_BASELINE.md) for upstream attribution).
GitHub: `Lexi-Energy/hive-office-agents` (private)

## Vision: What We're Building

Not "OpenClaw but Python." What OpenClaw should have been:
- **Security-first**: AST filter + Docker isolation. OpenClaw has a known RCE (Feb 2026). We don't.
- **Quality over volume**: 10 battle-tested skills > 1,700 unvetted. Queen writes her own.
- **3 channels that work perfectly** > 15 that sort-of work (Telegram ✓, SFTP, Gmail — post-S7)
- **Cost control built-in**: token budget gate, circuit breaker. No surprise bills.
- **Modular and packageable**: each layer is independently deployable and replaceable.

Strategy: Phase 1 = match OpenClaw core (S0-S7). Phase 2 = exceed on workflows (5 that solve real problems completely). Phase 3 = open the tool format. Phase 4 = network effects.

Reference: `docs-alex-vision-DO_NOT_EDIT_READ_ONLY/Where OpenClaw users hurt and where you win.md`

## Hive Architecture (canonical)

```
Hive-Queen  (LAW, root, crowned)
├── Hive-Teams  (highest class — specialised multi-worker collaborative workflows)
│   ├── Writing-Team     (e.g. RAG-powered content production)
│   ├── Research-Team    (multi-worker, learns from each run)
│   └── ... (each Team is a defined workflow + learning layer)
├── Workers
│   ├── Temps       — ephemeral. Queen spawns, Queen kills when done.
│   └── Consorts    — stateful. Promoted temps. Do the Queen's bidding long-term.
└── Personal Skill Docker  (experimental)
    └── Python Dev (smolagent) — Queen instructs → creates solution → Queen checks
                                  → duplicates for workers, teams, or direct use
```

**Queen's explicit responsibilities:**
- Delegates all execution — does not do heavy work herself
- QA and fact-checks all output from workers and teams
- Pauses teams/workers when server resources demand it
- Kills temps on task completion
- Can lend Consorts to Hive-Teams temporarily
- Future: token budget monitoring, flow integrity checks, suggests better approach

**How this maps to the build steps:**
- S3 (Docker executor) = the sandbox every worker runs in, including the personal Python dev
- S4 (Hive manager) = spawning temps and Consorts, Self-Terminator protocol
- S5 (Skill forge) = Queen uses her Python dev to create and save reusable skills
- Hive-Teams = new step, post-S7, not yet specced in detail

**Hive-Teams** are higher-class than single workers:
- Multiple workers collaborating on a defined workflow
- The team itself learns (not just the Queen)
- Alex has pre-worked "solutions and flows" for this — detail when ready

## NO-GO (do not build without explicit direction)

- **WhatsApp channel** — security risk, deprioritized indefinitely
- **ClawHub / external skill marketplace** — not aligned with quality-over-quantity strategy
- **LangChain, CrewAI, vector DBs** — no heavy dependencies

## How We Work

**This is an agile project.** The build plan (see below) is a living document, not a contract.
- The plan gets amended whenever we learn something that changes the approach
- The builder (Claude Code) is ALWAYS free to suggest different approaches
- Daily recap and test sessions are the checkpoint for plan adjustments
- Alex (she/her) tests via Telegram for experience quality; Claude Code tests via pytest for correctness
- Two-layer testing protocol: see `docs/hive_office_test_protocol.md`

## Core vs Personal Data — Decision Framework

Before building anything, ask: **where does this belong?**

**The test:** Would a factory reset erase this? Does it change per user/deployment?
- Yes → personal data (wipeable, `~/.hive/workspace/`)
- No → core (git-tracked, `queen-alpha/workspace/` or `hive/`)

| Thing | Type | Location |
|-------|------|----------|
| Queen's *type* ("Hive Queen") | Core | `workspace/SOUL.md` |
| Queen's *personal name* (given by user) | Personal data | `memory/identity/user.md` |
| Operational rules (SOUL.md) | Core | `workspace/SOUL.md` |
| User's name, address, preferences | Personal data | `memory/identity/` |
| **User's language preference** | **Personal data** | `memory/identity/preferences.md` |
| **User's constraints** ("never lie") | **Personal data** | `memory/identity/constraints.md` |
| Memory hierarchy *structure* (templates) | Core | `templates/memory/` |
| Memory hierarchy *content* (learned facts) | Personal data | `~/.hive/workspace/memory/` |
| Tool definitions | Core | `hive/agent/tools/` |
| Queen's created skills (system) | Core | `hive/skills/` |
| **User-created / Queen-written skills** | **Personal data** | `~/.hive/workspace/skills/` |
| Session history | Personal data | `~/.hive/sessions/` |
| Channel config, API keys | Personal data | `~/.hive/config.json` |

**Principle:** Core ships with every Queen instance. Personal data belongs to the user and wipes cleanly.
If a new user installs the Hive, they should get the same core — and zero of the previous user's data.

**When in doubt:** ask "would this make sense on a fresh install for a different user?" If yes → personal data.
User-created content (learned facts, skills the Queen wrote, preferences, project data) is **always** personal data,
even if it lives in the workspace directory. Never hardcode user-specific content into core files.

## Gateway Routine (every session)

**After any code change — restart the gateway:**
```bash
kill $(pgrep -f "hive gateway") && sleep 2
source /root/queen-alpha/.venv/bin/activate
nohup hive gateway >> /root/queen-alpha/gateway.log 2>&1 &
sleep 4 && tail -20 /root/queen-alpha/gateway.log
```

**Check the log before assuming code works:**
```bash
tail -50 /root/queen-alpha/gateway.log
```

**Stale process check** — if process start time < last commit time, restart:
```bash
ps -o pid,lstart -p $(pgrep -f "hive gateway")
git -C /root/queen-alpha log --oneline -1
```

Alex tests live on Telegram. Her feedback and the gateway log are real-time QA — use both.

## Constraints

- Do NOT rewrite the core agent loop. Extend it. (exceptions are for now the memory system and are open to extension, which you can discuss with Alex)
- Do NOT introduce heavy dependencies (no LangChain, no CrewAI, no vector DBs).
- Keep new files under 500 lines each, if possible (ask otherwise).
- Use the existing skill system for new tools.
- All file IPC uses write-then-rename pattern (atomic writes).
- Never say "I fixed it" unless you verified the output.
- Scripts must survive re-runs (idempotency).
- No temp files left behind after any task.

## Commit Discipline

- One commit per logical change
- Message format: `SX.Y: description` (e.g., `S1.2: implement get_path traversal`)
- Gate commits at phase boundaries: `SX GATE: description`
- Snapshots (git tags) at critical milestones: `queen-alpha_SX_name`

## Security & Secrets

- All secrets (API keys, bot tokens, user IDs) live in `~/.hive/config.json` (chmod 600, outside repo)
- NEVER commit secrets to git — not even in commit messages
- Telegram bot: @hive_queen_alpha_bot (allowlisted to Alex only)
- GitHub PAT: stored in git remote URL only (not in any file)
- Audit command: `git log --all -p | grep -E '(AIzaSy|bot_token_prefix|github_pat_)' `

## Session Continuity Protocol

Context gets compressed and sessions restart. To stay in the loop:

1. **CLAUDE.md** — read this first every session. It's the project brain.
2. **STATUS.md** — current step, blockers, decisions, open questions.
3. **Update both** at every gate commit and whenever something significant changes.
4. **Commit messages** encode the step: `S1.3: ...` tells you exactly where we are.
5. **Git log** is the ground truth: `git log --oneline` shows the full build history.

Rule: if a new session can't figure out what to do next from CLAUDE.md + STATUS.md + git log, we failed at documentation.

## Server Layout

```
/root/                             # Server home
├── queen-alpha/                   # ← GIT REPO (the codebase). git push = backed up.
│   ├── hive/                      # Core Python package
│   │   ├── agent/                 # loop.py, context.py, memory.py, retrieval.py,
│   │   │                          #   consolidation.py, onboarding.py, admin.py,
│   │   │                          #   skills.py, subagent.py, tools/
│   │   ├── channels/              # 9 chat integrations (telegram, whatsapp, etc.)
│   │   ├── bus/                   # Async pub/sub message routing
│   │   ├── config/                # Pydantic config models + JSON loader
│   │   ├── providers/             # 16 LLM providers via LiteLLM
│   │   ├── cron/                  # Scheduled task service
│   │   ├── heartbeat/             # Proactive agent wake-up
│   │   ├── session/               # JSONL DAG conversation storage
│   │   ├── skills/                # Bundled skills (github, weather, tmux, etc.)
│   │   ├── cli/                   # hive CLI (gateway, agent, status, etc.)
│   │   └── utils/
│   ├── templates/                 # Memory hierarchy templates (git-tracked, no user data)
│   │   └── memory/                # Copied to ~/.hive/workspace/memory/ on first boot
│   ├── workspace/                 # Template workspace files (SOUL.md, AGENTS.md, etc.)
│   ├── bridge/                    # WhatsApp bridge (TypeScript/Node.js)
│   ├── docs/                      # Planning, specs, references (git-tracked)
│   │   └── specs/                 # Alex's vision docs (memory architecture, build specs)
│   ├── tests/                     # pytest suite (182 tests)
│   ├── CLAUDE.md                  # Project brain — read first every session
│   └── STATUS.md                  # Current step, decisions, open questions
│
├── .hive/                         # ← RUNTIME DATA. Back this up manually.
│   ├── config.json                # API keys, bot token, channel config (chmod 600)
│   ├── sessions/                  # Conversation history (JSONL DAG files)
│   └── workspace/                 # Queen's working directory
│       ├── SOUL.md, AGENTS.md     # Core behavior rules (from queen-alpha/workspace/)
│       ├── memory/                # LEARNING — everything the Queen knows
│       │   ├── MEMORY.md          # Rich long-term facts (populated, valuable)
│       │   ├── identity/          # user.md, constraints.md, preferences.md (after /onboard)
│       │   ├── systems/           # infrastructure.md, tools.md
│       │   ├── projects/          # per-project working memory
│       │   ├── procedural/        # workflows/ and fixes/
│       │   ├── lessons/           # failures.md, patterns.md, corrections.md
│       │   └── skills/            # skills_registry.json
│       └── get_to_know_alex_game.md  # Game session from Feb 18
│
└── reference-repos/               # Read-only reference material. No backup needed.
    ├── pi-mono-main/              # pi-mono DAG reference (used for S1)
    ├── n8n-workflows-main/
    ├── smolagents-main/
    ├── awesome-agent-skills/
    └── awesome-claude-code-subagents/
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
| **S0** | Scaffold + Telegram verified | **COMPLETE** — gate commit `106e6a4`, tag `queen-alpha_S0_baseline` |
| **S1** | JSONL DAG memory (replace HISTORY.md) | **COMPLETE** — gate commit `53e0689`, tag `queen-alpha_S1_dag_memory` |
| **S2** | Memory architecture (hierarchy, retrieval, confidence, signals, onboarding, factory reset) | **COMPLETE** — 182 tests, tag `queen-alpha_S2_memory_arch` |
| **S3** | Docker executor (sandboxed Python execution, AST filter) | Not started |
| **S4** | Hive manager (worker spawning, IPC, registry) | Not started. Depends on S3. |
| **S5** | Skill forge (Queen creates her own tools) | Not started. Can parallel S3/S4. |
| **S6** | Safety rails (circuit breaker, budget gate, depth limits) | Not started. Depends on S1. |
| **S7** | Emission stream (WebSocket live observation) | Not started. Last step. |

### Model Strategy

| Role | Model | Notes |
|------|-------|-------|
| Builder (Claude Code) | Claude Opus via subscription | Architecture work |
| Queen (dev/test) | Gemini 2.5 Flash via API | EUR 200 in credits, fast + cheap |
| Queen (production) | Gemini 2.5 Pro or Claude Sonnet | Upgrade when stable and costs clear |
| Workers | Gemini Flash or Qwen and other opensource models via OpenRouter | open to extension |

## Environment (Verified 2026-02-18)

| Component | Version / Path | Status |
|-----------|---------------|--------|
| OS | Linux 6.8.0-100-generic (Ubuntu) | Running |
| Python | 3.12.3 | System |
| Virtual env | `/root/queen-alpha/.venv/` | All deps installed (editable mode) |
| Node.js | 20.20.0 | Working |
| npm | 10.8.2 | Working |
| hive CLI | `hive` (via `pip install -e ".[dev]"`) | Working |
| Config | `~/.hive/config.json` | Initialized via `hive onboard` |
| Workspace | `~/.hive/workspace/` | Created (AGENTS.md, SOUL.md, USER.md, memory/) |
| WhatsApp bridge | `/root/queen-alpha/bridge/dist/` | Built, 0 vulnerabilities |
| Test suite | 182/182 passed | All green |
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
- **Agent Loop** (`hive/agent/loop.py`): ReAct pattern, 20 iter cap, capacity trigger at 200 msgs (DAG-only), signal-based memory writes via `report_task`
- **Memory hierarchy** (`hive/agent/memory.py` + `memory/`): `MemoryEntry` with confidence (HIGH/MEDIUM/LOW) + decay. Hierarchy: identity/, systems/, projects/, procedural/, lessons/, skills/
- **Retrieval** (`hive/agent/retrieval.py`): `MemoryRetriever` — always loads identity/, on-demand loads matching workflows + failure paragraphs
- **Consolidation** (`hive/agent/consolidation.py`): 6 signal types → 6 memory writers (workflow, failure, correction, decision, pattern, skill)
- **Onboarding** (`hive/agent/onboarding.py`): `/onboard` — 4-phase state machine, writes to memory/identity/ and memory/systems/
- **Factory reset** (`hive/agent/admin.py`): `/factory-reset` — backup zip + wipe memory/ + sessions/ + reinitialise
- **Session DAG** (`hive/session/dag.py`): JSONL tree sessions. Each message is a node with parent_id. build_context() reconstructs the branch for the LLM. compact() embeds summaries in the tree.
- **Context** (`hive/agent/context.py`): Assembles system prompt from bootstrap files + memory + skills
- **Providers** (`hive/providers/registry.py`): 16 providers via ProviderSpec, LiteLLM routing
- **Tools** (`hive/agent/tools/`): exec, read/write/edit_file, list_dir, web_search/fetch, message, spawn, cron, MCP
- **Skills** (`hive/agent/skills.py`): YAML frontmatter, progressive loading, dependency checking
- **Channels** (`hive/channels/`): Abstract base, ChannelManager dispatches outbound

### Config
`~/.hive/config.json` — sections: `agents`, `channels`, `providers`, `gateway`, `tools`

## Reference Documents

| Document | When to read |
|----------|-------------|
| `docs/PIMONO_DAG_REFERENCE_v2.md` | Before starting S1. Full Python port code for JSONL DAG. |
| `docs/hive_office_test_protocol.md` | Before every step. Two-layer testing (automated + Alex via Telegram). |
| `docs/hive_office_revised_plan_v03.md` | The build plan. Living document. |
| `docs/hive_office_brainstorm_archive.md` | Future ideas only. Not actionable unless directed. |

## Commands Reference

```bash
hive onboard           # Initialize config & workspace
hive agent             # Interactive chat
hive agent -m "..."    # Single message
hive gateway           # Start gateway (channels + cron + heartbeat)
hive status            # Show config status
hive channels status   # Show channel status
hive cron list         # List scheduled jobs
```
