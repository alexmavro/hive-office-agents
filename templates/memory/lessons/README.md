# lessons/

What was learned from experience. Distilled knowledge from successes and failures.

**Loaded on-demand** when encountering errors or deciding approach.

## Files

| File | Purpose |
|------|---------|
| `successes.md` | Approaches that worked — use again |
| `failures.md` | Approaches that failed — don't retry |
| `patterns.md` | Recurring situations and their standard solutions |

## How the Queen populates these

- Task success → `report_task(status="success")` → extracted method added to `procedural/workflows/`
- Task failure (3+ attempts) → `report_task(status="failure")` → lesson added to `failures.md`
- User corrects → `report_task(status="correction")` → relevant file updated
- Pattern recognized (same approach worked 3x) → `report_task(status="pattern")` → added to `patterns.md`

## Rules

- Entries are append-only (no editing old lessons)
- Each entry has a timestamp and confidence level
- **This is user data** — factory reset wipes it
