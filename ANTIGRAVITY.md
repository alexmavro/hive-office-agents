# ANTIGRAVITY.md — Builder Entry Point

**Read this first. Every time. All builders: human developers and AI instances.**

This is the single entry point for the `queen-alpha` (hive-office-agents) repository.
Everything else is referenced from here with clear intent.

---

## Document Map (MECE)

| Document | Purpose | When to read |
|---|---|---|
| **ANTIGRAVITY.md** (this file) | Builder entry point. NO-GO list. Process rules. Lessons. Architecture traps. Nav hub. | **Always first** |
| [VISION.md](VISION.md) | Product vision. Architecture. Design philosophy. Why things are built the way they are. | When understanding *what we're building* or *why* a design choice was made |
| [STATUS.md](STATUS.md) | Living roadmap. Current build state. Phase 1/2 plans. SB checklist. Next step spec. | When picking up where we left off. Start here after ANTIGRAVITY. |
| [SECURITY.md](SECURITY.md) | Security policy. Tiered gate specs. SB implementation details. Known limitations. | When building anything security-related. Reference spec. |
| [README.md](README.md) | User-facing. Quick start. CLI. Config. | For new users setting up — not for builder work |

**workspace/ files (runtime, not builder docs):**

| File | Purpose |
|---|---|
| `workspace/SOUL.md` | Queen's identity and operational rules. Ships with every instance. |
| `workspace/AGENTS.md` | Agent self-knowledge: capabilities, tool reference, restart commands. |
| `workspace/TOOLS.md` | Tool usage patterns and examples for the Queen. |
| `workspace/HEARTBEAT.md` | Proactive wake-up context. |
| `workspace/memory/MEMORY.md` | Memory hierarchy template and reading instructions. |

---

## NO-GO (do not build without explicit direction from Alex)

- **WhatsApp channel** — security risk. Deprioritized indefinitely.
- **ClawHub / external skill marketplace** — not aligned with quality-over-quantity strategy.
- **LangChain, CrewAI, vector DBs** — no heavy framework dependencies.
- **n8n credentials in config.json** — external service credentials stay in n8n's store, never `~/.hive/config.json`.
- **Two parallel `WorkerReport` schemas** — reconcile before adding Instructor (A.2). One class, extended.
- **Blocking asyncio in tool execution** — all tool execution paths are async. No `time.sleep`, no blocking I/O.
- **Direct user messaging from workers** — workers cannot call `message`. All output routes through Queen.
- **Workers spawning workers** — only Queen spawns workers currently. Future sub-spawning: children are Temps only.

---

## Process Rules

### How We Work

- Agile. Build plan is living, not a contract.
- Builder (Antigravity) is always free to suggest different approaches to Alex.
- Alex (she/her) tests live on Telegram/Discord. AI builders test via pytest.
- **Two-layer testing:** automated (`pytest tests/`) + live channel testing by Alex.
- `pytest tests/` must pass before declaring any task complete. 504 tests as of 2026-02-25.
- Read `ANTIGRAVITY.md` + `STATUS.md` at every session start. Update both when something significant happens.

### Commit Discipline

```
type(scope): description
```
Examples: `fix(S4): resolve pipeline deadlock`, `feat(S7): add WebSocket stream`, `test(S6): patch safety coverage`

Gate commits at phase boundaries. Git tags at milestones (`queen-alpha_SX_name`).
See STATUS.md for current tag inventory.

### Gateway After Code Changes

```bash
sudo systemctl restart hive-gateway
journalctl -u hive-gateway -n 50 -f
```
Do not use screen/tmux/nohup — duplicated process polling breaks everything.

### Testing Strategy

```bash
./.venv/bin/pytest tests/ --ignore=tests/integration -q    # Full unit suite
./.venv/bin/pytest tests/integration/ -v                    # E2E (hits real Gemini API, slow)
./.venv/bin/pytest -m "not docker" -q                       # Skip Docker sandbox tests
```

---

## Where We Are Right Now (2026-02-25)

**Phase 1 (S0-S7): 6/7 complete.** S7 (emission stream) is the last step.
**504 tests passing.** No known regressions.

**Immediate next step: build S7.** See STATUS.md for the full S7 spec.

After S7, Phase 2 begins. Full plan in `/root/alex_notes/hive-office_main-system_implementation_plans.md`. Summary in STATUS.md. Build order starts with A.2 (Instructor), then A.3, B.1, A.1 (S7 already done), B.2, HT.1...

