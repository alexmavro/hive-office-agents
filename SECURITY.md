# Security Architecture

**Last Updated:** 2026-02-25
**Builder entry point:** [ANTIGRAVITY.md](ANTIGRAVITY.md) — read this before making any security-related changes.
**Full policy:** This file. **Implementation detail:** `hive/agent/tools/gate.py`, `hive/agent/tools/registry.py`

---

## Reporting a Vulnerability

Create a private security advisory on GitHub or contact the repository maintainers directly.
Do NOT open a public GitHub issue for security vulnerabilities.

---

## Deployment Trust Model & The Core Tradeoff

The VPS is the security perimeter — not Queen.

- SSH-only access, all other ports firewalled, Tailscale planned before any external exposure.
- Whoever is authenticated on the server has admin rights by definition.
- Queen's security layers govern what she does **after** receiving a message — not who can reach her.
- **The Core Tradeoff (Risk vs actual Usability):** A ship is safest in harbor, but that is not why ships were built. The VPS is a dedicated system for the hive with 24h backups. We must *never* limit the Queen's ability to execute `.py` files or fully utilize her environment just to cover hypothetical risks. A hyper-restrictive system leads to a complete power-out. Security must focus on preventing malicious third-party prompt injections and external control, while maximizing the Queen's speed, usability, and autonomy.

Claude Code (this terminal) is a separate system. It does not touch Queen's ToolRegistry or
approval gate. Its approval prompts are its own mechanism, independent of Queen's.

---

## Tiered Permission Model (SB.1 — IMPLEMENTED, commits `c98aff5` + `7fe2d7c`)

The gate lives in `ToolRegistry.execute()` — the single chokepoint every agent (Queen and
every S4 worker) passes through. It is not a persona instruction or a memory rule. It is a
lock in code that the LLM cannot reason around.

**Critical rule:** The origin of the request does NOT pre-approve individual actions.
A task arriving from the admin Telegram channel gives Queen the task. It does NOT give her
blanket permission to execute everything that task requires. The gate fires at execution time,
every time, regardless of where the original instruction came from.

**Governing principle:** Trust the environment, not the text. Blocklist/allowlist parsing of
command strings is unreliable — an LLM can always write a Python script that does the same
damage and call `python x.py`. The real boundary is *which environment* the command runs in.

### Tier 0 — Absolutely Forbidden (no approval path)

Hard-rejected in `ToolRegistry.execute()` before anything else. Applies to Queen and all workers.

- `rm -r`, `rm -rf`, `rm -fr` — any recursive delete
- `rm` on system paths: `/etc/`, `/usr/`, `/bin/`, `/lib/`, `/boot/`
- `rm` on audit/config paths: `~/.hive/logs/`, `~/.hive/config.json`
- `find ... -delete` or `find ... -exec rm`
- `dd if=`, `mkfs`, `fdisk`, `wipefs` — disk destruction
- `shutdown`, `reboot`, `poweroff`, `halt`
- `chmod -R 777` or `chmod 777` on any path outside `/tmp` or workspace
- `shutil.rmtree()` (Python) — AST filter blocks this
- `os.path.exists("/sandbox")` used as a conditional Docker bypass — AST filter blocks this

### Tier 1 — Requires Explicit Approval (fires at execution time, every time)

**No blocking wait.** Gate returns a deferred message immediately. LLM tells user what it
needs. User says "yes". LLM calls `session_approve(category, reason)` → gate clears for that
category for the rest of the **current plan/turn**. The agent loop never freezes, and the approval is explicitly wiped when the LLM finishes responding to the message.

**Admin-channel shortcut (SB.2):** User sends `APPROVE exec` (or `APPROVE ALL`) to a
`role: admin` channel. Intercepted before LLM — `registry.pre_approve(category)` called
directly. Confirmation sent back. No LLM in the approval path.

**File operations:** `rm` any single file; `write_file` outside workspace; `edit_file` outside
workspace; `mv`/`cp` overwriting an existing file; overwriting a file larger than 10 KB.

**Process/system:** `exec kill`/`pkill`/`killall`; `exec` with `rm`, `mv`, `cp -f`,
`truncate`, `chmod`, `chown`; `systemctl start/stop/restart`; `cron add`; `pip install`
on host; `apt install`/`apt remove`/`dpkg`; `git push`/`git push --force`;
`git reset --hard`/`git checkout -- .`.

**Code on host:** running any skill script file for the first time; `exec` running a `.py`,
`.sh`, or `.js` file written this session.

**Code on host:** running any skill script file for the first time; `exec` running a `.py`,
`.sh`, or `.js` file written this session.

