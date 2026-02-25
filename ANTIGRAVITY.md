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
| `ANTIGRAVITY.md` | **The Agent Memory Bank**: Hard-won technical learnings, exact gotchas, and SOPs for future agents. | When you discover a quirk (e.g., `python -c` bypass, or config precedence) that the next agent will definitely trip over if they aren't warned. |
| `/root/Builder_Reports/` | **The Project History & AI Commentary**: A persistent directory containing detailed markdown reports of process, thinking, problems, and walkthroughs for each major session. | At the clean end of a work session before handing back to Alex. |
| `Walkthroughs` | **Ephemeral Session Receipts**: Artifacts in `.gemini/antigravity/brain` highlighting changes during the active session. | Only used during active development; the final polished history goes into `Builder_Reports`. |

> [!TIP]
> **Documentation Sweeps**
> When starting a documentation review task or onboarding into a complex flow, do not guess file names. The single fastest way to grab all top-level context is to run: `find /root/queen-alpha -maxdepth 2 -name "*.md"` or `ls -la /root/queen-alpha/*.md`. This guarantees you don't miss files like `README.md`, `STATUS.md`, `CLAUDE.md`, `SECURITY.md`, and `ANTIGRAVITY.md`.

## 3. The Implementation Loop (How We Work)

As a security-aware project manager, you must follow this exact sequence for every objective:

1. **Alignment & Planning:** Read `CLAUDE.md` and `STATUS.md` first. Propose a plan to Alex. **Do not make silent architectural changes.** If you find a security hole, explain it and propose the fix before mutating the codebase.
2. **Deep-Verification & Execution:** Write the code. You **MUST** run the test suite (`pytest tests/`) and verify your changes. **NOTHING IS REAL UNLESS WE TEST IT.** You must write WAY MORE TESTS specifically targeting edge cases, bounds, and constraints for any new logic. 
    *   **Unit Tests vs. Integration:** Beware unit tests that mock the `__init__` constructor of complex objects (like `AgentLoop`). During SB.2, we discovered critical missing parameters (`workspace=`) and missing registrations (`SessionApproveTool`) because unit tests mocked them out. Write real integration tests.
    *   **The Deep-Verification Protocol:** Do not blindly rely on the happy path. Actively look for execution deadlocks (e.g., missing dependencies causing silent import hangs that block bash pipes), silent failures masquerading as successful log lines, and resource leaks. Always test against adversarial inputs. Before declaring a feature "COMPLETE", you must verify the full integration boundary from configuration schema validation all the way to runtime object instantiation and output.
3. **The Handover (Documentation Phase):**
    *   Tick the completed items in `STATUS.md` and `SECURITY.md`.
    *   Append new architectures or dangerous quirks to the `Memory Bank` below.
    *   **CRITICAL:** Write a comprehensive historical report in `/root/Builder_Reports/` (e.g., `YYYY-MM-DD_Feature_Report.md`). Discuss thought processes, failed approaches, and security learnings.
4. **Commit & Propose Push:** Commit with clear conventional commit messages to the active branch (e.g., `workers`). **DO NOT `git push` without explicitly asking Alex for permission first.**

---

## 4. The Agent Memory Bank (Technical & Security Learnings)

*To all future Antigravity instances: Read this section before touching the codebase. These are blood-written rules.*

### Systemd & Gateway Stability
- The Hive Gateway MUST run as a singleton supervised process (`hive-gateway.service`) via systemd.
- Manual execution of the gateway (tmux/screen) leads to duplicated polling (Telegram Conflict errors) and loss of short-term memory upon restarts.