---

## Architecture Quick Reference

See VISION.md for full architecture. Short version:

```
Hive-Queen  (LAW, root, crowned)
├── Hive-Teams     (multi-worker collaborative workflows — Phase 2)
│   ├── Research-Team (STORM, HT.2)
│   └── Writing-Team  (co-writer bridge, HT.3)
├── Workers
│   ├── Temps       (ephemeral, one task, self-terminate)
│   └── Consorts    (promoted Temps, persistent memory/workers/{name}/)
└── Skill Forge (S5) — Queen creates reusable skills
```

**Two execution modes (always know which you're using):**

| | Tool | Scope | Gate |
|---|---|---|---|
| Host shell | `exec` | Root on VPS. Permanent. | SB.1 Tier 0/1 — gated |
| Sandbox | `docker_exec` | Ephemeral container. Isolated. | Always free (container IS the gate) |

**Key files:**

| File | Role |
|---|---|
| `hive/agent/loop.py` | AgentLoop — central ReAct engine |
| `hive/agent/tools/gate.py` | SB.1 tiered gate — Tier 0/1/2 classification |
| `hive/agent/tools/registry.py` | ToolRegistry — all tool exec passes through here |
| `hive/agent/worker/registry.py` | WorkerRegistry — concurrency, lifecycle, spawn_worker_and_wait |
| `hive/agent/tools/worker_tools.py` | spawn / spawn_pipeline tools |
| `hive/agent/budget.py` | BudgetTracker — daily + per-worker USD limits |
| `hive/agent/circuit_breaker.py` | SHA256 action + error loop detection |
| `hive/config/schema.py` | All config models — SecretStr on all credentials |
| `hive/agent/context.py` | Context builder — system prompt assembly |
| `hive/agent/consolidation.py` | Signal-based memory write |
| `hive/bus/` | MessageBus — async pub/sub routing |
| `hive/audit/` | AuditLogger — JSONL event stream |

---

## Builder Lessons & Traps (Agent Memory Bank)

### Agent Loop Architecture
- The agent loop is ReAct (Reason + Act). Max 20 iterations. Tool calls are JSON-structured.
- `ToolRegistry.execute()` is the chokepoint — ALL tools from ALL agents pass through it. The SB.1 gate lives here. Add new tools to the registry; never call them directly.
- `AgentLoop._set_tool_context()` **must** include any tool that publishes bus messages. Missing from here → messages silently go to `"cli:direct"` (a dead channel). Fixed for `SpawnPipelineTool` after discovering this the hard way.
- New Tier 1 tool categories must be added to BOTH `gate.py` and `SECURITY.md`.

### Memory Architecture
- Two layers: core (`queen-alpha/workspace/`, git-tracked) vs personal data (`~/.hive/workspace/`, wipeable).
- Identity files always loaded; other memory sections loaded on-demand by retrieval relevance.
- `report_task` is the Queen's self-learning mechanism — signal → consolidation → memory write.
- 6 signal types: `workflow`, `failure`, `correction`, `decision`, `pattern`, `skill_created`.

### Session Architecture
- JSONL DAG sessions. Each message is a node with `parent_id`.
- `build_context()` reconstructs the branch for the LLM.
- `compact()` embeds summaries in the tree — reduces token cost on long sessions.

### Worker Delegation (S4) & Pydantic DMZ
- `WorkerLoop` is a subclass of `AgentLoop` with restricted tools.
- Workers receive: `docker_exec`, `web_search`, `read_file`, `write_file`, `report_task`. Not `exec`, `spawn`, `message`.
- Worker ↔ Queen boundary: `WorkerOrder` + `WorkerReport` Pydantic models. External content that workers scrape is serialised into bounded schema fields before re-entering Queen's context. Prompt injection cannot become an instruction.
- **The fire-and-forget trap:** `spawn_worker()` returns `WorkerReport(status=PENDING)` immediately. If pipeline code checks `status != "completed"` against a fire-and-forget call, it always fails. Use `spawn_worker_and_wait()` for sequential pipeline steps.
- **Context wiring rule:** Any tool that produces background bus messages must have `set_context(channel, chat_id)` called per-message in `AgentLoop._set_tool_context()`.

### Security Gate (SB)
- Gate is in `ToolRegistry.execute()` — code, not persona. LLM cannot reason around it.
- Tier 0 = hard reject. Tier 1 = deferred return (LLM must call `session_approve`). Tier 2 = always free.
- Admin-channel `APPROVE <category>` intercepts BEFORE the LLM — `registry.pre_approve()` called directly.
- `channel_role` in `InboundMessage.metadata` is always overwritten by config. Cannot be spoofed.
- **SB.4 known flaw:** Workspace-constraint check in `gate.py` step 4 can short-circuit the script first-run SHA256 gate for workspace-path scripts. Low priority until HT.4 (Flow-Dev). Don't mark it fixed.
- Session approvals (SB.1) are turn-scoped: wiped when Queen finishes processing the current message.

### Skill Forge (S5)
- Separation of concerns: code generation (workers + docker_exec) is separate from skill packaging (forge tool).
- `SkillForgeTool` validates kebab-case names (`^[a-z0-9-]+$`), enforces YAML frontmatter, atomically writes. Rollback on error: partial directories are `shutil.rmtree`'d.
- Skills live: system (`hive/skills/`) vs user-created (`~/.hive/workspace/skills/`). User skills take priority (workspace-first loading).

### Safety Rails (S6)
- `BudgetTracker` uses `asyncio.Lock` for concurrent `add_cost` writes. State persisted in `.budget_state.json`.
- Day rollover: `_load_state()` checks today's date vs persisted date. Mismatch → clean slate.
- Budget gate is `>=` (not `>`). $1.00 / $1.00 daily = halted.
- `CircuitBreaker` hashes `(tool_name, arguments)` with SHA256. Hash changes on ANY argument change → counter resets. Counter only tracks sequential identical calls.
- The MagicMock trap: `litellm.completion_cost()` must return a `float`. Generic mocks fail `isinstance` guard in `loop.py`. Use specific return values in tests.

### Phase 2 Navigation Rules (added 2026-02-25)
- **Canonical strategic doc:** `/root/alex_notes/hive-office_main-system_implementation_plans.md`
- **WorkerReport schema conflict before A.2:** Reconcile existing `hive/agent/worker/schema.py` `WorkerReport` with the Instructor plan's fields BEFORE implementing A.2. Don't create two parallel schemas.
- **Config additions needed:** `stream_token: SecretStr` (A.1), `n8n_api_key: SecretStr` (B.1), `docling_url: str` (B.2). Add to `hive/config/schema.py`.
- **Port map:** 5678=n8n, 5001=Docling, 9100=S7 stream, 8384=Syncthing. No current conflicts.
- **Consort promotion path:** `memory/workers/{name}/` is documented in S4 design but verify `initialize_memory_hierarchy()` creates this before HT.4.
- **STORM/dspy/Gemini triple (HT.2):** Test `STORMWikiRunner` with `gemini/gemini-flash` in isolation BEFORE building ResearchTeam. STORM defaults to OpenAI model names.
- **A-track test-before-ship:** A.2 (Instructor) and A.4 (Crawl4AI) bring large dependencies. Create standalone test files that can be skipped in CI before wiring into the production loop.

### Async Patterns
- All gateway, channel, and bus operations are `asyncio`-native. No blocking I/O.
- `asyncio.create_task()` is fire-and-forget — the task runs when the event loop yields. Tests need `await asyncio.sleep(0)` looped a few times to drain pending tasks before asserting.
- File I/O in `BudgetTracker` uses `asyncio.to_thread` — correct pattern for blocking disk reads.

---

## Environment Reference

| Component | Value |
|---|---|
| OS | Ubuntu Linux 6.8.0 |
| Python | 3.12.3 |
| Venv | `/root/queen-alpha/.venv/` |
| hive CLI | `pip install -e ".[dev]"` in venv |
| Config | `~/.hive/config.json` (chmod 600) |
| Tests | 504/504 passing (2026-02-25) |
| Queen model | `gemini/gemini-3-pro-preview`, maxTokens 65536 |
| Git identity | Lexi-Energy (noreply) |

**Activate venv:**
```bash
source /root/queen-alpha/.venv/bin/activate
```

---

## Builder Reports (session logs)

Detailed session findings (bugs fixed, test coverage added, architectural decisions) are in:
`/root/Builder_Reports/` — named `YYYY-MM-DD_Session-Description.md`

Most recent: `2026-02-25_Spawn-Fix-and-S5-S6-Audit.md`

---

*ANTIGRAVITY.md is the living memory of every builder who has worked on this repo.*
*Keep it honest. Keep it current. Update it when something breaks your assumptions.*
