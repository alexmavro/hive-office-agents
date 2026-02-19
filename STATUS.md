# STATUS.md

## Current step: S4 (Hive Manager) — NOT STARTED
## Last git commit: `123b429` — SA.3: daily audit reporter + asyncio daily schedule
## Git tag: `queen-alpha_S3_docker_executor` (at `0693718`) — SA layer is a parallel track, no new tag

## S2 Checklist

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
- [x] SA GATE commit (this gate)

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

## Next step: S4 — Hive Manager

Build stages:

- [ ] **S4.1**: `WorkerLoop` — `AgentLoop` subclass with restricted tool set (no exec/spawn/message), `max_iterations` cap (hard), `completion_callback`, `progress_callback`. Worker registry write on start/complete/fail.
- [ ] **S4.2**: `spawn` tool — Queen creates a named background worker. Captures session_id + channel at spawn time. Returns immediately. Enforces concurrency cap.
- [ ] **S4.3**: Completion notification path — `completion_callback` → `bus.publish()` → Telegram. Failure notification includes step trace.
- [ ] **S4.4**: `workers` status tool + `kill_worker` tool. Queen can list and terminate.
- [ ] **S4.5**: Config: `maxWorkers` (default 3), worker tool allowlist. Gate: concurrency cap enforced, no zombie workers, all 257+ tests green.

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

**Post-S7 roadmap (from vision doc):**
- S8: SFTP watcher (file dropzone)
- S9: Gmail API (inbox sentinel)
- S10: Calendar integration
- S11: PDF processor (extract text/tables)
- S12: Web scraper (Playwright worker)
- S13: HTTP tool (generic API calls)
- S14: Invoice extraction workflow (German PDFs)
- S15: Email triage workflow (multi-account)
- S16: Research aggregation workflow

**Vision alignment:**
Build what OpenClaw should have been: 3 channels that work perfectly > 15 that sort-of work.
10 battle-tested skills > 1,700 unvetted. Queen writes her own tools. Security and cost control
are structural advantages, not features.

## Open questions for next session

- First-boot `/onboard` nudge: proactive (Queen asks) or passive (suggested in system prompt)? — deferred, not blocking S4
- Hive-Teams spec: when does Alex want to detail this? — post-S7, not blocking S4
- **Worker progress pings: verbose-only (recommended) or on by default?** — UX call for Alex, needed before S4.3
- ~~S4.1 detail: should WorkerLoop be subclass or delegator?~~ — **RESOLVED: subclass of AgentLoop**