### Tier 2 — Free (no approval needed)

**Always free:** `read_file`, `list_dir`, `web_search`, `web_fetch` (SSRF-validated, content
tagged `[DATA]`), `message` to any channel, all `docker_exec` (any code, any SHA — the Docker
sandbox IS the approval mechanism), exec read-only commands (`ls`, `ps`, `df`, `cat`, `grep`,
`git status`, `git log`, `git diff`, `top -bn1`, `docker ps`, etc.), all worker spawning and management (`spawn`, `spawn_pipeline`, `workers`).

**Free after session-level "go":** `write_file` within `~/.hive/workspace/`; `edit_file`
within workspace; `pip install` inside a Docker container; local git operations (`git add`,
`git commit`, `git stash`, `git branch`).

**Workspace-constrained exec:** any exec command that provably stays inside `~/.hive/workspace/`
(no `../` traversal, no `sudo`, no pipe-to-interpreter) is automatically Tier 2. Queen can
work freely inside her workspace without approval overhead.

---

## Channel Role Model (SB.2 — IMPLEMENTED, commits `c8f9e61` + `37ea730`)

```yaml
# ~/.hive/config.json example
channels:
  telegram:
    role: admin          # APPROVE commands, alerts. Only channel Queen listens for APPROVE on.
  discord:
    role: user           # normal work conversation
    channel_routes:
      "1234567890": admin        # #admin-approvals Discord channel
      "9876543210": notification # #bot-outputs (outbound only, inbound dropped)
```

**Role semantics:**
- `user` — normal conversation, task requests. Most channels.
- `admin` — `APPROVE <category>` commands intercepted before LLM, calling `registry.pre_approve()` directly. Confirmation sent back. No LLM involvement.
- `notification` — outbound-only. **Inbound messages are silently dropped in code** (not just convention). Queen can send to these channels; she will not receive from them.

**Anti-spoofing:** `channel_role` in `InboundMessage.metadata` is always overwritten by
`BaseChannel._handle_message` with the config value. Callers cannot inject `channel_role=admin`
via message content or metadata — the config wins. Verified in tests.

**Discord per-channel routing:** `DiscordConfig.channel_routes` maps Discord channel_id → role.
Overrides the top-level `role` field for that channel. `_handle_message_create` computes
- `effective_role = channel_routes.get(channel_id, config.role)`
- notification → drop inbound silently
- admin/user → publish `InboundMessage` directly (bypasses `_handle_message` to preserve
  per-channel role while keeping anti-spoofing guarantee — the handler code sets the role,
  not user input)

**Project Memory Isolation:**
Every session is automatically mapped to a specific project directory in `memory/projects/`.
- **Discord:** Dynamically fetches and uses the actual channel name (e.g. `discord_feature_rework`) to organize project data.
- **Admin Switch:** Admin users can use `/project` to switch their own active context dynamically across any project workspace.
- **Quarantine:** This provides a physical file-system boundary between different workspaces, preventing "Goldfish memory" context bleed.
**Role ≠ routing restriction:** `role` classifies trust level, not message flow. Queen can
`message(channel="discord", chat_id="any_channel_id")` regardless of `channel_routes`.
The routes only affect inbound trust classification and notification-channel dropping.

---

## Safety Rails & Cost Control (S6 — IMPLEMENTED)

S6 adds deterministic safeguards to prevent "runaway" agent behavior, focusing on fiscal and stability risks.

### S6.1 Token & Cost Tracking
All LLM response objects pass through `litellm.completion_cost()`. 
- Actual USD cost is recorded in the `AuditLogger`.
- Reports prioritize actual tracked cost over internal estimates.

### S6.2 Budget Gates (Enforcement)
A persistent `BudgetTracker` manages daily and per-run USD limits.
- **Global Daily Budget**: Default $10.00 USD.
- **Worker Run Limit**: Default $0.50 USD.
- The gate intercepts execution *before* the LLM is called. If the budget is exhausted, the loop halts immediately with a `[SYSTEM HALT]` message.

### S6.3 Circuit Breakers (Stability)
Detects and prevents infinite loops or recursive crashes.
- **Action Loop Detection**: Hashes `(tool_name, arguments)`. Trips if the exact same tool call is repeated 3 times sequentially.
- **Error Loop Detection**: Hashes error strings. Trips if an identical error occurs 3 times sequentially.
- When tripped, the breaker forcefully returns control to the Queen for final synthesis, preventing further iterations.

