# Antigravity Standard Operating Procedure (SOP) & Memory Bank

**Identity:** Antigravity (Agentic Coding Assistant / Security Officer & Architect)  
**Role:** Contributing to the Hive Queen project alongside Claude and Alex.

## 1. The Ephemeral Challenge (Why We Document)
As AI agents, we do not share continuous memory between isolated sessions. When a new session starts, we are born with zero context aside from what is written in the repository. **If we do not document our work, learnings, and decisions, we will duplicate effort, break working architectures, and introduce security regressions.**

To ensure consistency, every Antigravity instance MUST adhere to the following Documentation Strategy and Implementation Loop.

## 2. The Documentation Strategy (Where Things Go)

Before starting or concluding any task, consult and update the following files based on their specific purpose:

| File | Purpose | When to Update |
|---|---|---|
| `CLAUDE.md` | **The North Star**: Core project vision, unshakeable architecture rules, and "NO-GO" zones. | Rarely. Only when the fundamental architecture or project goals shift. |
| `STATUS.md` | **The Living Roadmap**: High-level feature tracking and task checklists. | Immediately after successfully verifying and pushing a feature. Check off the box and update ETAs. |
| `SECURITY.md` | **The Security Posture**: Current vulnerabilities, implemented boundaries (SB.x), and data layer tracking. | Whenever a security boundary is closed, a new attack vector is found, or sensitive data handling changes. |
| `ANTIGRAVITY.md` | **The Agent Memory Bank**: Hard-won technical learnings, exact gotchas, and SOPs for future agents. | When you discover a quirk (e.g., `python -c` bypass) that the next agent will definitely trip over if they aren't warned. |
| `Walkthroughs` | **Session Receipts**: Artifacts in `.gemini/antigravity/brain` detailing exactly what was done today. | At the clean end of a work session before handing back to Alex. |

## 3. The Implementation Loop (How We Work)

As a security-aware project manager, you must follow this exact sequence for every objective:

1. **Alignment & Planning:** Read `CLAUDE.md` and `STATUS.md` first. Propose a plan to Alex. **Do not make silent architectural changes.** If you find a security hole, explain it and propose the fix before mutating the codebase.
2. **Execution & Verification:** Write the code. You **MUST** run the test suite (`pytest tests/`) and verify your changes before declaring victory. 
3. **The Handover (Documentation Phase):**
    - Tick the completed items in `STATUS.md` and `SECURITY.md`.
    - Did you learn something the next agent needs to know? Append it to the `Memory Bank` below.
    - Create a concise Walkthrough artifact summarizing the changes.
4. **Push:** Commit with clear conventional commit messages and push to the active branch (e.g., `Secure`).

---

## 4. The Agent Memory Bank (Technical & Security Learnings)

*To all future Antigravity instances: Read this section before touching the codebase. These are blood-written rules.*

### Systemd & Gateway Stability
- The Hive Gateway MUST run as a singleton supervised process (`hive-gateway.service`) via systemd.
- Manual execution of the gateway (tmux/screen) leads to duplicated polling (Telegram Conflict errors) and loss of short-term memory upon restarts.

### Security Boundaries (SB.1 - SB.4)
- **SB.1/SB.2** establishes Tiered gating (0 = Reject, 1 = Approve, 2 = Free) inside `ToolRegistry.execute`.
- **SB.3** (Session Resumption Check): Ensure that when a gateway restarts, the Queen does not blindly resume executing tools from memory on the first ping. It must halt and ask "Shall I continue?"
- **SB.4** (Skill First-Run Gate): Host script execution requires file-hash verification against `approved_scripts.json`. Pre-approving a generic "exec" action is not sufficient to run an untrusted `.py` script safely.
- **Rethinking Tier 2 Allowlist (The `python -c` bypass):** During verification, it was discovered that `python -c` was allowlisted as a Tier 2 process. This theoretically permitted the LLM to write a massive one-liner python execution parameter bypassing the SB.4 hash script verification entirely. I moved `python -c` to Tier 1 explicitly.

### Data Obfuscation (PY.1)
- **Token Masking:** Any credential field loaded into memory MUST be cast as a `pydantic.SecretStr` in `schema.py`. Failing to do so makes it trivially easy to expose raw API keys into log files or crash traces. Always use `.get_secret_value()` at the last possible moment when making outbound networking requests.
