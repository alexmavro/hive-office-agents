# STATUS.md

## Current step: S2 (Memory Architecture) — COMPLETE
## Last git commit: `f40348b` — S2.6: factory reset
## Git tag: `queen-alpha_S2_memory_arch`

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

## Blockers

- (none)

## Next step: S3 — Docker executor

Sandboxed Python execution with AST filter.
See `docs/hive_office_revised_plan_v03.md` for full S3 spec.

## Open questions for next session

- Should the Queen proactively run `/onboard` prompt on first boot, or just suggest it?
  (Currently: memory retrieval returns empty string → legacy MEMORY.md fallback → silent)
- S3 Docker executor: use existing `ExecTool` as foundation or build fresh?
- Consider wiring `initialize_memory_hierarchy()` into `AgentLoop.__init__()` (templates_dir
  needs to be resolved from package installation path)
