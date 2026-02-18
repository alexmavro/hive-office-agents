# identity/

Who the user is, what they value, how they want to be served.

**Always loaded** into every system prompt.

## Files

| File | Purpose | Changes how often |
|------|---------|------------------|
| `user.md` | Name, role, languages, timezone | Rarely |
| `constraints.md` | Non-negotiables — things never to do | Rarely |
| `preferences.md` | Communication style, format, autonomy level | Occasionally |
| `context.md` | Business/project context (what they do, why it matters) | Occasionally |
| `worker_shared.md` | Discipline rules inherited by all workers | Rarely |

## Rules

- Populated via `/onboard` or manual edit
- **This is user data** — factory reset wipes it
- Core behavioral rules (verify, idempotency, etc.) live in `SOUL.md`, not here
- No secrets here — use config references only