### Security Boundaries (SB.1 - SB.4) & Gate Integrity
- **The Core Tradeoff (Risk vs. Usability):** A ship is safest in harbor, but that is not what ships are built for. The VPS has 24h backups and is a dedicated environment specifically for the Hive. Do NOT cripple the Queen's ability to run `.py` files or manage her own machine just to block hypothetical internal risks. Security measures must focus strictly on preventing *external* control (e.g., prompt injections from untrusted channels) rather than locking the Queen out of her own execution environment. We must balance autonomy with security, always shining a light on how restrictions affect the Hive's speed and usability.
- **SB.1/SB.2 Tiered Gating:** Tier 0 = Reject, Tier 1 = Approve, Tier 2 = Free. This lives inside `ToolRegistry.execute`.
- **Admin Configuration (The Discord Incident):** Never blindly trust the user's `config.json` default roles. In Discord, we learned the default role could be accidentally set to `"admin"` globally. Rely on `channel_routes` for precision least-privilege scoping, and ensure default handler bypasses enforce user-level permissions unless explicitly whitelisted.
- **Execution Gates & `.py` autonomy:** The Queen requires the ability to write and execute scripts within her workspace to actually *do* things. While we previously considered strict fail-closed methods for `classify_exec`, we must not enact blocks that cause a "power-out" for the Queen. Gating should ensure that *data* (like a scraped webpage) doesn't execute as *code*, but the Queen herself must retain the autonomy to run scripts she intentionally authors.
- **SB.3 Session Resumption:** Ensure that when a gateway restarts, the Queen does not blindly resume executing tools from memory on the first ping. It must halt and explicitly ask "Shall I continue?".

### Memory Structure: Global Identity vs. Active Projects
- **The Dual Memory Architecture:** We abandoned strict Channel Isolation in favor of a unified Identity with distinct Project workspaces. The Queen maintains one overarching persona (`SOUL.md` and `memory/identity/`) that learns globally across all interactions.
- **Project Workspaces (`memory/projects/{name}/`):** Task-specific data and ongoing work belong to Projects, not channels. A user can interact with the same active project from both Telegram and Discord seamlessly.
  - *Note on Projects:* Think of this exactly like "Claude Projects" or "Custom GPTs". When a user creates a new Discord channel, the Queen automatically maps it to a new Project space, becomes curious, and starts asking about her explicit role and objective so she can categorize the context correctly.
- **Session Histories (`sessions/`):** While the Queen's *knowledge* is global and project-based, the literal turn-by-turn conversation DAGs (`DagSession`) remain scoped per chat session key (e.g., `telegram:12345`). This allows trainability across the system without intermingling direct conversational flows.
- **Tool Context Flow:** Any background worker spawned (e.g., `SpawnTool`) inherits the active Project context rather than isolating by channel, ensuring subordinates contribute to the shared architectural goal.
- **Future Functionality — Worker-Team Channel Routing:** Soon, we will allow explicit worker-teams or Hive-Specialists to interact with their respective explicit Discord channels. This prevents the Queen from acting as an annoying intermediary for everything, saving her resources for high-level management rather than message-passing.

### Test Environment & Pytest Execution
- **The Global Path Blank:** `pytest` is NOT installed globally on the VPS. 
- **DO NOT run:** `pytest tests/` or `python3 -m pytest tests/` or `uv run pytest tests/`. These will fail with "Command not found" or "No module named pytest".
- **The Fix:** ALWAYS run tests using the explicit virtual environment path: `./.venv/bin/pytest tests/...`. If you forget this, you will waste 3-4 turns fighting the shell.

### E2E Test Suite & API Costs
- **The Cost of E2E:** Our integration test suite (`tests/` containing `AgentLoop` tests) actually hits the LLM provider API (OpenRouter/Gemini). This costs real money and tokens.
- **When to Run:** DO NOT run the full E2E test suite on every single small iterative change. We only run the E2E test suite when we reach a **milestone debugging phase** or when Alex explicitly asks for it. 
- **The "Unbuilt Bridge" Problem:** E2E suites are highly sensitive. They will often fail because they hit "yet unbuilt bridges" (e.g., a missing config flag we plan to add in the next step). Running them too early causes false-alarms for incomplete milestones. Stick to targeted unit tests (where possible) or manual verification until the milestone is complete.

### Data Obfuscation (PY.1)
- **Token Masking:** Any credential field loaded into memory MUST be cast as a `pydantic.SecretStr` in `schema.py`. Using plain strings leaks raw API keys into log files or crash traces trivially. Always invoke `.get_secret_value()` at the last possible execution jump.

