# systems/

Infrastructure state: what the Queen is managing and how it's configured.

**Loaded on-demand** when spawning workers or making infrastructure decisions.

## Files

| File | Purpose | Changes how often |
|------|---------|------------------|
| `infrastructure.md` | VPS specs, IP, SSH setup, installed services | When infrastructure changes |
| `tools.md` | Docker, Python versions, available packages | When tools are installed/updated |
| `topology.md` | How components connect (Telegram → Queen → workers → outputs) | When architecture changes |

## Rules

- Never store actual credentials here — store references to where credentials are
- Mark each fact with confidence level (HIGH/MEDIUM/LOW) and source
- Re-verify infrastructure facts after major changes
- **This is user data** — factory reset wipes it
