# STATUS.md — Build State

**Last updated:** 2026-02-25 | **Tests:** 504/504 passing
**Entry point for new instances → [ANTIGRAVITY.md](ANTIGRAVITY.md)**

---

## Phase 1 Status (S0-S7)

| Milestone | Description | Status | Tag |
|---|---|---|---|
| S0 | Scaffold + Telegram | ✅ Complete | `queen-alpha_S0_baseline` |
| S1 | JSONL DAG memory | ✅ Complete | `queen-alpha_S1_dag_memory` |
| S2 | Memory architecture + retrieval + consolidation + onboarding + factory reset | ✅ Complete | `queen-alpha_S2_memory_arch` |
| S3 | Docker executor (AST filter + ephemeral containers) | ✅ Complete | `queen-alpha_S3_docker_executor` |
| SA | Audit layer (JSONL logging, retention, daily reports) | ✅ Complete | commit `4a3921a` |
| SB | Security Boundaries (tiered gate, channel roles, session resumption, first-run gate) | ✅ Complete | `queen-alpha_SB_security_boundaries` |
| S4 | Hive Manager (worker spawning, registry, pipeline) | ✅ Complete (spawn bug fixed 2026-02-25) | `queen-alpha_S4_hive_manager` |
| S5 | Skill Forge (forge_skill tool + CLI packaging) | ✅ Complete | committed |
| S6 | Safety Rails (budget gates, circuit breakers, emergency controls) | ✅ Complete | `queen-alpha_S6_safety_rails` |
| **S7** | **Emission stream (WebSocket live observation)** | 🔲 **Not started** | — |

**Phase 1 closes when S7 is complete.**

---

## SB Security Checklist (verified 2026-02-25 against code)

| Item | Status | Code location |
|---|---|---|
| SB.1 Tiered gate (Tier 0/1/2) | ✅ Live | `hive/agent/tools/gate.py`, `hive/agent/tools/registry.py` |
| SB.2 Channel roles + Discord routing + known-chats | ✅ Live | `hive/channels/`, `hive/agent/loop.py` |
| SB.3 Session resumption security override | ✅ Live | `hive/agent/loop.py` line ~752 |
| SB.4 Skill first-run SHA256 gate | ✅ Live (logic flaw noted) | `hive/agent/tools/gate.py` |
| PY.1 SecretStr on all credential fields | ✅ Live | `hive/config/schema.py` |
| PY.2 SSRF private-IP blocklist on web_fetch | ✅ Live | `hive/agent/tools/web.py` |
| PY.3 Field bounds (ge/le) on numeric config | ✅ Live | `hive/config/schema.py` |
| PY.4 Literal on enum fields | ✅ Live | `hive/config/schema.py` |
| PY.5 ConfigDict(extra='forbid') on leaf models | ✅ Live | `hive/config/schema.py` |
| Tailscale | ❌ Pending | Required before any external-facing exposure |

**SB.4 known flaw:** Workspace-constraint check in `gate.py` step 4 can short-circuit the script first-run approval check. Low priority until HT.4 (Flow-Dev) ships host-exec scripts. See SECURITY.md.

---

## S7 — Emission Stream (next to build)

**Goal:** Real-time JSON event stream over WebSocket (port 9100). Tool calls, worker lifecycle, budget heartbeat every 30s. Read-only observation. `hive stream` CLI tail command.

**Key files to create:**
- `hive/gateway/stream.py` — WebSocket server
- Hook: subscribe a `StreamSubscriber` to the existing `MessageBus`

**Key constraints:**
- Default binding: `127.0.0.1` only (no public exposure)
- Auth: bearer token from `config.json` when exposed over network
- Read-only. No control channel.
- Rate-limit to 10 events/second. Buffer/batch if exceeded.
- Heartbeat ping/pong every 15s, drop silent clients after 3 missed pongs.

