# STATUS.md

## Current step: S6 — Safety Rails (COMPLETE)
## Last git commit: `b7f2a11` (simulated)
## Git tag: `queen-alpha_S6_safety_rails`

## S4 Checklist (Completed)

- [x] **S4.1**: `WorkerLoop` — `AgentLoop` subclass with restricted tool set (`docker_exec`, no shell), `max_iterations` cap, `provide_final_answer` grace mechanism.
- [x] **S4.2**: `WorkerRegistry` & Lifecycle — Tracks active tasks, enforces `maxWorkers` cap, limits concurrency.
- [x] **S4.3**: `spawn` & `spawn_pipeline` tools — Queen passes Pydantic DMZ config down to registry; pipeline strings tasks sequentially. **Bug fixed 2026-02-25**: `spawn_pipeline` was calling `spawn_worker()` (fire-and-forget, returns `PENDING` immediately) and then checking `status != "completed"` — pipeline always aborted after stage 1. Fixed by adding `spawn_worker_and_wait()` to `WorkerRegistry` + wiring `SpawnPipelineTool` context in `_set_tool_context()`.
- [x] **S4.4**: `workers` tool — Queen lists background worker uptimes and recent completion reports.
- [x] **S4.5**: Bus Event Injection — Re-routed pipeline start/end messaging directly into the event bus for immediate Discord/Telegram notification.
- [x] **S4.6**: Core Loop Mechanics Integration — `WorkerLoop` execution loop brought up to parity with `AgentLoop` using `ContextBuilder`. End-to-End tests passing.

## S6 Checklist (Complete)

- [x] **S6.1**: Token Tracking — Integrated `litellm.completion_cost()` into `LLMResponse` and `AuditLogger`.
- [x] **S6.2**: Budget Gates — Persistent `BudgetTracker` with daily ($10) and worker ($0.50) limits.
- [x] **S6.3**: Circuit Breakers — SHA256 hashed repetition detection for tools and errors (N=3).
- [x] **S6.4**: Emergency Controls — `/emergency-stop`, `/budget-status`, and proactive MessageBus alerts (75%/90%/100%).
- [x] **S6.5**: E2E Verification — Dedicated safety suite (`tests/integration/test_e2e_safety.py`) passing.

## SB Checklist

- [x] S2.1: Memory hierarchy templates (`templates/memory/`) + SOUL.md rewrite — commit `c30f1a4`
- [x] S2.2: Retrieval integration — `MemoryRetriever`, query-driven memory/ in system prompt — commit `07e738f`
- [x] S2.3: `MemoryEntry` + confidence tracking (HIGH/MEDIUM/LOW, decay schedule) — commit `1919655`
- [x] S2.4: `report_task` tool + signal detection + consolidation routing — commit `374abf3`
- [x] S2.5: Onboarding flow (`/onboard`) — 4-phase state machine, bypasses LLM — commit `d55006d`
- [x] S2.6: Factory reset (`/factory-reset`) — backup zip + wipe + reinitialise — commit `f40348b`
- [x] 182/182 tests passing
- [x] No hardcoded user data in `hive/` core
- [x] S2 GATE commit + tag

## S2 Wipeable Checklist (manual verification)

- [ ] Can delete `~/.hive/workspace/memory/` entirely and Queen still boots
- [ ] Fresh boot shows no crash (empty identity/ is graceful)
- [ ] `/onboard` creates functional user profile (test via Telegram)
- [ ] Completing onboarding populates `memory/identity/user.md`, `constraints.md`, `preferences.md`
- [ ] Active project set → `memory/.active_project` + `projects/{name}/` created
- [ ] `report_task` tool visible in Queen's tool list during conversations
- [ ] After a successful task, Queen calls `report_task(status="success", ...)` → workflow file created
- [ ] `/factory-reset` → warning + confirmation prompt shown
- [ ] `CONFIRM FACTORY RESET` → backup zip created in `exports/`, memory wiped
- [ ] Post-reset `/onboard` works cleanly

## What changed in S2

### New files
- `templates/memory/` — full template tree (identity/, systems/, projects/, procedural/, lessons/, skills/)
- `hive/agent/retrieval.py` — `MemoryRetriever`: always-loaded identity + on-demand workflow/failure search
- `hive/agent/consolidation.py` — signal detection + 6 memory writers (workflow, failure, correction, decision, pattern, skill)
- `hive/agent/tools/report_task.py` — `ReportTaskTool`: Queen signals meaningful events
- `hive/agent/onboarding.py` — `OnboardingFlow`: 4-phase structured intake, persisted state
- `hive/agent/admin.py` — `factory_reset()`: backup + wipe + reinitialise
- `tests/test_memory_hierarchy.py` — 10 tests
- `tests/test_retrieval.py` — 17 tests
- `tests/test_memory_entry.py` — 16 tests
- `tests/test_signal_consolidation.py` — 27 tests
- `tests/test_onboarding.py` — 29 tests
- `tests/test_factory_reset.py` — 15 tests

### Modified files
- `workspace/SOUL.md` — rewritten: 5 operational rules, memory protocol, communication rules
- `workspace/AGENTS.md` — removed stale HISTORY.md references
- `hive/agent/memory.py` — added `MemoryEntry`, `write_memory_entry`, `read_memory_entries`, `decay_confidence`, `initialize_memory_hierarchy`
- `hive/agent/context.py` — uses `MemoryRetriever`, removed `USER.md` from bootstrap (now via retrieval)
- `hive/agent/loop.py` — registered `ReportTaskTool`, replaced 50-msg count trigger with 200-msg capacity trigger, added `_handle_signal()`, `/onboard`, `/factory-reset` commands

