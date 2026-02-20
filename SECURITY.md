# Security Architecture

**Last Updated:** 2026-02-20
**Full analysis:** `reference-repos/pydantic-governance.md` (Security Officer document)

---

## Reporting a Vulnerability

Create a private security advisory on GitHub or contact the repository maintainers directly.
Do NOT open a public GitHub issue for security vulnerabilities.

---

## Deployment Trust Model

The VPS is the security perimeter — not Queen.

- SSH-only access, all other ports firewalled, Tailscale planned before any external exposure
- Whoever is authenticated on the server has admin rights by definition
- Queen's security layers govern what she does **after** receiving a message — not who can reach her

Claude Code (this terminal) is a separate system. It does not touch Queen's ToolRegistry or
approval gate. Its approval prompts are its own mechanism, independent of Queen's.

---

## Tiered Permission Model (SB — planned build track)

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

Queen sends approval request to all `role: admin` channels. Waits on asyncio.Event (5-min
timeout → auto-reject). No action proceeds until YES arrives. Workers cannot bypass this.

**File operations:** `rm` any single file; `write_file` outside workspace; `edit_file` outside
workspace; `mv`/`cp` overwriting an existing file; overwriting a file larger than 10 KB.

**Process/system:** `exec kill`/`pkill`/`killall`; `exec` with `rm`, `mv`, `cp -f`,
`truncate`, `chmod`, `chown`; `systemctl start/stop/restart`; `cron add`; `pip install`
on host; `apt install`/`apt remove`/`dpkg`; `git push`/`git push --force`;
`git reset --hard`/`git checkout -- .`.

**Code on host:** running any skill script file for the first time; `exec` running a `.py`,
`.sh`, or `.js` file written this session.

**Workers (S4):** spawning any new worker; promoting a Temp to Consort; changing worker tool
permissions.

### Tier 2 — Free (no approval needed)

**Always free:** `read_file`, `list_dir`, `web_search`, `web_fetch` (SSRF-validated, content
tagged `[DATA]`), `message` to any channel, all `docker_exec` (any code, any SHA — the Docker
sandbox IS the approval mechanism), exec read-only commands (`ls`, `ps`, `df`, `cat`, `grep`,
`git status`, `git log`, `git diff`, `top -bn1`, `docker ps`, etc.).

**Free after session-level "go":** `write_file` within `~/.hive/workspace/`; `edit_file`
within workspace; `pip install` inside a Docker container; local git operations (`git add`,
`git commit`, `git stash`, `git branch`).

---

## Channel Role Model (SB.2 — planned)

```yaml
channels:
  telegram_main:   role: user    # normal conversation, task updates
  telegram_admin:  role: admin   # approval requests + YES/NO responses only
  cli:             role: admin   # always admin when SSH'd in
```

- Approval requests go to `role: admin` channels only
- Only `role: admin` channels can send valid approval responses
- A `role: user` channel message saying "yes" mid-conversation cannot unblock a pending gate
- Swap messengers (Signal, Matrix, Discord) by changing config, not code

---

## Data Plane vs Control Plane

| Source | Plane | Can instruct? |
| --- | --- | --- |
| Telegram (admin channel) | Control | Yes |
| CLI (on VPS) | Control | Yes |
| Telegram (user channel) | Control | Yes (normal chat) |
| Web-scraped content | Data | No — tagged `[DATA]` |
| Email bodies (future) | Data | No — tagged `[DATA]` |
| File content Queen reads | Data | No — tagged `[DATA]` |
| Worker output (S4) | Data | No — validated through Pydantic DMZ |

External content informs Queen's reasoning. It cannot direct her actions. The injection scanner
(SA-sec) flags control-plane patterns in data-plane content — but the flag must trigger a gate
pause, not just a log entry.

---

## Session Resumption (SB.3 — planned)

When a new session starts and Queen has pending tasks in memory, she MUST:

1. Describe the pending tasks
2. Ask "shall I continue?" explicitly
3. Wait for a response before touching any tool

This is a code check in session initialisation, not a memory instruction. It prevents the
confirmed incident where a 2-character Telegram message triggered 9 tool calls because Queen
loaded a pending task from memory and interpreted the message as "continue."

---

## Skill First-Run Gate (SB.4 — planned)

A skill script file (`.py` / `.sh` registered as a skill) requires explicit Tier 1 approval
the first time it runs. This prevents self-written skills from auto-executing and
auto-scheduling themselves via cron without human review.

The `if not os.path.exists("/sandbox")` Docker bypass pattern must be blocked in the AST
filter — the sandbox must be structural, not a runtime check a skill can opt out of.

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
messages, and LLM API error logging (fires even on network failure). 305 tests.

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
| PY.4 | `Literal[...]` on enum-like string fields | `hive/config/schema.py` |
| PY.5 | `ConfigDict(extra='forbid')` on leaf models | `hive/config/schema.py` |

---

## Known Limitations (pre-SB)

- **`exec` is ungated**: Queen runs arbitrary host shell commands as root. Audit log records them but does not block. SB.1 will fix this.
- **No session resumption gate**: pending tasks in memory can resume on a minimal input. SB.3 will fix this.
- **Injection signal does not block**: SA-sec logs injection patterns but does not pause execution. SB will tie the signal to a gate pause.
- **Credentials are plain `str`**: config object in an error traceback exposes API keys. PY.1 will fix this.
- **SSRF possible via web_fetch**: `follow_redirects=True` with no private-IP check. PY.2 will fix this.

---

## Build Order

SB must complete before S4. Workers inherit the ToolRegistry gate — if the gate isn't there
before S4 ships, every worker gets an ungated root shell.

```
SB.1  ToolRegistry tiered gate       ← unblocks S4
SB.2  Channel role config + routing
SB.3  Session resumption check
SB.4  Skill first-run approval

[parallel] PY.1–PY.5  Pydantic hardening  ← no dependencies, ~2 hours total

S4    Hive Manager  ← after SB.1
      + Pydantic DMZ (WorkerOrder + WorkerReport) at spawn layer
```

---

## Security Checklist (pre-launch)

- [ ] `~/.hive/config.json` permissions: `chmod 600`
- [ ] `allowFrom` configured for all enabled channels
- [ ] SB.1 approval gate in `ToolRegistry.execute()` — live and tested
- [ ] SB.2 channel roles configured (`role: admin` on at least one channel)
- [ ] SB.3 session resumption check — live and tested
- [ ] SB.4 skill first-run gate — live and tested
- [ ] PY.1 `SecretStr` on all credential fields
- [ ] PY.2 SSRF validator on `web_fetch`
- [ ] Telegram bot token not committed to git
- [ ] LLM provider API key not committed to git
- [ ] `pip-audit` clean
- [ ] Tailscale configured before any external-facing exposure