**Test criteria:**
- [ ] WebSocket server starts with gateway
- [ ] `hive stream` connects and receives events
- [ ] Tool call events appear within 1s of execution
- [ ] Worker spawn/complete events appear
- [ ] Budget heartbeat fires every 30s
- [ ] Multiple clients can connect simultaneously
- [ ] Server doesn't crash when all clients disconnect

**Config additions needed first:** `stream_token: SecretStr` in `hive/config/schema.py`

---

## Phase 2 Roadmap (post-S7)

**Full strategic doc:** `/root/alex_notes/hive-office_main-system_implementation_plans.md`

### Recommended Build Order

| # | Plan | Track | Effort | Unlocks |
|---|---|---|---|---|
| 1 | **A.2** Instructor integration | A | 2-4h | Structured LLM output for all downstream |
| 2 | **A.3** ai-bom compliance scan | A | 2-3h | Audit trail, EU AI Act |
| 3 | **B.1** n8n deployment | B | 4-6h | External workflows, Gmail, Calendar |
| 4 | **A.1** S7 Stream | A | 6-8h | ← already in Phase 1, closes it |
| 5 | **B.2** Docling ingestion | B | 4-6h | Document parsing (PDF/DOCX/etc.) |
| 6 | **HT.1** Hive-Team framework | C | 8-12h | Required before any team |
| 7 | **A.4** Crawl4AI scraping | A | 3-4h | STORM research backend |
| 8 | **HT.2** Research-Team (STORM) | C | 10-16h | First real Hive-Team |
| 9 | **B.3** Dropzone watcher | B | 6-8h | File ingestion (Syncthing) |
| 10 | **HT.4** Flow-Dev consort | C | 6-8h | Internal automation |
| 11 | **HT.3** Writing-Team | C | 8-12h | co-writer-hive integration |

**~65-95h total. Full specs in `/root/alex_notes/hive-office_main-system_implementation_plans.md`.**

### Key Pre-work Before Building Phase 2

1. **WorkerReport schema conflict (before A.2):** Plan adds `artifacts`, `lessons`, `token_cost` fields. Current `hive/agent/worker/schema.py` has different fields. Reconcile — do not create two parallel `WorkerReport` classes.
2. **Config schema additions:** A.1 needs `stream_token: SecretStr`. B.1 needs `n8n_api_key: SecretStr`. B.2 needs `docling_url: str`. Add to `hive/config/schema.py`.
3. **Port map:** 5678=n8n, 5001=Docling, 9100=stream, 8384=Syncthing. No conflicts currently.
4. **Consort promotion not yet implemented:** `memory/workers/` listed in S4 design but unverified in `initialize_memory_hierarchy()`. Verify before HT.4.
5. **STORM/dspy/Gemini triple (HT.2):** Test `STORMWikiRunner` with `gemini/gemini-flash` before building ResearchTeam class.
6. **n8n credential isolation is non-negotiable:** No external service credentials in `~/.hive/config.json`.

### Phase 2 Deferred Items

| Item | When |
|---|---|
| Inbox Sentinel (email triage) | After HT.3 |
| Calendar integration | Phase 3 |
| Web dashboard (React) | Phase 3 |
| GPU infra (VibeVoice, local LLMs) | Phase 3+ |
| n8n-Architect consort | After B.1 proven |
| Invoice extraction workflow | After B.2 proven |
| LangFuse observability | Phase 3 |

---

## Git Tags (phase gates)

| Tag | Milestone |
|---|---|
| `queen-alpha_S0_baseline` | S0 complete |
| `queen-alpha_S1_dag_memory` | S1 complete |
| `queen-alpha_S2_memory_arch` | S2 complete |
| `queen-alpha_S3_docker_executor` | S3 complete |
| `queen-alpha_SB_security_boundaries` | SB complete |
| `queen-alpha_S4_hive_manager` | S4 complete |
| `queen-alpha_S6_safety_rails` | S6 complete |
| `queen-alpha_S7_emission_stream` | S7 complete — Phase 1 closed |

---

*For full historical build log, decision record, and architecture learnings: see git log and ANTIGRAVITY.md.*