### Architecture principles established
- **Core vs user data boundary**: templates (git-tracked) vs `~/.hive/workspace/memory/` (wipeable)
- **Signal-based learning**: Queen calls `report_task` → async consolidation → writes to memory hierarchy
- **Confidence decay**: HIGH→MEDIUM@30d, MEDIUM→LOW@90d, LOW→needs_reverification@7d
- **Onboarding-first UX**: fresh boot without `memory/identity/user.md` → nudge to `/onboard`

## S1 (Complete)

- [x] All S1 items — see tag `queen-alpha_S1_dag_memory` (commit `53e0689`)
- JSONL DAG sessions, DagSession, CompactionEntry, removed HISTORY.md

## S0 (Complete)

- [x] All S0 items — see tag `queen-alpha_S0_baseline` (commit `106e6a4`)

## Post-S2 additions (committed, not in original gate)

- S2.5 redesigned: LLM-driven onboarding (removed state machine, `/onboard` injects conversational mission)
- File upload intake: Queen reads PDFs/docs dropped in Telegram, extracts → confirm → save + archive
- Link intake: Queen fetches URLs, extracts → confirm → save + log
- SOUL.md: Data Handling rule (PII stays on server, not sent via web tools or spawn)

## Blockers

- (none)

## Known Growing Pains (revisit after S3)

Observed from live Telegram testing (2026-02-19). Partially fixed, partially deferred.

**Fixed this session:**
- Queen called herself "nanobot" → `_get_identity()` was hardcoding "Queen-Alpha" on top of SOUL.md. Fixed: removed identity claim from context.py, SOUL.md is now the sole identity source.
- Relative file paths failing → Queen used `memory/identity/user.md` which resolved against `/root`, not workspace. Fixed: system prompt now shows absolute workspace path with explicit "always use absolute paths" instruction.
- Voice messages causing context loss → OGG file passed raw to LLM → "Yes to what?" loop. Fixed: audio files now intercepted with graceful fallback mission.
- Language not switching automatically → Fixed: SOUL.md rule added, plus language preference save flow.
- `/factory_reset` visible in Telegram command menu → Fixed: removed from BOT_COMMANDS.
- Crash loop due to invalid Discord role → Fixed: changed invalid `"ignore"` role to valid `"notification"` role in `config.json`.

**Deferred — revisit after S3:**
- Factory reset broken in chat: confirmation phrase recognized but LLM refuses to execute it. Admin-only for now, will rethink flow later.
- Robotic greeting formula: Queen appends "How can I help you do less office work today?" to every hello. Feels like a task bot, not a friend. Needs SOUL.md tone work.
- Queen doesn't know her own execution model: "Can you restart yourself?" caused 5 turns of confusion. She has `exec` and root — she should know this. Add self-knowledge section to SOUL.md post-S3.
- Memory not internalised after restart: Queen reads identity files via tool calls instead of reasoning from them. Retriever loads them correctly but LLM doesn't "own" the knowledge. Improve retrieval quality or prime her with a startup summary.
- Voice transcription: no audio-to-text capability. Deferred to post-S3 (Whisper worker or Google STT as a Hive-Team later).

## S3 (Complete)

- [x] S3.1: AST filter (`hive/agent/sandbox/ast_filter.py`) — sandbox escape detection — commit `6183794`
- [x] S3.2: DockerSandbox class (`hive/agent/sandbox/docker_sandbox.py`) — ephemeral containers — commit `b354f89`
- [x] S3.3: DockerExecTool + loop.py registration — commit `0d5325a`
- [x] S3.4: `worker.Dockerfile` — built + verified, 257 tests pass — commit `0693718`, tag `queen-alpha_S3_docker_executor`

**Security architecture:**
- AST filter: catches Docker-escape attempts + syntax errors before container starts
- Docker: full network access (Queen can pip install), host filesystem isolated (only /sandbox mounted)
- Resource limits: `--memory 512m --cpus 1.0`
- Non-root user (`worker`, uid 1000) + `--security-opt no-new-privileges`
- Named containers with forced cleanup on timeout (no zombie containers)

**Design decision answered:** Build fresh (`DockerExecTool` + `ExecTool` coexist).
- `exec` = host-level commands (hive cron add, ls, system tasks)
- `docker_exec` = sandboxed code execution (Python + shell, full network, ephemeral)

**Queen's use of docker_exec:**
- `language=python` → code written to /sandbox/run.py → AST checked → container runs it
- `language=shell` → `sh -c` in container (no AST filter)
- `pip install` works inside container — user site-packages pre-created in image
- Files written to `/sandbox` are available during the run for exchange

## Post-S3 additions (committed, not in original gate)

- **Systemd Gateway Service**: Created `hive-gateway.service` to prevent multiple gateway instances from fighting over Telegram polling and to auto-restart the Queen gracefully. Test suite verified (473 passing).
- **Tool suppression bug fixed** (`context.py`): "Reply directly with text" rule was silently blocking ALL tool calls. Fixed to explicitly instruct tool use. Commit `e7ef059`.
- **Self-knowledge updated**: `workspace/SOUL.md` + `workspace/AGENTS.md` rewritten with exec/docker_exec two-mode execution table, pip install patterns, restart command. Copied to `~/.hive/workspace/`. Commit `0acb854`.
- **Model upgraded**: `gemini/gemini-2.5-flash` → `gemini/gemini-3-pro-preview` (thinking model, released Feb 2026). `maxTokens`: `8192` → `65536` (thinking models consume tokens before output; the cap was silently strangling complex tasks). Config only — `~/.hive/config.json`.

## S4 Architecture — Decisions Made (2026-02-19)

### From smolagents review

