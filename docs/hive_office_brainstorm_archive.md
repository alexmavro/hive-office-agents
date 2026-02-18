# Hive-Office: brainstorm archive

**Purpose:** This file compresses the 38 vision/brainstorm documents into a single reference. Everything here is "future work" or "context for later decisions." Nothing here is actionable for the current build phase. If you're VPS-Claude, ignore this file unless the strategist points you at a specific section.

**Date archived:** 2026-02-17

---

## 1. The vision (what we're building toward)

A sovereign digital back office. You do the human things (client empathy, strategy, living your life). An autonomous digital staff handles the machine work. Not a collection of chat windows. A persistent, asynchronous fleet that takes objectives, breaks them down, executes, and delivers finished output.

The Queen orchestrates. Workers execute. Everything runs on bare metal you control.

## 2. The hive architecture (target state)

Queen-Alpha sits at the center. She doesn't do grunt work. She reads the request, checks the ledger, routes the work. Her job: evaluate, delegate, verify.

Workers are ephemeral Docker containers. They spin up, do one job, report back, die. The "Self-Terminator" protocol. No zombie processes, no context rot, no memory leaks between tasks.

Communication uses strict schemas (Pydantic-validated Orders and Reports). If an Order is malformed, it gets rejected before reaching any worker. If a Report claims success but provides no artifact, the system forces a retry.

## 3. Input channels (future phases)

Three entry points were discussed:

The local dropzone. A Syncthing-linked folder on Alex's desktop. Drop a file in, the Queen picks it up. Challenges to solve later: race conditions (half-synced files), context vacuum (what should the Queen DO with a random file?), and the loop-of-death (output triggers re-processing). Solutions sketched: ignore .tmp/.syncthing files, wait for stable file size, use folder-structure-as-intent (INBOX/Summarize_This, INBOX/Invoice_Check).

The inbox sentinel. API hook into email. She reads incoming mail, categorizes, drafts replies in Alex's voice for the routine stuff. Flags anything requiring human empathy.

The calendar negotiator. Read/write access to schedule. Cross-references energy levels against meeting requests. Books time blocks autonomously.

## 4. Worker templates (future specializations)

Data cleaner: ingests raw client data, writes a Pandas script, runs it in sandbox, returns clean output.

Site weaver: builds static HTML/CSS from text descriptions.

Book drafter: massive context allowance, handles narrative consistency across chapters.

Research worker: web search, source comparison, citation.

Security auditor: uses AST-isolated execution for untrusted code review.

These are templates, not immediate builds. The hive manager (S4) creates the infrastructure to spawn any of them.

## 5. Memory architecture (long-term vision)

