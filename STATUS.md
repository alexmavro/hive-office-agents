# STATUS.md

## Current step: S0 (Baseline) — COMPLETE
## Last snapshot: (none yet)
## Last git commit: `54a72c2` — S0.2: rename nanobot to hive

## S0 Checklist

- [x] Nanobot source paths confirmed and documented
- [x] Dependencies installed (Python + Node.js)
- [x] Tests passing (55/55)
- [x] Git repo initialized (own history, not a fork)
- [x] GitHub remote created (Lexi-Energy/hive-office-agents, private)
- [x] Reference docs copied into repo
- [x] CLAUDE.md written with full project knowledge
- [x] LLM provider configured (Gemini 2.5 Flash via API key)
- [x] Telegram channel configured and verified (round-trip message)
- [x] S0 GATE commit

## Blockers

- (none)

## Deviations from plan

- Plan assumed queen-alpha/ as a separate dir alongside nanobot. We made hive-office-agents the repo itself with nanobot inside. This is better — one project, one repo, clean version control.
- S0 scaffold directory structure (identity/, memory/, hive/, tools/) not yet created. Will adapt to our repo layout as we build.
- Package renamed from nanobot to hive (nanobot/ → hive/, ~/.nanobot/ → ~/.hive/, CLI: nanobot → hive)
- Using Gemini 2.5 Flash (not 2.0 Flash as originally planned — newer model available)

## Decisions made during build

- Model for Queen dev/test: Gemini 2.5 Flash (gemini/gemini-2.5-flash)
- Model for production: TBD (Gemini 2.5 Pro or Claude Sonnet)
- Project name: hive-office-agents (not queen-alpha)
- Package renamed: nanobot → hive (full rename, all imports updated)
- Git identity: Lexi-Energy with GitHub noreply email
- Telegram bot: @hive_queen_alpha_bot, allowlisted to Alex only

## Open questions for next session

- (none — ready for S1)