Reviewed `/root/reference-repos/smolagents-main` (HuggingFace, Apache 2.0). Key insight that aligns with our design:

> **Multi-agent is not a separate framework — agents are just callable tools with a standard interface.**

Stealing from smolagents:
- **Worker interface contract**: `inputs = {"task": str, "additional_args": object(nullable)}`, `output_type = "string"`. Sub-agent appears as a named tool in Queen's registry.
- **Completion report format**: `"Here is the final answer from {name}:\n{answer}\n\n[step summary if requested]"`
- **`provide_run_summary` pattern**: worker appends a summary of all steps to its report — Queen sees full trace of what the worker did.
- **Grace on max_steps**: when iteration cap hit, worker makes one extra LLM call to synthesise what was accomplished before dying (`provide_final_answer()` pattern).
- **`reset=False` resume**: useful for Consorts — re-summon a named worker and it continues from its memory, no context loss.

NOT taking from smolagents:
- `LocalPythonExecutor` AST interpreter — we have Docker (superior)
- `CodeAgent` (LLM writes Python strings) — doesn't fit our tool-call model
- Sync blocking architecture — we're async
- Hub serialisation, Gradio UI — irrelevant

### S5 Architecture Decisions (2026-02-24)

**The Separable Concerns: Generation vs. Packaging**
- **Code Generation:** The Queen already has workers with `docker_exec` that can write and test code.
- **Skill Packaging:** S5 focuses purely on the packaging layer (`forge_skill` tool). The Queen needs a strict, automated way to convert a working script into a properly formatted `SKILL.md` (with YAML frontmatter) inside `~/.hive/workspace/skills/`.

**Smolagents Integration Deferred (S5.5+)**
- While the vision outlines a "Python Dev" worker powered by `smolagents` that "thinks in code", this was deferred from the core S5 deliverable.
- Including it now would conflate code generation methodology with skill permanence, risking an over-engineered S4 repeat.
- Minimum viable S5: the `forge_skill` tool to unblock the Queen from permanently saving the capabilities she discovers.

### S5.1 Skill Forge Core (Complete)

- [x] **`SkillForgeTool` (`forge.py`)**: Tier 2 tool registered in `AgentLoop`. Validates kebab-case names, scaffolds `scripts/` and `references/` subdirectories, and strictly enforces YAML frontmatter inside `SKILL.md`. Prevents blind overwrites.
- [x] **CLI Utilities (`skill_utils.py`)**: Human parity scripts (`hive skill init <name>` and `hive skill package <name>`) to create and zip distributable `.skill` files locally.
- [x] **Verification tests**: `test_skill_cli.py` and E2E LLM simulation in `test_e2e_skill_forge.py` all passing.

### Worker design decisions (Alex + session 2026-02-19)

**1. What a worker IS**
A Temp worker is a lightweight `AgentLoop` instance — NOT a docker_exec call. Workers have their own full tool-call loop with capped `max_iterations` and a restricted tool subset. They call `docker_exec` internally when they need to run code. docker_exec = code isolation. Worker = agent isolation. These are different layers.

**2. The critical safety boundary: `exec` stays with Queen only**
Workers receive: `docker_exec`, `web_search`, `read_file`, `write_file`, `report_task`.
Workers do NOT receive: `exec` (host shell), `message` (direct Telegram access), `spawn` (no spawning).
Only Queen has root shell. This is the real security wall — Docker handles code loops, but Queen holds the host.

**3. Queen-only spawning (for now)**
Only the Queen spawns workers. Workers cannot spawn workers. Queen has direct control over: what context each worker gets, what tools it can use, quality-checking the output.

**4. Sub-spawning rule (future)**
When worker-spawning is eventually opened, any children a worker creates are always Temps only — never promotable to Consort. A worker cannot build its own permanent team.

**5. Background-first design**
Workers run async in the background. Queen returns immediately to the conversation:
`"Started researcher. I'll notify you when it's done."`
When worker completes → callback fires → message via bus → Telegram notification to user.
The user is not on the VPS. The bus is the only window. Transparency is the obligation.

**6. Concurrency cap**
Config: `maxWorkers` (default: 3). Spawn at cap → Queen tells user "3 workers running, queuing this or dropping it — your call."

**7. Proactive status reporting**
Queen must never make the user ask "what's happening?":
- **On start**: "Starting [name]: [one-line task summary]"
- **On completion**: "Done: [name] — [result summary]"
- **On failure/timeout**: "Failed: [name] at step [N] — [last action]. Here's what it did: [step list]. Do you want me to retry?"
- **On demand**: `workers` tool returns table of active/completed workers with status, iterations, last action.
- **Progress pings** (optional, verbose mode): every N iterations worker emits step update.

**8. Worker Registry**
Persisted at `workspace/workers/registry.json`. Tracks: id, name, task, started_at, status, iterations_used, last_action, result. Survives gateway restart — Queen can answer "what workers ran this week?" from this file.

**9. Self-Terminator protocol**
On `max_iterations` exceeded: worker makes one final LLM call to synthesise what was accomplished ("provide_final_answer" pattern), marks itself `status: timeout`, notifies Queen via callback. No zombie workers. No silent death.

**10. Consort promotion**
A Temp does good work → Queen promotes it: give it a name, create `memory/workers/{name}/`. Promotion means it gets a persistent memory slice for its domain. Future runs of same-named worker inherit that context. Promotion is a Queen decision, not automatic.

## Pre-S4 codebase cleanup (2026-02-19) — commit `b0c0202`

Fresh-eyes audit of the entire codebase. Everything nanobot-specific, dead, or hindering was addressed.

