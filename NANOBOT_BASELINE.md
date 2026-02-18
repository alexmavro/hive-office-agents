# Nanobot Baseline

This project is built on top of **nanobot**, an open-source lightweight AI assistant framework.

## Upstream Source

- **Repository:** https://github.com/HKUDS/nanobot
- **Version:** 0.1.3.post7
- **Last upstream commit:** `79d15e6` — "Merge PR #748: avoid sending empty content entries in assistant messages"
- **Snapshot date:** 2026-02-16
- **License:** MIT

## What We Took

The entire nanobot codebase at the commit above, including:
- `nanobot/` — Python agent package (agent loop, tools, channels, providers, config, cron, sessions, skills)
- `bridge/` — WhatsApp bridge (TypeScript/Node.js, Baileys)
- `workspace/` — Template workspace files (AGENTS.md, SOUL.md, USER.md, TOOLS.md)
- `tests/` — Test suite (55 tests)
- `Dockerfile` — Container build
- `pyproject.toml` — Package definition (modified for our project)

## What We Changed From Day One

- Project renamed to **hive-office-agents**
- `pyproject.toml` updated with our project identity
- Fresh git history (upstream 395 commits not carried over)
- `CLAUDE.md` added for project knowledge
- This file (`NANOBOT_BASELINE.md`) added for attribution

## Upstream Sync Policy

We are **not** a fork. We track upstream manually if needed:
```bash
# To check what changed upstream since our snapshot:
git clone --depth=1 https://github.com/HKUDS/nanobot /tmp/nanobot-latest
diff -rq /tmp/nanobot-latest/nanobot/ ./nanobot/ --exclude=__pycache__
```
