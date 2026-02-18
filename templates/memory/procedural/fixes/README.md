# procedural/fixes/

Known problems with known solutions.

## Naming convention

Filename = the problem symptom or error name.

Examples:
- `port_conflict.md` — port already in use
- `permission_denied.md` — file/directory permission errors
- `docker_daemon_not_running.md` — Docker service not started

## File format

```markdown
# {Problem Name}

**Confidence:** HIGH | MEDIUM | LOW
**Source:** {how this was discovered}
**First seen:** {date}

## Symptoms

[What you see when this problem occurs]

## Root cause

[Why it happens]

## Fix

[Exact steps to resolve it]

## Prevention

[How to avoid this in the future]
```

## Population

Created automatically via `report_task(status="failure")` after repeated failures,
or manually when a fix is discovered.