**Identity fixed:**
- README.md: full rewrite (hive-focused, correct `hive` CLI + `~/.hive/` paths)
- SECURITY.md: rewritten for actual VPS deployment reality
- LICENSE: Lexi-Energy copyright added alongside nanobot upstream attribution
- Bridge renamed to "Hive WhatsApp Bridge", auth path → `~/.hive/whatsapp-auth`
- tmux skill: `NANOBOT_TMUX_SOCKET_DIR` → `HIVE_TMUX_SOCKET_DIR`, `nanobot.sock` → `hive.sock`
- `workspace/HEARTBEAT.md`: "nanobot agent" → "Hive Queen"

**Dead code removed:**
- `hive/providers/openai_codex_provider.py` (282 lines) + all 6 call-sites + `oauth-cli-kit` dep
- `provider login` CLI command (only served openai_codex — gone)
- `workspace/USER.md` (deprecated template, replaced by `memory/identity/` in S2)
- `COMMUNICATION.md` (empty placeholder, all rules live in SOUL.md)
- `case/` directory (30MB nanobot demo GIFs, unrelated)

**Archived outside repo** (`/root/archive/clawhub/`):
- `hive/skills/clawhub/` — NO-GO per CLAUDE.md (external marketplace = security risk)

**Kept intentionally (not dead):**
- `hive/providers/transcription.py` — stub for future audio implementation (D2, deferred)
- `hive/agent/subagent.py` + `spawn` tool — stub, will be superseded by S4 WorkerLoop
- 8 unused channel implementations — kept for future S8+ use
- `hive/agent/tools/mcp.py` — no tests yet but needed, keep until better reference

**Verification after cleanup:**
- 257/257 tests passing
- Gateway restarted (stale since 14:51, restarted 19:34 on fresh code)
- docker_exec live test: Queen called the tool (not faked) — container Python 3.12.12 ≠ host 3.12.3
- Queen reported result accurately and completely

## Open questions — RESOLVED (2026-02-19)

**S4.1: WorkerLoop as subclass vs delegating wrapper?**
→ **Subclass of AgentLoop.** `SubagentManager` is a non-functional stub and will be superseded entirely by S4. Build WorkerLoop clean as an AgentLoop subclass with restricted tools + callbacks. Don't extend the stub.

**Worker progress pings: on by default or verbose-only?**
→ **Still open — UX call for Alex.** Recommendation: verbose-only by default (cleaner Telegram experience; on-demand `workers` tool provides status). Confirm before S4.3.

## SA — Audit Layer (COMPLETE, 2026-02-19)

Parallel build track — no dependency on S4. S4 workers will call `audit.log_worker()` when built.

### Checklist

- [x] SA.1: `hive/audit/logger.py` — `AuditLogger` (async-safe JSONL, sanitization, anomaly detection) — commit `b3e57f6`
- [x] SA.1: `hive/audit/retention.py` — `run_retention()` + `check_size_gb()` — commit `b3e57f6`
- [x] SA.1: `tests/test_audit_logger.py` — 24 tests — commit `b3e57f6`
- [x] SA.2: `AuditConfig` in `hive/config/schema.py` — commit `52c81d0`
- [x] SA.2: `ToolRegistry.execute()` wraps all tool calls with timing + sanitized arg logging — commit `52c81d0`
- [x] SA.2: `AgentLoop._run_agent_loop()` logs every LLM call with token counts + anomaly detection — commit `52c81d0`
- [x] SA.2: `AgentLoop._process_message()` logs channel events in/out (metadata only, no content) — commit `52c81d0`
- [x] SA.2: `gateway()` creates `AuditLogger`, logs start/stop, runs retention on boot, warns on size — commit `52c81d0`
- [x] SA.3: `hive/audit/reporter.py` — daily MD report generator (tool table, LLM stats, errors, anomalies) — commit `123b429`
- [x] SA.3: `_run_daily_report_loop()` asyncio task in gateway (default 09:00 UTC daily) — commit `123b429`
- [x] 289/289 tests passing
- [x] SA GATE commit `4a3921a` (CLAUDE.md + STATUS.md updated)
- [x] SA fix: `hive agent` CLI command now also creates AuditLogger (was missing `audit=` in AgentLoop constructor) — commit `802ed62`
- [x] Live verified: gateway restart → `gateway_start` event logged → Queen ran docker_exec → `tool_call` with `code: <108 chars>` sanitized in JSONL — all correct

### What gets logged

| Event type | Data logged |
|---|---|
| `tool_call` | actor, tool name, args (sanitized — sensitive keys replaced with `<N chars>`), ok/fail, duration_ms, error |
| `llm_call` | model, tokens_in, tokens_out, tool_calls_n, duration_ms, anomalies (if any) |
| `channel_event` | direction (in/out), channel, session_id, content_length (NOT content) |
| `system` | event name (gateway_start/stop), pid, model, channels |
| `worker` | worker_id, name, event — **stub for S4** |

**Anomaly flags on `llm_call`:** `tokens_in > 50,000`, `tokens_out > 10,000`, `duration_ms > 30,000`

### Decisions recorded

| Decision | Choice | Rationale |
|---|---|---|
| What to log | Tool calls, LLM calls (tokens + anomalies), channel events (metadata only), system events | Everything system-relevant; no personal data content |
| Retention | 30 days active → `archive/` → keep until manual deletion | Queen flags if >5GB, asks user |
| Sensitive args | Replace with `<N chars>` — drop content of keys: code, content, text, body, message, prompt | Privacy by default |
| Format | JSONL for audit, MD for daily reports | JSONL = grep-friendly, encrypt-friendly later |
| Schedule | asyncio task in gateway, not LLM cron | Avoids LLM round-trip for a file write |
| Log directory | `~/.hive/logs/audit/` (configurable via `AuditConfig`) | Personal data path |

