# HISTORY.md — Build History

> **This is a living narrative log.** It's written for humans (and future builders) to understand not just what was built, but why decisions were made and what we learned. 
> Git commits capture *what changed*. This file captures *why*.

For the technical build state and roadmap see [STATUS.md](STATUS.md).

---

## Phase 1 (S0–S7): Building the Foundation (Jan–Feb 2026)

### S0 — Baseline + Telegram
*Tag: `queen-alpha_S0_baseline` · Commit `106e6a4`*

The start. Scaffold, venv, Telegram channel. Proved the agent can receive a message and respond.

**Decision:** Telegram as primary channel (not Discord) because Alex tests from her phone — Telegram is her tool of choice for quick feedback loops.

---

### S1 — JSONL DAG Memory
*Tag: `queen-alpha_S1_dag_memory` · Commit `53e0689`*

Replaced HISTORY.md (flat append log) with a proper DAG session store. Each message is a node with `parent_id`. Sessions can branch, be compacted, and reconstructed for the LLM.

**Reference:** `pi-mono-main/` DAG implementation ported to Python.

**Why DAG over flat log?** Compression: summarised old branches stay in the tree as context without token bloat. Branching: conversations can fork (approval flows, multi-step confirmations) without losing history.

---

### S2 — Memory Architecture
*Tag: `queen-alpha_S2_memory_arch` · 182 tests*

The memory system. Six-tier hierarchy: `identity/`, `systems/`, `projects/`, `procedural/`, `lessons/`, `skills/`. Signal-based learning: Queen calls `report_task` → consolidation routes to correct tier → persisted on disk.

**Key decisions made here:**
- **Core vs personal data boundary**: templates git-tracked, content in `~/.hive/workspace/`. Factory reset wipes personal data without touching core.
- **Confidence decay**: HIGH→MEDIUM at 30 days, MEDIUM→LOW at 90 days. Forces re-verification of old knowledge rather than trusting stale facts.
- **Onboarding-first UX**: no `memory/identity/user.md` → nudge to `/onboard`. Queen must know who she's working for.

**Post-S2 addition:** LLM-driven onboarding replaced the state machine. The state machine worked but felt bureaucratic — conversational mission injection is warmer.

---

### S3 — Docker Executor
*Tag: `queen-alpha_S3_docker_executor` · 257 tests*

Code lives in Docker now. `docker_exec` = ephemeral container, AST filter, 512MB/1CPU limits, non-root user (`worker`, uid 1000), `--security-opt no-new-privileges`. Not mounted to host filesystem — only `/sandbox` volume.

**Why Docker over AST-only?** AST filtering catches known patterns. Docker catches everything else — even patterns we haven't imagined yet. The container IS the gate. This is a structural guarantee, not a heuristic.

**Two-mode execution defined here:** `exec` (root on host, permanent) vs `docker_exec` (sandbox, ephemeral). The mental model: if you'd be nervous running it directly, use docker_exec.

**OpenClaw RCE context:** OpenClaw's same-month RCE (Feb 2026) was an in-process Python executor. Docker makes this structurally impossible in our system.

---

### SA — Audit Layer
*Commit `4a3921a` · 289 tests*

Structured JSONL event log. Every tool call, LLM call, channel event. SHA-256 of docker_exec code. Sanitized args (sensitive keys replaced with `<N chars>`). Daily MD summaries at 09:00 UTC.

**Why structured JSONL?** grep-friendly, encrypt-friendly, appendable without locking. MD reports for humans; JSONL for future automated analysis.

**Key constraint:** Audit writes are fire-and-forget — a failed write must never break the main system. The system keeps running even if the audit can't write.

---

### SB — Security Boundaries
*Tag: `queen-alpha_SB_security_boundaries`*

The event that triggered this: from the live audit log (2026-02-20), discovered that a 2-character Telegram message triggered 9 tool calls overnight (file writes, docker_exec, exec) via memory resumption. Queen wrote a script, executed it, scheduled it for weekly cron — no human review at any step.

This was a wake-up call. `exec` was completely ungated.

**SB.1 — Tiered gate:** Tier 0 (hard reject: `rm -rf`, disk wipe), Tier 1 (deferred: `exec` needs approval), Tier 2 (always free: `docker_exec`, reads, web search). Gate lives in `ToolRegistry.execute()` — not in persona, not in memory. Code that cannot be reasoned around.

**SB.2 — Channel roles:** `user`, `admin`, `notification`. Admin `/APPROVE exec` intercepted before the LLM — no model involvement in the approval path. Known-chats persistence so Queen can reach user after any restart.

**SB.3 — Session resumption:** `SYSTEM SECURITY OVERRIDE` injected on first message of a loaded session. Forces Queen to summarise pending tasks and halt before executing anything.

**SB.4 — Skill first-run gate:** SHA256 of script file. First run needs approval. Hash stored. Known flaw: workspace-constraint check can short-circuit this gate for workspace-path scripts. Logged. Not yet fixed (low priority — Flow-Dev consort, HT.4, is when this matters most).

**PY hardening:** `SecretStr` on all credential fields. SSRF private-IP blocklist on `web_fetch` (127.x, 10.x, 192.168.x, redirect chains too). `ConfigDict(extra='forbid')` and `Field(ge=, le=)` bounds on all config models.

---

### S4 — Hive Manager (Worker Spawning)
*Tag: `queen-alpha_S4_hive_manager`*

