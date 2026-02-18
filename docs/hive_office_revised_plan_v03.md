# Hive-Office: build plan v0.3

**Status:** Post-audit, post-brainstorm-compression, pre-build.
**Date:** 2026-02-17
**Supersedes:** v0.2 and all original blueprint documents.

This is the single source of truth for the build. VPS-Claude reads this file and the companion files listed below. Nothing else.

---

## Companion files (the complete file set)

| File | What it is | When VPS-Claude reads it |
|---|---|---|
| `PIMONO_DAG_REFERENCE_v2.md` | Verified spec of pi-mono's JSONL DAG, with Python port code | Before starting S1 |
| `hive_office_test_protocol.md` | Two-layer testing (Claude Code automated + Alex via Telegram) | Before every step |
| `hive_office_brainstorm_archive.md` | Compressed vision docs. Future ideas. Not actionable yet. | Only when strategist says so |
| This file | The build plan | Always |

All 38 original brainstorm .docx files have been archived. Their content lives in the brainstorm archive. Don't reference any .docx by name.

---

## What nanobot already gives us

These are done. Configure, don't build.

| Capability | Status | Action |
|---|---|---|
| Async agent loop (ReAct pattern) | Built in | Learn how it works. Don't rewrite it. |
| Tool/skill registry with progressive loading | Built in | Write new skills using the existing format. |
| Telegram channel | Built in (one of 9 channels) | Configure it. Verify it works. |
| Cron + heartbeat | Built in | Use for file-watcher later. |
| LiteLLM with 16 providers | Built in | Set default model in config. |
| MEMORY.md (persistent facts) | Built in | Keep as-is. We only replace HISTORY.md. |
| Subagent system with isolated contexts | Built in | S4 builds on top of this. |

---

## What we build (7 steps)

### S0: Baseline and scaffold

**Goal:** Working project structure. Telegram verified. Git initialized.

VPS-Claude confirms nanobot's actual file paths (agent loop, memory system, skills directory, config directory). Creates the queen-alpha/ scaffold alongside nanobot (not inside it). Initializes git. Copies PIMONO_DAG_REFERENCE_v2.md into the project directory so it's available locally. Configures Telegram and verifies a round-trip message.

Directory structure:
```
queen-alpha/
  CLAUDE.md
  STATUS.md
  PIMONO_DAG_REFERENCE_v2.md
  identity/
    IDENTITY.md        (placeholder)
    brand_voice.md     (placeholder)
  memory/
  hive/
  tools/
  tests/
```

**S0 does NOT include reading pi-mono source.** That work is already done. The reference document exists. VPS-Claude reads PIMONO_DAG_REFERENCE_v2.md directly instead of exploring the TypeScript repo.

**Commit:** `S0 GATE: project scaffold, Telegram verified`

**Snapshot:** `queen-alpha_S0_baseline` (non-negotiable)

---

### S1: JSONL DAG memory

**Goal:** Replace HISTORY.md with a JSONL tree. Branching, time travel, compaction, context reconstruction.

VPS-Claude reads PIMONO_DAG_REFERENCE_v2.md first. That document contains the full Python implementation (dataclasses, SessionManager class, all methods). The port is a translation job, not a design job.

Key deliverables:
- SessionManager class with: create, open, in_memory, append, branch, get_path, get_children, build_context
- CompactionEntry support (manual trigger, not auto)
- Crash recovery (skip malformed JSONL lines on reload)
- Integration point: wherever nanobot builds LLM context, swap HISTORY.md read for session_manager.build_context()

MEMORY.md stays untouched. It serves a different purpose (persistent facts vs conversation history). Only HISTORY.md gets replaced.

**Commit convention:** `S1.1: dataclasses`, `S1.2: get_path traversal`, etc.

**Gate commit:** `S1 GATE: DAG memory integrated, all tests green`

**Snapshot:** `queen-alpha_S1_dag-memory` (non-negotiable)

---

### S2: Identity and persona

**Goal:** The Queen has a soul. She sounds like herself, not a generic chatbot.

Two files get written:

