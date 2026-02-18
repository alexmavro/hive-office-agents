# Decisions

<!-- Why we chose X over Y. Append-only log. -->
<!-- Format: ## [date] [decision title] -->

<!-- Example:
## 2026-02-18 — Chose JSONL over SQLite for session storage

**Decision:** JSONL append-only files for conversation history.

**Alternatives considered:**
- SQLite: more queryable, but overkill for current scale (<10k messages)
- Plain text: no structure, no branching support

**Reasoning:** JSONL is crash-safe (append-only), human-readable, no migrations needed.
Migrate to SQLite when >50k nodes or complex queries required.

**Outcome:** Working well. Branching and compaction implemented cleanly.
-->