### Worker Delegation (S4) & Pydantic DMZs
- We rejected smolagents' AST Python executor and their sync loops. Our `WorkerLoop` is completely asynchronous, uses `provide_final_answer` grace exits on threshold limits, and executes untrusted code remotely in a controlled `docker_exec`. 
- **The Pydantic DMZ:** The boundary between the Queen and her subordinate Workers is secured by `WorkerOrder` and `WorkerReport` pydantic schemas. Prompt-injected content scraped externally by a worker cannot mutate into a system instruction; it is forcefully serialized into bounded fields before it is allowed back into the Queen's thought process.
- **The Fire-and-Forget Trap (Fixed 2026-02-25):** `WorkerRegistry.spawn_worker()` is intentionally fire-and-forget — it launches a background `asyncio.Task` and returns `WorkerReport(status=PENDING)` immediately. If a pipeline orchestrator calls `await spawn_worker()` and then checks `status == "completed"`, it will **ALWAYS** fail because the returned status is `PENDING`. The fix: `WorkerRegistry.spawn_worker_and_wait()` was added as the sequential-await API. It calls `spawn_worker()` to register/launch, then `await asyncio.shield(task)` to block until the real result is in `_results`. Pipelines MUST use `spawn_worker_and_wait()`. Single spawns keep using `spawn_worker()` (fire-and-forget is correct there).
- **Context Wiring for Tools:** Any tool that produces background bus messages (spawn, spawn_pipeline, cron, message) must have `set_context(channel, chat_id)` called **per-message** in `AgentLoop._set_tool_context()`. If a new tool is added that routes outbound notifications, add it to `_set_tool_context()` or its completions will silently go to `"cli:direct"` — a dead channel nobody reads.

### Skill Forge & Permanence (S5)
- **Separation of Concerns:** We explicitly separated the concept of *Code Generation* from *Skill Packaging*. For S5, the blocker was that the Queen had no way to make her solutions permanent. 
- **The Packaging Layer:** We built the `forge_skill` tool and CLI utilities to strictly enforce `SKILL.md` YAML frontmatter and directory structures (`~/.hive/workspace/skills/`). This solved the permanence issue without over-engineering.
- **smolagents Deferral (S5.5+):** 
  - While `smolagents` (the HuggingFace framework) is recognized as the ultimate engine for autonomous "Python Dev" workers that "think in code" rather than JSON tool calls, it was intentionally deferred. 
  - Why? Because the Queen can already generate code using existing workers and `docker_exec`. Tacking on a massive framework dependency during S5 would have conflated structural packaging with code generation methodology. 
  - **Future integration rule:** If/when `smolagents` is integrated, it must be deployed strictly as a *specialized worker type* connected to our `DockerSandbox`, not as a replacement for the core `WorkerLoop` or the `AgentLoop`.

### S6 Safety Rails & Cost Control
- **Standardized Cost Tracking:** We integrated `litellm.completion_cost()` directly into the `LiteLLMProvider`. This ensures every `LLMResponse` carries an accurate USD cost before it even hits the `AuditLogger` or the `BudgetTracker`. 
- **The MagicMock Trap:** When writing E2E tests with `pytest`, be extremely careful with `MagicMock` usage in `litellm` calls. If a mock returns an object that doesn't strictly follow the expected `completion_cost` return types (or if it's a generic mock that `isinstance(x, float)` fails on), it will crash the `AgentLoop`. We added `isinstance` guards in `loop.py` to prevent this.
- **Circuit Breaker Hashing:** The breaker uses SHA256 hashes of `(tool_name, arguments)` and error strings. To trip correctly, the hash must be reset only when the *content* of the tool call or the *success/failure state* changes. A single successful "message" call usually resets the action loop.
- **Budget Gate Atomicity:** Spend levels are persisted in `~/.hive/workspace/.budget_state.json`. The `BudgetTracker` uses an `asyncio.Lock` to ensure that concurrent workers adding cost don't cause race conditions in the spend total.
- **Proactive CLI Commands:** The `/budget-status` and `/emergency-stop` commands are routed through the system message handler. They provide a vital "dead man's switch" for the user to halt background operations without needing to kill the VPS process.