IDENTITY.md: who she is, what she values, how she operates. Must include the five behavioral rules from the Coronation Protocol (see brainstorm archive section 15):
1. Verify rule (never claim success without evidence)
2. Idempotency rule (scripts survive re-runs)
3. Clean State rule (no temp file rot)
4. Operational loop (Analyze -> Plan -> Execute -> VERIFY -> Report)
5. Delegation principle (orchestrate, don't do grunt work)

brand_voice.md: tone, language preferences, what she says and doesn't say.

Integration: modify the prompt builder to inject both files before every LLM call.

Also in S2: build the Telegram diagnostic commands. These are for Alex during the build phase, not production features.

```
/status   - current state, active workers, memory stats
/tree     - DAG branch structure (text representation)
/budget   - token spend today
/workers  - active workers and their tasks
/health   - self-diagnostics
```

**Commit:** `S2 GATE: identity loaded, diagnostic commands working`

**Snapshot:** Git commit is enough. Low-risk step.

---

### S3: Docker executor

**Goal:** The Queen can run Python in sandboxed containers. Code goes in, result comes out, container dies.

Key deliverables:
- AST safety filter (parse before execution, reject dangerous patterns)
- Ephemeral container lifecycle (spin up -> execute -> capture output -> destroy)
- Timeout enforcement (kill container after N seconds)
- Zero leftover containers after any run

**Commit:** `S3 GATE: sandboxed execution working, AST filter tested`

**Snapshot:** `queen-alpha_S3_docker` (non-negotiable)

---

### S4: Hive manager

**Goal:** The Queen can spawn specialized workers, send them tasks, and collect results.

Builds on nanobot's existing subagent system. Adds Docker-based worker spawning, file-based IPC (write-then-rename for atomic delivery), and a worker registry (JSON file tracking name, role, status, container ID).

Workers are ephemeral. They receive a mission file, execute, write a result file, and the container gets destroyed. The Self-Terminator protocol.

**Commit:** `S4 GATE: worker spawning, IPC, registry, cleanup verified`

**Snapshot:** `queen-alpha_S4_hive` (non-negotiable)

---

### S5: Skill forge

**Goal:** The Queen can create new tools for herself.

The save_skill tool (the "scribe"): writes .py skill files that conform to nanobot's skill format. Skills load on restart. Workspace mapper: the Queen maintains an internal model of what's where on the VPS.

Can run in parallel with S3/S4 after S1 is done.

**Commit:** `S5 GATE: save_skill working, new skill loads on restart`

**Snapshot:** Git commit is enough.

---

### S6: Safety rails

**Goal:** The Queen can't destroy herself or drain the budget.

Circuit breaker on the DAG: if a branch accumulates N consecutive failures, it gets abandoned. The Queen reports what happened and stops retrying.

Token budget gate: hard daily spending limit. Blocks LLM calls when exceeded. Reports remaining budget on request.

Max branch depth: configurable cap. Prevents infinite nesting.

**Commit:** `S6 GATE: circuit breaker, budget gate, depth limit tested`

**Snapshot:** `queen-alpha_S6_safety` (non-negotiable)

---

### S7: Emission stream

**Goal:** You can watch the Queen think in real time.

WebSocket server. JSON event stream. Connect from a second terminal and see: nodes being created, tools being called, workers spawning and dying.

Last step. Everything else needs to be stable first.

**Commit:** `S7 GATE: WebSocket stream working`

**Snapshot:** Git commit is enough.

---

## Dependency chain

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
S6 (safety rails) <-- depends on S1 (circuit breaker needs DAG)
 |
S7 (emission stream) <-- last, needs everything stable
```

---

## Timeline

| Day | Target | Deliverable |
|---|---|---|
| Day 1 | S0: scaffold + Telegram | queen-alpha/ dir, git repo, working Telegram |
| Day 2-3 | S1: JSONL DAG memory | SessionManager, context reconstruction, tests green |
| Day 4 AM | S2: identity + diagnostics | IDENTITY.md, brand_voice.md, /status /tree /budget /workers /health |
| Day 4 PM | S5: skill forge | save_skill, workspace mapper |
| Day 5-6 | S3: Docker executor | AST filter, sandboxed execution |
| Day 7-8 | S4: hive manager | Worker spawning, IPC, registry |
| Day 9 | S6: safety rails | Circuit breaker, budget gate |
| Day 9 PM | S7: emission stream | WebSocket tail |
| Day 10 | Integration testing | Everything works together |

8-12 working days. Budget two weeks with buffer.

---

## Model and cost strategy

| Role | Model | Why | Cost |
|---|---|---|---|
| Builder (Claude Code) | Claude Opus via subscription | Best reasoning for architecture work | Subscription (watch message limits) |
| Queen (dev/test) | Gemini 2.0 Flash via API | EUR 200 in credits. Fast, cheap, good enough for testing plumbing. | ~EUR 0.10-0.30/day |
| Queen (production) | Gemini 2.5 Pro or Claude Sonnet via API | Upgrade when architecture is stable | EUR 1-3/day |
| Workers | Gemini Flash or Haiku via OpenRouter | Workers do narrow tasks. Small models are fine. | Pennies per task |

LiteLLM handles model switching via config. No code changes needed.

---

## CLAUDE.md (for VPS-Claude)

This goes into queen-alpha/CLAUDE.md. Fill in actual paths after S0 confirms them.

```markdown
# Queen-Alpha project rules

## What this is
Sovereign AI orchestrator based on the nanobot micro-kernel.
The Queen delegates work to Docker-sandboxed workers. She does not execute heavy tasks herself.

## Architecture
- Base: nanobot (Python 3.12, installed at ~/.nanobot/)
- Memory: JSONL-based DAG (replacing flat HISTORY.md)
- Session: Directed Acyclic Graph. Every node has node_id + parent_id.
- Execution: Docker containers for worker sandboxing
- LLM: LiteLLM (already configured). Default model set in config.
- Style: Functional composition. No deep class hierarchies.

## Constraints
- Do NOT rewrite nanobot's core loop. Extend it.
- Do NOT introduce heavy dependencies (no LangChain, no CrewAI, no vector DBs).
- Keep new files under 300 lines each.
- Use nanobot's existing skill system for new tools.
- All file IPC uses write-then-rename pattern (atomic writes).
- Never say "I fixed it" unless you verified the output.
- Scripts must survive re-runs (idempotency).
- No temp files left behind after any task.

## Commit discipline
- One commit per logical change.
- Message format: "SX.Y: description" (e.g., "S1.2: implement get_context traversal")
- Gate commits: "SX GATE: description" at phase boundaries.

## Testing
- Automated: pytest tests/
- Lint: ruff check .
- Manual: Alex tests via Telegram after each step.
- Two-layer protocol: see hive_office_test_protocol.md
- Never skip tests to save time.

## Key directories
- Agent source: [fill after S0 audit]
- Skills: [fill after S0 audit]
- Config: ~/.nanobot/
- Our additions: ~/queen-alpha/

## Reference documents
- PIMONO_DAG_REFERENCE_v2.md (read before S1, contains Python port code)
- hive_office_test_protocol.md (read before every step)
- hive_office_brainstorm_archive.md (future ideas, only when directed)

## Current step
See STATUS.md for progress.
```

---

## STATUS.md template

```markdown
# STATUS.md

## Current step: S0 (Baseline)
## Last snapshot: (none yet)
## Last git commit: (none yet)

## Blockers
- Need to confirm nanobot source file paths

## Deviations from plan
- (none yet)

## Decisions made during build
- Model for Queen dev/test: Gemini 2.0 Flash
- Model for production: TBD

## Open questions for strategist
- (none yet)
```

---

## The workflow

```
1. Alex and strategist (here) define the next task, reference step number
2. Strategist drafts task brief for VPS-Claude
3. VPS-Claude executes, commits, reports
4. Alex tests via Telegram (experience layer) and SSH (observation layer)
5. Alex reports back: STATUS.md update, conversation excerpts, gut read
6. Strategist adjusts plan if needed, loop back to 1
```

What Alex brings to each session:
- Current STATUS.md contents
- Error output or unexpected behavior
- Her read on whether the Queen "feels right"

---

## First task brief for VPS-Claude

Paste this to Claude Code to start S0:

```
TASK: S0 — Baseline setup for Queen-Alpha

CONTEXT: We are building Queen-Alpha on top of the nanobot micro-kernel.
This task creates the project scaffold. Do NOT modify any nanobot source files.

ACTIONS:
1. Confirm exact file paths for nanobot source:
   - Where is the agent loop?
   - Where is the memory/history system?
   - Where is the skills directory?
   - Show contents of ~/.nanobot/ config directory.

2. Create ~/queen-alpha/ with the directory structure from the build plan.

3. Create CLAUDE.md with the content from the build plan.
   Fill in the actual paths you found in step 1.

4. Create STATUS.md with the template from the build plan.

5. Copy PIMONO_DAG_REFERENCE_v2.md into ~/queen-alpha/.

6. git init, git add, git commit -m "S0: project scaffold"

7. Configure Telegram channel in nanobot.
   Verify: send a test message from Alex's phone, confirm response.

8. Report: paste full nanobot status output, config contents, and
   confirmation that Telegram works.

COMMIT: "S0: project scaffold"
```

---

## SQLite migration (not now)

JSONL is Phase 1. When data volume justifies it (10k+ nodes, or when you need indexed queries), migrate to SQLite. The migration is mechanical: read JSONL, insert into SQLite table. The SessionManager API stays identical. Only the storage backend changes. Resolution levels, branch-depth constraints at the DB level, and atomic transactions get added during that migration.

Don't think about this until the Queen has been running stable for at least a week.
