# STATUS.md

## Current step: S1 (DAG memory) — COMPLETE
## Last git commit: `84d0485` — S1.3: update loop.py

## S1 Checklist

- [x] DagSession core module (`hive/session/dag.py`) — 13 new tests
- [x] Wire DagSession into Session class (`hive/session/manager.py`)
- [x] Update loop.py consolidation — remove HISTORY.md, use CompactionEntry
- [x] Update memory.py — remove append_history() and history_file
- [x] 68/68 tests passing
- [x] Gateway restarted, Telegram verified live
- [x] S1 GATE commit + tag

## S0 (Complete)

- [x] All S0 items — see tag `queen-alpha_S0_baseline` (commit `106e6a4`)

## What changed in S1

- `hive/session/dag.py` (NEW): JSONL tree sessions. Each conversation stored as an
  append-only .jsonl file. Every message is a node with parent_id. Branching supported.
  CompactionEntry stores summaries in-tree (replaces HISTORY.md).
- `hive/session/manager.py`: Session.messages list → DagSession backing. add_message()
  writes to DAG, get_history() calls build_context(). Append-only, crash-safe.
- `hive/agent/loop.py`: 8 session.messages refs → session.message_count + _dag.get_path().
  Consolidation writes CompactionEntry instead of HISTORY.md.
- `hive/agent/memory.py`: Removed append_history() and history_file. MEMORY.md stays.
- `tests/test_dag_session.py` (NEW): 13 tests covering all DagSession operations.
- `tests/test_consolidate_offset.py`: Updated to use new DAG API.

## Migration note

Session files created before S1 (old flat format) are gracefully handled — old messages
have no `type` field and are ignored by the new loader. New messages append in DAG format.
No data migration needed (all pre-S1 sessions were dev test messages).

## Blockers

- (none)

## Next step: S2 — Identity + Telegram diagnostics

Commands to implement: /status /tree /budget /workers /health
Queen gets a stronger identity/persona in context.py.

## Open questions for next session

- S2 persona: how strong should the Queen's identity be? More assertive/personality-forward?
  Or keep the current neutral assistant style and just add the /commands?
- Budget tracking: track Gemini API spend per day? Or defer to S6 safety rails?