### Future reworks required (before any public deployment)

- **Encryption** — JSONL files are plaintext. Add at-rest encryption before exposing to external systems.
- **PII guardrails** — Define what "personal data" means in Hive context. Audit must scrub before writing. Requires separate design session.
- **Security Office Consort** (post-S4) — A worker that reads audit logs daily, sends reports to Telegram, flags anomaly patterns over time. SA is its data foundation.
- **Real-time anomaly alerting** — Push to Telegram on repeated tool failures or cost spikes. Currently only in daily report.
- **Log shipping** — If >5GB flag fires repeatedly, ship old archives to cold storage (S3, SFTP). Not in scope now.
- **Per-worker audit trail** — S4 will add worker lifecycle events. Worker ID will correlate all worker events.

### Verification steps (run after gateway restart)

1. Restart gateway → check `~/.hive/logs/audit/YYYY-MM-DD.jsonl` has `system/gateway_start` event
2. Send Telegram message → verify `channel_event` in + out + `llm_call` with token counts
3. Ask Queen to run `docker_exec` → verify `tool_call` with tool=docker_exec + sanitized args
4. Check `pytest tests/test_audit_logger.py` — all 32 pass
5. Manually call `generate_daily_report()` → check MD file at `~/.hive/logs/reports/YYYY-MM-DD.md`

## Current: SB — Security Boundaries (SB.1 + SB.2 done, SB.3 next)

**Must complete before S4.** SB.1 + SB.2 are done. Workers spawned by S4 will inherit
the gate from ToolRegistry automatically. Next: SB.3 (session resumption check).

**Full spec:** `reference-repos/pydantic-governance.md` (Security Officer document)
**Policy:** `SECURITY.md` (summary + checklist)

### SB Checklist

- [x] **SB.1**: Tiered gate in `ToolRegistry.execute()` — Tier 0 hard-reject + Tier 1 deferred-return (no blocking) + Tier 2 always-free. `session_approve` Tier-2 tool lets LLM unlock Tier 1 categories after explicit user consent. **Update 2026-02-22**: Approvals are now strictly plan/turn-specific and wipe entirely when the Queen finishes processing the current message.
- [x] **SB.2**: Channel role config (`role: Literal["user","admin","notification"]` on all 9 channel models). `channel_role` injected into every `InboundMessage.metadata` via `BaseChannel._handle_message`. Admin-channel `APPROVE <category>` / `APPROVE ALL` commands intercepted in `AgentLoop._process_message` before the LLM, calling `registry.pre_approve()` directly — no LLM in the approval path. Caller cannot spoof role. **Discord `channel_routes`**: per-text-channel role override. **Known-chats persistence**: every inbound message writes `(channel, chat_id)` to `workspace/.known_chats.json`. **Update 2026-02-22 (Memory Isolation)**: These known-chats now route their active context explicitly to `workspace/memory/projects/ch_{channel}_{chat_id}/` to ensure separate project scoping without goldfish memory. System prompt reads all active channel scopes into context.
- [x] **SB.3**: Session resumption check — dynamic tracking in `loop.py` to inject `"SYSTEM SECURITY OVERRIDE"` on the first message of a loaded session, forcing Queen to summarize and halt unapproved tools.
- [x] **Memory & Metadata Refinement (2026-02-22)**:
  - Fixed LiteLLM `fallbacks` propagation regression in `consolidation.py` and `loop.py`.
  - Refined memory architecture: shifted from channel-isolation to **Dual Memory Architecture** (Global Identity + Project Workspaces).
  - Implemented `/project <name>` admin-only command for dynamic context switching.
  - Implemented automatic Discord channel name mapping to project directory names.
  - Injected "Curious Onboarding" prompt for pristine project spaces.
- [x] **SB.4**: Skill first-run approval gate — script files running in workspace via host exec are intercepted in `gate.py`. *(Note 2026-02-21: Logic flaw discovered where workspace constraint short-circuits the script check. Fix deferred until S4 Worker architecture solidifies Docker vs Host exec boundaries.)*
- [x] PY.1 `SecretStr` on all credential fields in `hive/config/schema.py` ← can run parallel, ~30 min

Gate tag: `queen-alpha_SB_security_boundaries`

### SB Design Decisions (2026-02-20)

