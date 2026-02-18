# procedural/workflows/

Step-by-step approaches for task types that have been successfully executed.

## Naming convention

Filename = what you'd search for when starting this type of task.

Examples:
- `deploy_service.md` — how to deploy a Docker service
- `debug_container.md` — diagnostic approach for container issues
- `backup_data.md` — the safety protocol for data backup
- `setup_python_env.md` — creating a reproducible Python environment

## File format

```markdown
# {Task Type}

**Confidence:** HIGH | MEDIUM | LOW
**Source:** task_success signal on {date}
**Last used:** {date}

## When to use

[One sentence: what situation triggers this workflow]

## Prerequisites

- [What needs to be true before starting]

## Steps

1. [Step 1]
2. [Step 2]
...

## What to watch out for

- [Known gotchas]

## Verification

[How to confirm the task succeeded]
```

## Population

The Queen creates files here automatically via `report_task(status="success")`.
You can also create them manually for workflows you know work.