Phase 1 is JSONL DAG (porting pi-mono's pattern). This gives branching, time travel, compaction.

Phase 2 (someday): SQLite migration. Adds resolution levels (0=raw log, 1=tactical summary, 2=strategic fact), indexed queries, atomic transactions, branch-depth constraints at the database level.

Phase 3 (far future): semantic clustering over the knowledge dump. Understanding relationships between thousands of notes, not just keyword matching. Possibly vector embeddings, but not until the basics work.

## 6. Self-improvement loop

The skill forge concept: Queen watches what tools she uses, notices patterns, writes new skills to automate repeated workflows. The save_skill tool (the "scribe") lets her create .py skill files that load on restart.

Workspace mapper: she maintains an internal model of what's where on the VPS.

memorize_learning: after solving something hard, she writes the pattern to persistent memory so she doesn't re-derive it.

## 7. Security model

Every worker runs in a Docker sandbox. If a worker reads a poisoned PDF, the blast radius is trapped in a temporary container.

AST safety filter on code execution: parse the Python AST before running, reject dangerous imports (os.system, subprocess, etc).

No worker gets host filesystem access. Communication happens through mounted volumes with strict permissions.

Circuit breaker on the DAG: if a branch accumulates too many failures, it gets killed automatically. No infinite retry loops.

Token budget gate: hard daily spending limit. Queen reports when she's near the cap. Blocks further LLM calls when exceeded.

## 8. Observability

Emission stream (WebSocket server). Live-tail the Queen's decisions from a second terminal. See nodes being created, tools being called, workers spawning and dying. JSON event stream.

The "Black Box Recorder": every command every worker executes gets logged to a central record. You can watch the hive think in real time.

## 9. Framework decisions (settled)

Base kernel: HKUDS/nanobot (Python, lightweight, 3,668 LOC).

NOT using: LangChain, CrewAI, vector DBs, OpenClaw (too opinionated about its own gateway), Agent Zero (interesting but wrong architecture for this use case).

DAG pattern ported from: pi-mono/OpenClaw's session system (TypeScript -> Python).

Sandboxed execution inspired by: smolagents' AST-based code isolation.

LLM routing: LiteLLM (already built into nanobot, supports 16+ providers).

## 10. Infrastructure (settled)

Hetzner VPS. 8 vCPU, 16GB RAM, 320GB disk. Ubuntu.

Python 3.12. Docker. SFTP via Cyberduck for file transfers.

Claude Code on the VPS for building. Gemini Flash for Queen dev/test (cheap, uses the EUR 200 credit). Production model TBD.

## 11. Naming and identity

Project: Hive-Office

Agent: Queen-Alpha (sometimes just "the Queen")

Architecture: Queen + Workers hive model

Workers called: temps, workers, nanobots (depending on context)

The persona should be: confident, direct, principled. Secure. Honest. She has a safetynet but she's not timid. She verifies before claiming success. She cleans up after herself.

## 12. Alternative approaches considered and rejected

Golden Image strategy (pre-built Docker images per worker type): deferred. Too much upfront work. Build generic workers first, specialize later.

Chainlit as UI: rejected. Telegram is simpler and mobile-native.

Multi-agent frameworks (CrewAI, AutoGen): rejected. Too much overhead. We control the orchestration ourselves.

Vector databases for memory: rejected for now. JSONL/SQLite handles the current scale.

## 13. Cost strategy

Builder (Claude Code): subscription, watch message limits.

Queen dev/test: Gemini 2.0 Flash via API (~EUR 0.10-0.30/day during dev).

Queen production: Gemini 2.5 Pro or Claude Sonnet (~EUR 1-3/day depending on volume).

Workers: Gemini Flash or Haiku equivalent via OpenRouter. Pennies per task.

## 14. Phrases and principles worth keeping

"Trust over Speed." Never say "I fixed it" unless you verified it.

"Blind optimism is a failure state."

"She orchestrates; they execute."

"Workers must die." The Self-Terminator protocol.

"Filesystem as interface." The dropzone concept.

"Correct means the function returns expected output. Good means talking to her feels right."

## 15. Coronation protocol behavioral rules (inputs for IDENTITY.md)

These are the specific operational directives from the original Coronation Protocol document. When building IDENTITY.md in step S2, these should be translated into the Queen's behavioral rules:

The Verify rule: Never claim success without evidence. If a command runs without error, check the output file. If a container starts, prove the endpoint is alive. "Exit code 0" is not verification.

The Idempotency rule: Scripts must survive re-runs. Check if a folder exists before creating it. Check if a container is running before starting it. Every script the Queen writes or delegates should be safe to execute twice.

The Clean State rule: No temporary files rotting in the root directory. No test.py left behind. No temp_log.txt accumulating. Clean up your workspace after every task.

The Operational Loop: Analyze -> Plan -> Execute -> VERIFY -> Report. The verify step is the most important. Report must include evidence (logs, file paths, curl output).

The Delegation principle: The Queen does not do grunt work. She builds specialized workers. She orchestrates; they execute.

These five rules are non-negotiable behavioral constraints for the Queen's identity. They separate her from a generic chatbot that hallucinates success.