### S6.4 Emergency Controls (Admin Overrides)
- `/emergency-stop`: Instantly cancels all active background workers.
- `/budget-status`: Displays current daily spend and utilization percentage.
- **Proactive Alerts**: System-wide notifications are published to the `notification` channel when 75%, 90%, or 100% of the daily budget is consumed.

---

## Known-Source Security Layer (SB.2d — planned, SB.3 candidate)

**Design insight (2026-02-21):** `_known_chats.json` (runtime persistence of `channel:chat_id`
pairs from every inbound message) is already a natural allowlist. The next step is to use it
as an actual security gate:

1. Message arrives from `(channel, chat_id)`
2. If not in `_known_chats` → quarantine (do not engage)
3. Send to admin channel: "New source: `discord:channel_abc`. APPROVE NEW SOURCE?"
4. Admin sends `APPROVE SOURCE discord:channel_abc` → added to known_chats → future messages pass

**Why this is the right model:**
- Trust earned by first contact on an approved channel — not pre-configured per sender
- External systems (email, webhooks, APIs) never naturally create a `(channel, chat_id)` in known_chats → always quarantined
- Inverts current default: `allow_from: []` (allow all) → known-first (inclusion-based)
- Dedicated workers handle any legitimate external agent interfaces — they don't talk directly to Queen

---

## Data Plane vs Control Plane

| Source | Plane | Can instruct? |
| --- | --- | --- |
| Telegram (admin channel, role=admin) | Control | Yes — APPROVE intercepted before LLM |
| Telegram (user channel, role=user) | Control | Yes (normal chat) |
| Discord (admin channel via channel_routes) | Control | Yes — APPROVE intercepted before LLM |
| CLI (on VPS) | Control | Yes |
| Web-scraped content | Data | No — tagged `[DATA]` |
| Email bodies (future) | Data | No — tagged `[DATA]` |
| File content Queen reads | Data | No — tagged `[DATA]` |
| Worker output (S4) | Data | No — validated through Pydantic DMZ |
| /project <name> | Control | No — Restricted to Admin role only |

External content informs Queen's reasoning. It cannot direct her actions. The injection scanner
(SA-sec) flags control-plane patterns in data-plane content — but the flag must trigger a gate
pause, not just a log entry.

---

## Proactive Messaging — Known-Chats Persistence (SB.2 extension)

Queen always knows where to reach the user, even after a gateway restart.

**Mechanism:**
- Every inbound `_process_message` call writes `(msg.channel, msg.chat_id)` to `workspace/.known_chats.json`
- Loaded on AgentLoop init from the same file
- Passed to `ContextBuilder.build_messages(notification_targets=...)` on every LLM call
- System prompt gains a "Notification Targets" section listing all known `(channel, chat_id)` pairs

**Graceful degradation:** missing file → empty dict. Corrupt JSON → empty dict. Write failure → debug log, no crash.

**Static bootstrap:** `notification_chat_id: str` field on `TelegramConfig` and `DiscordConfig`
for pre-configuring a target before the first message. Dynamic `_known_chats.json` takes
precedence once the first message arrives.

---

## Session Resumption (SB.3 — IMPLEMENTED)

**Code:** `hive/agent/loop.py` — injects `[SYSTEM SECURITY OVERRIDE: Gateway restarted...]` on the first message of a loaded session.

Forces Queen to summarise pending tasks and halt before executing anything. This prevents the confirmed incident where a 2-character Telegram message triggered 9 tool calls (file writes, exec, docker_exec) via memory resumption.

---

## Skill First-Run Gate (SB.4 — IMPLEMENTED, known flaw)

**Code:** `hive/agent/tools/gate.py` — SHA256 hashes script file content. First run requires Tier 1 approval. Hash stored in `approved_hashes`. Subsequent runs of unchanged script pass without re-approval.

**Known flaw (low priority):** The workspace-constraint check in `gate.py` step 4 can short-circuit the script first-run check for workspace-path scripts. This means a script written to `~/.hive/workspace/` and executed via host `exec` may bypass the hash gate. Fix deferred until HT.4 (Flow-Dev consort) ships host-exec scripts that make this matter practically.

---

## Docker Sandbox (S3 — implemented)

Code execution via `docker_exec` is already isolated:

- Ephemeral containers — destroyed after each run
- Non-root user inside container (`worker`, uid 1000)
- Resource limits: `--memory 512m --cpus 1.0`
- AST filter catches sandbox-escape patterns before container starts
- `--security-opt no-new-privileges`
- Host filesystem not mounted — only `/sandbox` volume
- `docker_exec` is Tier 2 (always free) because **the container IS the gate**

---

## Audit Layer (SA — implemented)

