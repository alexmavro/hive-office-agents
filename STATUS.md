# STATUS.md

## Current step: S3 (Docker Executor) — NOT STARTED
## Last git commit: `9ab5555` — post-S2 additions (onboarding redesign, file intake, link intake, privacy)
## Git tag: `queen-alpha_S2_memory_arch` (at `489a954`)

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

## Next step: S3 — Docker executor

**Why Docker matters (not optional):**
The Docker sandbox is what makes the Queen a *manager*, not a *worker*.
Workers run code in isolation. Queen orchestrates. Without S3, the Queen has no safe execution
environment to delegate real work to. This is foundational to the Hive architecture.

Key decisions confirmed:
- S3→S4→S5→S6→S7 order is intentional — do not reorder
- AST filter (parse-before-execute) is the security differentiator vs OpenClaw's known RCE vulnerability
- Workers = temps (ephemeral) and consorts (stateful), both run in Docker
- Self-Terminator protocol prevents zombie processes (S4)

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

- S3 Docker executor: use existing `ExecTool` as foundation or build fresh?
- First-boot `/onboard` nudge: proactive (Queen asks) or passive (suggested in system prompt)?
- Hive-Teams spec: when does Alex want to detail this?