**1. Gate location: ToolRegistry, not persona**
The gate must be in `ToolRegistry.execute()`. A persona-level constraint ("Queen must ask
before exec") breaks the moment S4 spawns workers — workers get their own agent loop with no
inherited constraint. ToolRegistry is the single chokepoint all agents share.

**2. Admin-origin does not pre-approve execution**
A task arriving from the admin channel gives Queen the task. It does not give her permission
to run every action that task requires. The gate fires at execution time regardless of where
the original instruction came from. This prevents Queen from chaining: "admin approved the
cleanup task → therefore deleting the database is also approved."

**3. Tier structure (environment over text)**
The governing principle: the safety boundary is *which environment* the command runs in, not
what the command text says. docker_exec = Docker container = always free (the container IS
the gate). exec on host = always gated. See `SECURITY.md` for full Tier 0/1/2 lists.

**4. Approval flow (SB.1 — deferred return, no blocking)**

- Tier 0: hard reject, LLM receives "absolutely forbidden" string — no approval path
- Tier 1: gate returns a structured deferred string immediately. No asyncio.Event, no wait.
  LLM tells user what it needs. User says "yes". LLM calls `session_approve(category, reason)`.
  Gate passes for the rest of the session for that category.
- Tier 2: executes immediately, no friction.
- The `_pending_approvals` dict is pre-wired for SB.2 async admin-channel YES/NO (not active in SB.1).

**4b. Admin-channel approval flow (SB.2)**

- User sends `APPROVE exec` (or `APPROVE ALL`) to the admin-role channel from their phone.
- `AgentLoop._process_message` detects `channel_role == "admin"` and matches the pattern.
- `registry.pre_approve(category)` is called directly — no LLM in the approval path.
- Confirmation sent back to the admin channel.
- Caller-supplied `channel_role` in metadata is overwritten by the real config value — cannot be spoofed.

**5. Channel roles (SB.2)**

Config: `role: Literal["user", "admin", "notification"]` on each of the 9 channel models.
Default: `"user"`. Set `role: "admin"` on your Telegram bot instance dedicated to approvals.
Admin channel: `APPROVE <category>` commands bypass the LLM entirely.
User channel: `APPROVE exec` message is not intercepted — goes to normal LLM loop.
Notification: outbound-only — inbound messages dropped in code (enforced in Discord via
`channel_routes`, enforced for any channel whose top-level `role` is `notification`).

**5b. Discord per-channel routing (SB.2 extension)**

`DiscordConfig.channel_routes: dict[str, Literal["user","admin","notification"]]`
maps each Discord channel_id to a trust role. Overrides the top-level `role` field for
that channel. Computed in `DiscordChannel._handle_message_create`:
- `effective_role = channel_routes.get(channel_id, config.role)`
- notification → drop inbound silently
- admin/user → publish `InboundMessage` directly (bypasses `_handle_message` to preserve
  per-channel role while keeping anti-spoofing guarantee — the handler code sets the role,
  not user input)

**5c. Known-chats persistence + notification targets (SB.2 extension)**

Every inbound `_process_message` call writes `(msg.channel, msg.chat_id)` to
`workspace/.known_chats.json`. Loaded on init. Passed to `build_messages()` as
`notification_targets`. System prompt gains a "Notification Targets" section listing
all known `(channel, chat_id)` pairs so Queen can proactively reach the user via the
`message` tool after any gateway restart.

**5d. Known-source security layer (planned — SB.3 candidate)**

User insight (2026-02-21): known_chats serves as a natural allowlist. Any message from
a `(channel, chat_id)` NOT in `_known_chats` is an unknown source. Future gate:
unknown sources → queued for admin approval before Queen engages. External drops (email,
webhook) → always go to draft/workflow inbox, never directly to the LLM.
Neither the user nor their clients need anyone else talking directly to Queen — a dedicated
worker handles any external-agent interface. This inverts the current `allow_from: []`
(allow all) default to a known-first model.

**6. Pydantic DMZ for S4 (add at spawn layer)**
When S4 ships workers, add WorkerOrder + WorkerReport Pydantic models as the validation
boundary between Queen and workers. Worker output is forced into typed schema fields before
re-entering Queen's context — prompt-injected content from scraped pages cannot become an
instruction. See `reference-repos/pydantic-governance.md` → "S4 Prerequisite: Pydantic DMZ".

### SB Approval Channels

- **Primary**: Telegram admin channel (`role: admin` in config) — works from phone, anywhere
- **Secondary (future)**: `hive-approve` CLI listener on VPS — same gate, stdin input, looks
  like Claude Code approval prompts. Not required for SB.1 — add after Telegram flow works.

### Evidence that drove SB

From live audit log (2026-02-20) and session report:
- 15 `exec` calls overnight, 10 in one session — all ungated, all as root
- 2-char Telegram message triggered 9 tool calls (file writes, docker_exec, exec) via memory
  resumption — confirmed in audit log timestamps
- Queen wrote `research_health/research.py` (with Docker bypass fallback), then executed it
  immediately, then scheduled it for weekly cron — no human review at any step
- `constraints.md` written by Queen in the same session she violated it — text files are not
  security boundaries

---

## SB → S4 Handoff

After `queen-alpha_SB_security_boundaries` tag:
- Workers spawned by S4 automatically inherit the Tier 0/1/2 gate from ToolRegistry
- Workers have `exec ❌` (no host shell access at all) — they cannot even ask for it
- Workers have `docker_exec ✅` (always Tier 2 — container is the gate)
- Add Pydantic DMZ (WorkerOrder + WorkerReport) at the spawn call and completion callback

---

## S4 — Hive Manager (Complete)

Build stages:

- [x] **S4.1**: `WorkerLoop` — `AgentLoop` subclass with restricted tool set (no exec/spawn/message), `max_iterations` cap (hard), `completion_callback`, `progress_callback`. Worker registry write on start/complete/fail.
- [x] **S4.2**: `spawn` tool — Queen creates a named background worker. Captures session_id + channel at spawn time. Returns immediately. Enforces concurrency cap.
- [x] **S4.3**: Completion notification path — `completion_callback` → `bus.publish()` → Telegram. Failure notification includes step trace.
- [x] **S4.4**: `workers` status tool + `kill_worker` tool. Queen can list and terminate.
- [x] **S4.5**: Config: `maxWorkers` (default 3), worker tool allowlist. Gate: concurrency cap enforced, no zombie workers, all 479+ tests green.

Gate tag: `queen-alpha_S4_hive_manager`

## Strategic decisions (2026-02-19)

**NO-GO (do not build, not in scope):**
- WhatsApp channel — security risk, deprioritized
- ClawHub / external skills marketplace integration — not aligned with quality-over-quantity strategy

**Planned but not yet in step plan:**
- `/status` command — Queen reports her current state (memory populated? active project? tools loaded?)
- `/memory` command — show what the Queen knows (memory file summary)
- `/health` command — VPS system health (disk, memory, processes, services)
- "Hive-Teams" — Alex's concept for the next modular layer (solutions + flows). Not yet specced.

**Post-S7 roadmap — SUPERSEDED.** See Phase 2 section below.

**Post-S7 roadmap (from vision doc, ARCHIVED - replaced by Phase 2 tracks):**
- ~~S8: SFTP watcher~~ → B.3 Dropzone (Syncthing-based)
- ~~S9: Gmail API~~ → B.1 n8n with Gmail credential isolation
- ~~S10: Calendar integration~~ → deferred Phase 3
- ~~S11: PDF processor~~ → B.2 Docling
- ~~S12: Web scraper~~ → A.4 Crawl4AI
- ~~S13: HTTP tool~~ → subsumed by B.1 n8n trigger_workflow
- ~~S14~~ → after B.1 + B.2 proven
- ~~S15~~ → after HT.3 Writing-Team
- ~~S16~~ → HT.2 Research-Team

**Vision alignment:**
Build what OpenClaw should have been: 3 channels that work perfectly > 15 that sort-of work.
10 battle-tested skills > 1,700 unvetted. Queen writes her own tools. Security and cost control
are structural advantages, not features.

## Open questions (resolved + pending)

- First-boot `/onboard` nudge: proactive (Queen asks) or passive (suggested in system prompt)? — deferred, not blocking anything now
- Hive-Teams spec: → **RESOLVED**: specced in `alex_notes/hive-office_main-system_implementation_plans.md`. See Phase 2 below.
- Worker progress pings: verbose-only (recommended) or on by default? — UX call for Alex, low priority

---

## Phase 2 Roadmap — Post-S6 (as of 2026-02-25)

**Strategic doc:** `/root/alex_notes/hive-office_main-system_implementation_plans.md`
**Baseline:** S0-S6 complete, 504 tests passing, spawn bugs fixed.

Three tracks run in parallel where dependencies allow. Full detail in the strategic doc — this is the authoritative summary for future instances.

---

### Track A — Foundation

#### A.1 — S7: Emission Stream (WebSocket live observation)
**Status:** 🔲 Not started  
**Effort:** 6-8h  
**Goal:** Real-time JSON event stream over WebSocket (port 9100). Tool calls, worker lifecycle, budget heartbeat. Read-only. `hive stream` CLI command.  
**Key files to create:** `hive/gateway/stream.py`  
**Key constraint:** Localhost-only binding by default. SSH tunnel for remote. No control channel.  
**Closes Phase 1 (S0-S7).**

#### A.2 — Instructor Integration
**Status:** 🔲 Not started  
**Effort:** 2-4h  
**Goal:** `instructor.from_litellm(completion)` wraps LLM calls. Enforces Pydantic schemas on WorkerReport, ConsolidationSignal. Retries on validation failure (max 3). Falls back to raw text on retry exhaustion.  
**Why first:** Everything downstream (HT.1, HT.2) uses structured TeamReport. Do this before building teams.  
**Known risk:** LiteLLM + Instructor + Gemini triple — test before wiring into production loop.

#### A.3 — ai-bom Compliance Scanning Skill
**Status:** 🔲 Not started  
**Effort:** 2-3h  
**Goal:** `ai-bom scan` on codebase + n8n workflows. Weekly cron. `/compliance` command. CycloneDX JSON in audit dir.  
**Quick win. No blockers.**

#### A.4 — Crawl4AI Web Scraping Skill
**Status:** 🔲 Not started  
**Effort:** 3-4h  
**Goal:** Clean content extraction — article text, tables, JS-rendered pages. Async batch. Rate-limited. 24h disk cache.  
**Key constraint:** Playwright binary ~500MB. Headless Chromium ~200-500MB RAM per page. Max 3-5 simultaneous.  
**Required for HT.2 (Research-Team STORM backend).**

---

### Track B — Integrations

#### B.1 — n8n Deployment + Queen↔n8n Bridge
**Status:** 🔲 Not started  
**Effort:** 4-6h  
**Goal:** n8n in Docker. Queen gets `trigger_workflow` + `list_workflows` tools. First workflow: ping test. Second: Gmail check. Credentials never in `~/.hive/config.json`.  
**Port:** 5678 (localhost only). SSH tunnel for UI.  
**Key tools:** `hive/agent/tools/n8n.py`  
**Unlocks external workflows. Block on this before inbox sentinel, bookkeeping, calendar.**

#### B.2 — Docling Document Ingestion Worker
**Status:** 🔲 Not started  
**Effort:** 4-6h  
**Goal:** `docling-serve` in Docker (port 5001). Queen skill: `parse_document`. Supports PDF, DOCX, PPTX, XLSX, HTML. PII scrubbing (regex-based, flag not auto-remove).  
**Key constraint:** AI models use 2-4GB RAM — set `--memory=4g`. Audio (Whisper) deferred to Phase 3.  
**Blocks B.3 (dropzone).**

#### B.3 — Dropzone Watcher (File Ingestion Trigger)
**Status:** 🔲 Not started  
**Effort:** 6-8h  
**Goal:** Syncthing syncs `HIVE_INBOX/` from Alex's machine to VPS `~/.hive/inbox/`. Watcher daemon routes files by subfolder intent: `summarize/`, `invoice/`, `research/`. Processed files move to `processed/`. Errors to `_errors/`.  
**Key constraint:** Poll-based (not inotify — more reliable with Syncthing). Wait for file stability (size unchanged ≥ 3s) before processing.  
**Depends on B.2.**

---

### Track C — Hive-Teams

#### HT.1 — Hive-Team Framework Spec
**Status:** 🔲 Not started  
**Effort:** 8-12h  
**Goal:** `HiveTeam` base class. DAG-of-steps execution engine. Team-level budget cap (sub-budget of S6 daily limit). Team-level learning (`memory/teams/{name}/`). Approval gates that pause + notify + resume. `delegate_to_team` Queen tool.  
**Key files:** `hive/teams/base.py`, `hive/teams/registry.py`  
**MUST come before any specific team. All teams are instances of this.**

#### HT.2 — Research-Team (STORM-powered)
**Status:** 🔲 Not started  
**Effort:** 10-16h  
**Goal:** 3-step workflow: perspective discovery → simulated research conversations → article writing. STORM engine (`pip install knowledge-storm`). BraveRM for web retrieval (free tier 2000 queries/month). $2.00 budget cap per run. Structured TeamReport (Instructor).  
**Model routing:** Flash for research, Pro for writing.  
**Key dependency:** dspy (STORM's internal framework) — test LiteLLM+dspy+Gemini triple carefully.  
**Depends on HT.1, A.2. A.4 (Crawl4AI) improves source quality but optional.**

#### HT.3 — Writing-Team Integration (co-writer-hive → Hive-Team)
**Status:** 🔲 Not started (blocked on co-writer Phase 2)  
**Effort:** 8-12h  
**Goal:** co-writer-hive exposes a localhost API. Queen wraps it as a Hive-Team. Brief in, draft out, approval loop through Telegram/Discord. Hybrid research: Research-Team (HT.2) feeds current data into Writing-Team session.  
**Key constraint:** Don't integrate a broken co-writer. P2.4 Writer specialization must be working first.  
**Depends on HT.1, HT.2, co-writer Phase 2 progress.**

#### HT.4 — Flow-Dev Consort (Internal Python Workflows)
**Status:** 🔲 Not started  
**Effort:** 6-8h  
**Goal:** Named persistent worker (Consort). Writes Python scripts for internal automation. Tests in Docker (max 3 attempts). Registers approved scripts as skills or cron jobs. Scope: 50-200 line scripts for VPS maintenance. NOT n8n workflows, scrapers, or full apps.  
**Key files:** `memory/workers/flow-dev/profile.md`, script template in `~/.hive/workspace/flows/`  
**Depends on S4, S5. Consort promotion pattern from S4 design doc.**

---

### Build Order (recommended)

| # | Plan | Track | Effort | Why now |
|---|---|---|---|---|
| 1 | **A.2** Instructor | A | 2-4h | Foundation for everything. No blockers. |
| 2 | **A.3** ai-bom | A | 2-3h | Quick win. Compliance from day one. |
| 3 | **B.1** n8n deploy | B | 4-6h | Unlocks external workflows. |
| 4 | **A.1** S7 Stream | A | 6-8h | Closes Phase 1. Observability. |
| 5 | **B.2** Docling | B | 4-6h | Document ingestion. |
| 6 | **HT.1** Team Framework | C | 8-12h | Required before any team. |
| 7 | **A.4** Crawl4AI | A | 3-4h | Prep for STORM. |
| 8 | **HT.2** Research-Team | C | 10-16h | First Hive-Team. The product starts here. |
| 9 | **B.3** Dropzone | B | 6-8h | Builds on B.2. |
| 10 | **HT.4** Flow-Dev | C | 6-8h | Internal automation consort. |
| 11 | **HT.3** Writing-Team | C | 8-12h | co-writer integration. Last. |

**Total: ~65-95 hours of implementation.**

---

### Deferred (known gaps, not in Phase 2 scope)

| Item | Reason | When |
|---|---|---|
| Inbox Sentinel (email triage) | Needs B.1 + B.2 + HT.3 first | After HT.3 |
| Calendar integration | Needs n8n + scheduling strategy | Phase 3 |
| Web dashboard (React) | A.1 builds the stream; dashboard is a separate project | Phase 3 |
| Multi-tenancy | One Queen per user until PMF | Phase 4+ |
| GPU infra (VibeVoice, local LLMs) | Not on current VPS budget | Phase 3+ |
| n8n-Architect consort | Needs B.1 stable first | After B.1 proven |
| Invoice extraction workflow | Needs B.2 + B.1 + custom prompts | After B.2 proven |
| LangFuse observability | S6+SA cover it. Dashboards later. | Phase 3 |
| Audio (Whisper) | Needs GPU or expensive CPU time | Phase 3 |

---

### Gaps vs Alex's Plan (builder audit, 2026-02-25)

Reviewed against `/root/alex_notes/hive-office_main-system_implementation_plans.md`:

1. **Instructor schemas in plan conflict with existing schemas.** Plan's `WorkerReport` adds `artifacts`, `lessons`, `token_cost` fields. Existing `hive/agent/worker/schema.py` `WorkerReport` has different fields. Reconcile before A.2. Don't create two `WorkerReport` classes.

2. **n8n auth token** must be added to `hive/config/schema.py` as `SecretStr`. The strategic doc shows it as `config.n8n_api_key` — ensure this lands in the Pydantic model, not a hardcoded env var.

3. **S7 Stream auth** — plan says "require bearer token from config.json" when not localhost. This means a new `stream_token: SecretStr` field in config. Add to schema before A.1.

4. **Consort promotion** is described in S4 design decisions but never implemented. `memory/workers/` directory exists in docs but may not be created on boot. Verify before HT.4.

5. **Port map** needs documenting centrally. Currently scattered: 5678 (n8n), 5001 (Docling), 9100 (stream), 8384 (Syncthing). Add a `## Port Allocation` section to CLAUDE.md before B.1.

6. **SB.4 logic flaw** (noted in SB.4 checklist entry) — script-check short-circuit via workspace constraint — still not fixed. Low priority, but document the known state before HT.4 (Flow-Dev) ships scripts that run through this gate.