Workers are AgentLoop subclasses (not docker_exec calls — that's code isolation; this is *agent* isolation, a different layer). They run in background asyncio tasks, report back via MessageBus, self-terminate on completion or timeout.

**From smolagents review:** borrowed the `provide_final_answer()` grace exit — when iteration cap hits, one extra LLM call synthesises before dying. This was the right pattern.

**The fire-and-forget bug (fixed 2026-02-25):** `spawn_pipeline` silently failed after stage 1 for its entire existence. Root cause: the pipeline called `spawn_worker()` (returns `PENDING` immediately) then checked `status != "completed"` — always True. Fixed by adding `spawn_worker_and_wait()` to `WorkerRegistry`. This was found during the S5/S6 audit session, not during original development.

**Second bug fixed same session:** `SpawnPipelineTool` was not wired into `_set_tool_context()`, so all completion messages routed to `"cli:direct"` (dead channel). Both bugs had existed since day one of the feature.

**Lesson:** Fire-and-forget tools that also publish bus messages need context wired explicitly per-message.

---

### S5 — Skill Forge
*Commit `eb87bc9`*

Queen can now make her capabilities permanent. `SkillForgeTool` validates names (kebab-case only, no traversal), enforces YAML frontmatter in SKILL.md, atomically writes. Rollback on error: partial directories cleaned up.

**Decision: smolagents deferred.** The original vision had a "Python Dev" worker powered by smolagents that thinks in code. Deferred — conflating code generation with skill packaging would have over-engineered S5. Minimum viable: `forge_skill` tool. Queen can already generate code with workers + docker_exec. Packaging is the missing piece.

---

### S6 — Safety Rails
*Tag: `queen-alpha_S6_safety_rails`*

Token tracking, daily budget gates ($10 default), per-worker limit ($0.50 default), SHA256 circuit breakers (action loop + error loop), emergency controls (`/emergency-stop`, `/budget-status`), proactive alerts at 75%/90%/100% of daily budget.

**Audit from 2026-02-25:** Only 3 unit tests covered `BudgetTracker` + `CircuitBreaker` — 2 critical safety systems. Added 6 gap tests: persistence across restarts, day rollover, concurrent write safety, exact-limit boundary, breaker counter isolation, off-by-one threshold.

---

### S7 — Emission Stream
*Commit `61a467f` · 523 tests · tag: `queen-alpha_S7_emission_stream`*

Final Phase 1 milestone. Real-time system telemetry over WebSocket (`ws://127.0.0.1:9100`). The stream publishes tool calls, LLM calls, worker lifecycle events, and budget updates to any connected observer via `hive stream`.

**Architecture decision: EventEmitter separate from MessageBus.** MessageBus handles channel I/O (Telegram messages, Discord messages). AuditLogger handles persistent disk writes. The new `EventEmitter` in `hive/bus/emitter.py` handles in-memory fan-out telemetry. Each concern stays clean. Mixing them would have coupled observability to channel routing in a way that'd be painful to unpick later.

**Fan-out design:** Each WebSocket client gets its own bounded `asyncio.Queue` (1000 events). Overflow drops oldest, never blocks the emitter. The emitter can have 0 to N subscribers — adding a client adds a queue subscription; disconnecting removes it. Lock is per-emitter, not global.

**Tap points are optional (`emitter=None` default everywhere):** All 4 tap points (ToolRegistry, AgentLoop, WorkerRegistry, BudgetTracker) accept `emitter=None`. When no emitter is wired, zero overhead. When wired, each taps a `from hive.bus.emitter import HiveEvent` inside the `if self._emitter:` block — lazy import, no coupling at module load.

**Non-blocking `start()` / blocking `serve_forever()` split:** Tests need to start a server, poke it, and stop it fast. A single `serve_forever()` that blocks would force every test to manage a background task. The split (`start()` sets up the server, `serve_forever()` blocks) makes tests clean and gateway integration simple.

**Liveness check on timeout:** The client handler polls `queue.get()` with a 0.5s timeout. On timeout, it checks `websocket.close_code is not None` — if the client is gone, break. Otherwise continue. This was discovered through iterative debugging: the websockets library doesn't raise `ConnectionClosed` until you *send* something, so an idle stream with a disconnected client would hang for up to 45s (the ping timeout) without this check.

**`hive stream` CLI:** Color-coded by event type (cyan=tool, yellow=llm, magenta=worker, green=budget, blue=system). Human-readable by default, `--json` for raw. Connection refused message tells you the gateway isn't running.

**Phase 1 is now closed.** Full test suite: 523 passing.

---

## Phase 2 (Post-S7): Building the Office (2026, ongoing)

Phase 2 is the Hive-Teams and integrations. See `STATUS.md` for the current roadmap.

Phase 2 is the Hive-Teams and integrations. See `STATUS.md` for the current roadmap.

Three tracks: A (Foundation: Instructor, ai-bom, Crawl4AI), B (Integrations: n8n, Docling, Dropzone), C (Hive-Teams: framework, Research-Team, Writing-Team, Flow-Dev). First recommended step: **A.2 Instructor integration** — structured LLM output unblocks all downstream structured data work.

Full strategic plan: `/root/alex_notes/hive-office_main-system_implementation_plans.md`

---

*Append to this file after each major milestone. One section per milestone. Be honest about bugs, false starts, and what we learned — that's the valuable part.*
