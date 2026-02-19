# STATUS.md

## Current step: S4 (Hive Manager) — NOT STARTED
## Last git commit: `0693718` — S3.4: worker.Dockerfile, 257 tests
## Git tag: `queen-alpha_S3_docker_executor` (at `0693718`)

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

## Next step: S4 — Hive Manager

Workers + spawning. Queen can now have workers run in Docker. Smolagents review before speccing.

Key things to spec with Alex before building:
- Worker anatomy (what does a Temp worker look like? just a docker_exec call? or a full agent?)
- IPC: how does the worker report back? (file in /sandbox? message bus? direct return?)
- Worker registry (how does Queen track what workers are running?)
- Consorts: how does a Temp get promoted? what state does it keep?
- Self-Terminator protocol: what triggers kill vs keep?

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

- S4 worker anatomy: Temp = docker_exec call? or full mini-agent in container?
- S4 IPC: worker reports back via file in /sandbox? message bus? direct tool return?
- Smolagents review: Alex wants to share patterns from smolagents-main before S4 spec
- First-boot `/onboard` nudge: proactive (Queen asks) or passive (suggested in system prompt)?
- Hive-Teams spec: when does Alex want to detail this?
