# procedural/

How to do things. Workflows that worked. Known fixes for known problems.

**Loaded on-demand** when starting a similar task or encountering a known error.

## Structure

```
procedural/
  workflows/    # step-by-step approaches that worked
  fixes/        # known problem → known solution
```

## Workflow format

Each workflow file in `workflows/` covers one type of task.
Filename should match what you'd search for: `deploy_service.md`, `debug_container.md`.

## Fix format

Each fix file in `fixes/` covers one recurring problem.
Filename should be the problem: `port_conflict.md`, `memory_leak.md`.

## How the Queen uses these

- When starting a task: keyword search against `workflows/` filenames
- When hitting an error: keyword search against `fixes/` filenames and `lessons/failures.md`
- When a task succeeds: `report_task(status="success")` → Queen extracts workflow

## Rules

- Written after successful execution, not speculatively
- Include: what worked, what to watch out for, confidence level
- **This is user data** — factory reset wipes it