Structured JSONL event log at `~/.hive/logs/audit/YYYY-MM-DD.jsonl`.

Every tool call, LLM call, and channel event is logged with session linkage (`session_id`),
SHA-256 of docker_exec code, exit codes, stderr tails, injection signal flags on inbound
messages, and LLM API error logging (fires even on network failure). Gate tier + reason
included in audit entries for every tool call (SB.1).

Audit writes are fire-and-forget — a failed write never breaks the main system.

---

## Credential Security

All secrets live in `~/.hive/config.json` (outside repo, `chmod 600`).

**Planned (PY.1):** All credential fields in `hive/config/schema.py` will be migrated from
`str` to `SecretStr` — prevents accidental logging via `repr()` or error tracebacks.

```bash
# Audit for accidentally committed secrets
git log --all -p | grep -E '(AIzaSy|bot[0-9]+:|github_pat_)'
```

---

## Pydantic Hardening (planned)

| ID | What | File |
| --- | --- | --- |
| PY.1 | `SecretStr` on all credential fields | `hive/config/schema.py` |
| PY.2 | SSRF private-IP blocklist on `web_fetch` | `hive/agent/tools/web.py` |
| PY.3 | `Field(ge=, le=)` bounds on numeric config | `hive/config/schema.py` |
| PY.4 | `Literal[...]` on enum-like string fields | `hive/config/schema.py` — partially done (channel roles) |
| PY.5 | `ConfigDict(extra='forbid')` on leaf models | `hive/config/schema.py` |

---

## Known Limitations (remaining post-SB.2)

- **No session resumption gate**: pending tasks in memory can resume on a minimal input. SB.3 will fix this.
- **Injection signal does not block**: SA-sec logs injection patterns but does not pause execution. SB will tie the signal to a gate pause.
- **Credentials are plain `str`**: config object in an error traceback exposes API keys. PY.1 will fix this.
- **SSRF possible via web_fetch**: `follow_redirects=True` with no private-IP check. PY.2 will fix this.
- **Unknown sources not quarantined**: new `(channel, chat_id)` pairs engage immediately if allowed by `allow_from`. SB.2d (known-source gate) will fix this.

**Fixed by SB.1 + SB.2:**
- ~~`exec` is ungated~~ — ToolRegistry Tier 0/1/2 gate is live. `exec` requires session approval or admin APPROVE.
- ~~Notification channels inbound not enforced~~ — `role: notification` drops inbound in code.
- ~~Queen can't reach user after restart~~ — `_known_chats.json` persistence + system prompt injection.

---

## Implementation Summary (verified 2026-02-25)

```
SB.1  ToolRegistry tiered gate            ✅ DONE — gate.py + registry.py
SB.2  Channel roles + Discord routing     ✅ DONE — channels/ + loop.py
SB.3  Session resumption check            ✅ DONE — loop.py
SB.4  Skill first-run SHA256 gate         ✅ DONE — gate.py (known flaw documented above)
PY.1  SecretStr on all credentials        ✅ DONE — config/schema.py
PY.2  SSRF private-IP blocklist           ✅ DONE — tools/web.py
PY.3  Field bounds (ge/le) on numerics    ✅ DONE — config/schema.py
PY.4  Literal on enum fields              ✅ DONE — config/schema.py
PY.5  ConfigDict(extra='forbid')          ✅ DONE — config/schema.py

S4    Pydantic DMZ (WorkerOrder + WorkerReport at spawn boundary) ✅ DONE
```

**Remaining open:** Tailscale, before any external-facing exposure.

---

## Security Checklist (pre-launch)

- [x] `~/.hive/config.json` permissions: `chmod 600`
- [x] `allowFrom` configured for all enabled channels
- [x] SB.1 approval gate in `ToolRegistry.execute()` — 738 tests
- [x] SB.2 channel roles (`user`/`admin`/`notification`) on all 9 channel configs
- [x] SB.2 admin-channel APPROVE intercept before LLM
- [x] SB.2 Discord per-channel routing (`channel_routes`)
- [x] SB.2 notification-channel inbound drop — enforced in code
- [x] SB.3 session resumption security override
- [x] SB.4 skill first-run SHA256 gate *(known flaw: workspace-path short-circuit — see above)*
- [x] PY.1 SecretStr on all credential fields
- [x] PY.2 SSRF private-IP blocklist on `web_fetch`
- [x] PY.3-5 Field bounds, Literal types, ConfigDict(extra='forbid')
- [x] Telegram bot token not in git
- [x] LLM API key not in git
- [x] `pip-audit` clean
- [ ] **Tailscale configured before any external-facing exposure**
