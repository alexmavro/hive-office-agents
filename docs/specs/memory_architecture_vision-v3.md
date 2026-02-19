# Memory Architecture Vision

**Date:** 2026-02-18  
**Status:** Brainstorm / System Design  
**Purpose:** Think through the ENTIRE memory system before committing to implementation

---

## THE FUNDAMENTAL PROBLEM

A conversation is not knowledge. A log is not memory. A history is not understanding.

Current state: HISTORY.md is a flat append-only log. MEMORY.md is a manually-edited text file. Both are dumb storage. Neither has structure. Neither has intelligence.

The Queen needs three capabilities that neither provides:

1. **Continuity** - remembering what was said (conversation history)
2. **Knowledge** - remembering what was learned (facts, patterns, solutions)
3. **Agency** - knowing what to do without being told every time (internalized understanding of Alex's world)

Right now we're only solving (1). That's not enough.

---

## THE CORE INSIGHT

Memory types are different. They need different structures. Different triggers. Different lifespans.

**EPHEMERAL MEMORY** (conversation context)
- What: The actual dialogue. User said X, Queen said Y, tool returned Z.
- Lifespan: Hours to days. Gets compressed or pruned.
- Trigger: Every interaction.
- Format: Needs branching (DAG). Needs time-travel. Needs fast retrieval.
- Current solution: JSONL DAG (S1)

**WORKING MEMORY** (active task context)
- What: The current objective. What we're building. What's blocking it. What we've tried.
- Lifespan: Until task completes. Then compresses into long-term.
- Trigger: Task start/end.
- Format: Structured. Project-specific. Active TODO vs Done vs Blocked.
- Current solution: Nothing. This is the gap.

**LONG-TERM MEMORY** (persistent knowledge)
- What: Facts about the world. System state. Learned patterns. User preferences.
- Lifespan: Permanent. Updated, not deleted.
- Trigger: Signal-based. Something important happened.
- Format: Structured. Categorized. Searchable.
- Current solution: MEMORY.md (flat file, manual editing, no structure)

**PROCEDURAL MEMORY** (how to do things)
- What: Workflows that worked. Approaches that failed. Skills. Tools.
- Lifespan: Permanent. Versioned.
- Trigger: Task success/failure. Skill creation.
- Format: Executable scripts + metadata.
- Current solution: Nothing systematic. Skills folder exists but no learning protocol.

**META-MEMORY** (memory about memory)
- What: What the Queen knows she knows. What she knows she doesn't know. Confidence levels.
- Lifespan: Permanent. Self-reflective.
- Trigger: When asked "do you know X?" or when retrieving fails.
- Format: Index. Registry. Capability map.
- Current solution: Nothing. The Queen can't introspect her own knowledge.

---

## THE SELECTION PROBLEM

Current consolidation: "Every 50 messages, summarize."

That's count-based. It treats all messages equally. A conversation about the weather gets the same treatment as a conversation where the Queen successfully deployed a service.

**The right triggers:**

SIGNAL DETECTION - consolidate when something meaningful happens:
- Task completed successfully → extract the working method
- Task failed after retries → capture what didn't work
- User corrected the Queen → this is a lesson
- New tool/skill created → update capability map
- Infrastructure changed → update system state
- Decision made → log the reasoning
- Pattern recognized → create a rule

CAPACITY TRIGGERS - only when context is actually full:
- Context window approaching limit → compress oldest ephemeral
- Working memory getting cluttered → archive completed tasks
- Procedural memory has duplicates → deduplicate and consolidate

TIME TRIGGERS - only for housekeeping:
- Daily: check for stale working memory (abandoned tasks)
- Weekly: review lessons learned, extract patterns
- Never for actual knowledge storage

**The wrong trigger:** "It's been 50 messages."

---

## THE CATEGORIZATION PROBLEM

Everything goes into one bucket. That's wrong.

Different knowledge types need different homes:

**IDENTITY** (who Alex is, what she values)
- user.md - facts about Alex (name, languages, timezone, role)
- constraints.md - non-negotiables (ethics, communication style, boundaries)
- preferences.md - how she likes things done (format, tone, workflow)
- context.md - UNBLURRY business context (without the frameworks/methods)

**SYSTEMS** (infrastructure state)
- vps.md - the Hetzner box (specs, IP, SSH setup, installed services)
- tools.md - what's available (Docker, Python versions, installed packages)
- access.md - credentials location, API keys setup (references, not actual secrets)
- topology.md - how things connect (Telegram → Queen → workers → outputs)

**PROJECTS** (current work)
- hive-office/
  - decisions.md - why we chose X over Y
  - blockers.md - what's stopping progress
  - todos.md - what needs to happen
  - changelog.md - what changed and when
  - context.md - what this project is about

**PROCEDURAL** (how to do things)
- workflows/
  - deploy_service.md - the steps that work
  - debug_container.md - the diagnostic approach
  - backup_data.md - the safety protocol
- fixes/
  - port_conflict.md - known issue, known solution
  - memory_leak.md - symptom → diagnosis → fix
  
**LESSONS** (learned from experience)
- successes.md - approaches that worked, use again
- failures.md - approaches that failed, don't retry
- patterns.md - recurring situations and their solutions

**SKILLS** (executable capabilities)
- Already exists in nanobot
- Needs: metadata about what each skill does, when to use it
- Needs: confidence scores (how reliable is this skill?)

---

## THE RETRIEVAL PROBLEM

Current: dump everything into context. Hope the model figures it out.

That doesn't scale. The Queen needs QUERY-DRIVEN retrieval.

**When to pull what:**

CONTEXT: Always loaded
- identity/ (who Alex is, her constraints)
- Current conversation branch (DAG path to current leaf)
- Active project context (what we're building right now)

ON-DEMAND: Loaded when relevant
- systems/ when making infrastructure decisions
- procedural/ when starting a task similar to something done before
- lessons/ when encountering an error or deciding approach
- skills/ metadata when choosing which tool to use

NEVER: Loaded automatically
- Old conversation branches (only via explicit time-travel)
- Archived projects (only if user references them)
- Raw logs (only for debugging)

**How to decide what's relevant:**

Semantic matching:
- User says "deploy the service" → check procedural/workflows/deploy_service.md
- Error appears → check lessons/failures.md for this error pattern
- User says "like last time" → check recent successes for similar tasks

Explicit triggers:
- Spawning a worker → inject systems/ knowledge about the environment
- Creating a skill → update skills registry
- Making a decision → reference projects/{project}/decisions.md

The prompt builder ASKS for relevant memory. It doesn't assume.

---

## THE LEARNING PROBLEM

The Queen needs to get smarter over time. Not just store more. LEARN more.

**Learning happens when:**

1. **Task succeeds** → extract the method
   - What was the goal?
   - What steps were taken?
   - What worked?
   - Write to procedural/workflows/

2. **Task fails** → extract the lesson
   - What was attempted?
   - Why did it fail?
   - What should be tried instead next time?
   - Write to lessons/failures.md

3. **User corrects** → update the model
   - Queen said X, user said "no, Y"
   - What was the misunderstanding?
   - Update relevant knowledge (identity/, systems/, procedural/)

4. **Pattern emerges** → create a rule
   - Same type of task succeeded 3 times with similar approach
   - Extract the pattern as a workflow
   - Same error occurred 3 times with same fix
   - Extract as a known fix

5. **Skill created** → update capability map
   - New skill added to skills/
   - Log: what it does, when to use it, confidence level
   - Make it discoverable for future tasks

**The learning protocol:**

After every significant interaction:
1. Did something important happen? (signal detection)
2. What category does this belong to? (route to correct memory type)
3. Does this update existing knowledge or create new? (merge vs append)
4. What's the confidence level? (high confidence from success, low from speculation)
5. Write structured entry with metadata (timestamp, category, confidence, source)

Not: "Every 50 messages, dump to MEMORY.md"

---

## THE ONBOARDING PROBLEM

New Queen instance knows nothing about Alex. That's slow.

**Fast initialization via structured intake:**

The first conversation should be a setup protocol. Not chat. Structured questions.

```
QUEEN: First boot. Need baseline context.

1. What's your name and what do you do?
   → writes to identity/user.md

2. Core constraints? (What should I never do?)
   → writes to identity/constraints.md

3. Communication preferences? (Languages, tone, format)
   → writes to identity/preferences.md

4. Current infrastructure? (What systems am I managing?)
   → writes to systems/

5. Active projects? (What are you working on?)
   → writes to projects/

6. Immediate task?
   → creates working memory entry
```

5-10 minutes of structured input. Gets the Queen 80% operational immediately.

This could even be a Telegram form. Multiple choice + short answers. Fast.

**What this enables:**

- No repeating yourself every conversation
- No "remind me again" tax
- Queen knows the constraints from day one
- Queen knows the system topology from boot
- Alex can test actual capabilities immediately, not train context first

**Updates after onboarding:**

- identity/ changes slowly (user.md might never change)
- systems/ updates when infrastructure changes (new service deployed)
- projects/ updates daily (progress, blockers, decisions)
- lessons/ grows continuously (every success/failure)

---

## THE STORAGE FORMAT QUESTION

Different memory types might need different formats.

**EPHEMERAL (conversation):**
- JSONL DAG? (fast append, branching support, time-travel)
- SQLite DAG? (indexed queries, atomic transactions, branch constraints)
- Decision: depends on scale. JSONL for <10k nodes. SQLite after.

**WORKING MEMORY (active tasks):**
- YAML? (human-readable, structured, easy to edit)
- JSON? (programmatic, validated schemas)
- Markdown? (readable by both human and LLM, flexible)
- Decision: probably YAML. Structured but human-readable.

**LONG-TERM (facts/lessons):**
- Markdown? (readable, versionable, flexible)
- SQLite? (queryable, indexed, relational)
- Vector DB? (semantic search, similarity matching)
- Decision: start with Markdown. Migrate to SQLite when search becomes slow. Vector DB only if semantic search is critical (probably not needed).

**PROCEDURAL (workflows):**
- Markdown + code blocks? (readable documentation with executable parts)
- Python modules? (directly executable, testable)
- Decision: Markdown files with embedded Python. Documentation and code in one place.

**META-MEMORY (capability map):**
- JSON? (structured, programmatic)
- YAML? (human-readable)
- Decision: JSON. This is machine-first, human-second.

---

## THE COMPRESSION PROBLEM

Memory grows. Context windows are finite. Compression is inevitable.

**What to compress:**

Ephemeral memory:
- Old conversation branches that aren't active → summarize to single node
- Resolved task context → extract outcomes, discard steps
- Repetitive exchanges → deduplicate patterns

**What NOT to compress:**

Long-term facts (identity/, systems/) → these are already compressed
Procedural workflows → these are reference, not history
Lessons learned → these are distilled knowledge already
Skills → these are executable, don't summarize code

**Compression triggers:**

- Context window approaching limit (capacity trigger)
- User explicitly requests history cleanup
- Task completes → compress working memory into outcomes

**The compression routine:**

1. Identify what's compressible (old conversation branches, resolved tasks)
2. Extract key outcomes (what was learned, what was decided)
3. Write outcomes to appropriate long-term memory
4. Replace ephemeral detail with reference ("see systems/vps.md for deployment details")
5. Mark compressed entries (they still exist, just not loaded by default)

Not: "summarize the last 50 messages into a paragraph"

---

## THE CONFIDENCE PROBLEM

The Queen doesn't know what she knows vs what she's guessing.

**Every memory entry needs confidence metadata:**

- **HIGH** - verified fact (user told her, or she verified via command)
- **MEDIUM** - inferred from context (probably true, not confirmed)
- **LOW** - speculation (might be true, needs verification)

Examples:

```yaml
# identity/user.md
name: Alex
confidence: HIGH
source: user_stated
timestamp: 2026-02-18T10:00:00Z

# systems/vps.md
ip_address: 123.45.67.89
confidence: HIGH
source: verified_ssh
timestamp: 2026-02-18T10:15:00Z

docker_version: 24.0.7
confidence: MEDIUM
source: inferred_from_logs
timestamp: 2026-02-18T10:16:00Z
note: "should verify with docker --version"
```

**Retrieval uses confidence:**

When the Queen retrieves memory, she knows what's verified vs speculative.

- HIGH confidence → state as fact
- MEDIUM confidence → state with caveat ("based on logs, appears to be...")
- LOW confidence → ask for verification before acting

**Confidence updates over time:**

- Speculation becomes verified when checked
- Facts become stale when not verified recently
- The Queen can flag "this fact is old, should recheck"

This prevents hallucination. The Queen knows the difference between "I know" and "I think."

---

## THE HIERARCHY QUESTION

Memory needs structure. But what kind?

**Option A: Flat categories** (current thinking)
```
memory/
  identity/
  systems/
  projects/
  procedural/
  lessons/
  skills/
```

Pro: Simple. Clear categories. Easy to navigate.
Con: No relationships. No hierarchy within categories.

**Option B: Graph structure**
```
Everything is a node. Nodes have relationships.
- Alex (person) → owns → UNBLURRY (project)
- hive-office (project) → uses → VPS (system)
- deploy_service (workflow) → requires → Docker (tool)
```

Pro: Captures relationships. Enables graph queries.
Con: Complex. Overhead. Might be overkill.

**Option C: Hybrid**
```
Flat categories for top level.
Graph relationships within categories.
Identity points to constraints. Projects point to workflows.
```

Pro: Structure where needed, simplicity where possible.
Con: Two systems to maintain.

**Decision criteria:**

- Will the Queen need to answer "what projects use Docker?" (graph query)
- Will the Queen need to understand dependencies? (X requires Y)
- Will the Queen need to trace reasoning? (used workflow A because project B needs feature C)

If yes to these → graph makes sense.
If no → flat categories are sufficient.

My instinct: start flat. Migrate to graph only if queries become complex.

---

## THE SCALE QUESTION

How much memory will the Queen actually accumulate?

**Estimates:**

Ephemeral (conversation):
- 100 messages/day × 365 days = 36,500 messages/year
- At 1KB/message = 36MB/year
- Compressed every 1000 messages → ~365 compression events/year
- After compression: maybe 5-10MB/year retained

Long-term (facts):
- identity/ - dozens of facts, rarely changes → ~10KB
- systems/ - hundreds of facts, occasional updates → ~50KB
- projects/ - one active project, archived when done → ~100KB active
- lessons/ - grows continuously → ~1MB/year

Procedural (workflows):
- Maybe 50-100 workflows over time → ~500KB
- Skills folder already handles this

**Total estimate:** <50MB/year. Manageable in flat files. No database needed unless:
- Semantic search required (then vector DB)
- Complex graph queries required (then graph DB)
- >100k ephemeral messages (then SQLite for indexing)

**Current conclusion:** Markdown + JSONL can handle this for years.

---

## THE IMPLEMENTATION QUESTION

What should S1 (or S1.5) actually build?

**Minimal viable memory system:**

1. **Structured long-term memory**
   - Create memory/ hierarchy (identity/, systems/, projects/, procedural/, lessons/)
   - Manual creation for now (Alex populates identity/ during onboarding)
   - Simple retrieval (grep, semantic keyword matching)

2. **DAG conversation history**
   - JSONL as planned
   - Branching, time-travel, compaction
   - This is ephemeral memory

3. **Signal-based consolidation**
   - After task success → prompt Queen to extract workflow
   - After task failure → prompt Queen to log lesson
   - After user correction → prompt Queen to update knowledge

4. **Confidence tracking**
   - Every memory entry has: content, confidence, source, timestamp
   - Retrieval respects confidence levels

5. **Onboarding protocol**
   - Structured intake conversation (could be Telegram)
   - Writes to memory/ hierarchy
   - Fast bootstrap

**What NOT to build yet:**

- Graph relationships (start flat)
- Vector DB (semantic search via grep is enough initially)
- SQLite (JSONL + Markdown sufficient for scale)
- Auto-compression on time triggers (signal-based only)

**Phased approach:**

S1: JSONL DAG + basic memory/ hierarchy (identity/, systems/, projects/)
S1.5: Signal detection + consolidation protocol + confidence tracking
S2: Onboarding flow + structured intake
Later: Migrate to SQLite/graph/vector only if scale demands it

---

## THE VISION

The Queen wakes up. She loads:
- identity/ (who Alex is, her constraints)
- systems/ (the VPS topology)
- projects/hive-office/ (current build context)
- Current conversation branch (last 20 messages)

Total context: ~50KB. Fast. Focused.

Alex says: "Deploy the analytics service."

The Queen:
1. Checks procedural/workflows/ for similar tasks (finds deploy_service.md)
2. Checks systems/vps.md for current state (port 8080 available)
3. Checks lessons/failures.md (no known issues with this service)
4. Executes the workflow
5. Verifies deployment
6. Updates systems/vps.md (service now running on port 8080)
7. Logs to projects/hive-office/changelog.md
8. Compresses working memory (task done) into long-term

Next time Alex says "deploy something," the Queen knows the pattern. She doesn't need to be told how. She learned.

That's the vision.

---

## THE DELEGATION PROBLEM

The Queen manages. Workers execute. But what does each one KNOW?

**Memory is not monolithic. Different agents need different knowledge.**

### Queen-level memory (orchestration)

What the Queen needs:
- identity/ - who Alex is, constraints, preferences
- systems/ - VPS topology, available resources
- projects/ - all active projects, their status
- procedural/ - high-level workflows (when to delegate what)
- lessons/ - strategic patterns (this approach works for this type of task)

What the Queen does NOT need:
- Detailed domain knowledge (that's worker-specific)
- Raw source material (research papers, documents - that's for specialized workers)
- Deep procedural detail (workers know their own methods)

The Queen knows WHAT and WHO. Not always HOW.

### Worker-level memory (execution)

Different worker types need different memory systems:

**TEMP WORKERS** (single-shot execution)
- Get: minimal context (just the mission parameters)
- Get: system state (VPS layout, available resources)
- Don't get: Queen's full memory (too much overhead)
- Don't get: other workers' context (isolated by design)

Example: Data cleaning worker
- Receives: input file path, output format spec
- Receives: available Python libraries (from systems/)
- Does NOT receive: Alex's identity, other projects, conversation history

**CONSORT WORKERS** (long-running specialists)
- Get: project-specific memory (everything about their domain)
- Get: relevant procedural memory (workflows for their specialty)
- Get: lessons specific to their task type
- Maintain: own working memory (task progress, blockers)

Example: Research consort
- Receives: research objectives, source constraints
- Maintains: knowledge graph of findings
- Reports: structured findings back to Queen
- Does NOT maintain: conversation history with Alex (that's Queen's job)

### Project-specific memory architecture

Different project types need different memory systems.

**HIVE-OFFICE** (current build)
- Queen memory: JSONL DAG + structured Markdown
- Workers: minimal context (just mission specs)
- No RAG needed (management tasks, not knowledge synthesis)

**RESEARCH-HIVE** (future)
- Queen memory: same (orchestration doesn't change)
- Research workers: RAG over document collections
  - Vector DB for semantic search
  - Document embeddings for source material
  - Citation tracking
  - Knowledge graph of findings
- Why: needs to search 10,000+ papers/documents semantically

**WRITER-HIVE** (future)
- Queen memory: same
- Writer workers: RAG over Alex's knowledge dump
  - Vector search over 4 years of notes
  - Semantic clustering of related ideas
  - Context retrieval for specific topics
  - Style consistency across long documents
- Why: book writing requires synthesis of massive unstructured knowledge

**The pattern:**

Queen = categories and references (overview, management)
Specialized workers = semantic search where needed (domain execution)

The Queen doesn't need RAG. She needs to know WHICH worker has WHICH capability.

### What gets passed down

**From Queen to Worker:**

ALWAYS:
- Mission parameters (what to do)
- System context (VPS state, available tools)
- Relevant constraints (from identity/constraints.md)

SOMETIMES:
- Project context (if worker needs to understand the bigger picture)
- Relevant lessons (if similar task was tried before)

NEVER:
- Full conversation history (too much, irrelevant)
- Other workers' internal state (isolation)
- Alex's complete identity (workers don't need to know personal details)

**From Worker to Queen:**

ALWAYS:
- Structured result (the output artifact)
- Execution summary (what was done, how long it took)
- Success/failure status

SOMETIMES:
- Lessons learned (if something interesting happened)
- Resource usage (if it was unusual)
- Errors encountered (if they're worth logging)

NEVER:
- Internal working state (Queen doesn't need worker's thought process)
- Raw debug output (unless failure investigation)

### RAG architecture (for future specialized hives)

When a worker DOES need RAG:

**Storage layer:**
- Vector DB (ChromaDB, Qdrant, or similar)
- Document embeddings (all-MiniLM-L6-v2 or similar)
- Metadata index (source, date, category, confidence)

**Retrieval layer:**
- Semantic search (find documents similar to query)
- Hybrid search (semantic + keyword for precision)
- Context window management (top-k results, reranking)

**Integration layer:**
- Worker queries vector DB
- Retrieves top N relevant chunks
- Injects into worker's prompt as context
- Worker cites sources in output

**Key difference from Queen's memory:**

Queen: structured categories, reference-based retrieval
Research/Writer workers: unstructured documents, semantic similarity retrieval

The Queen doesn't understand what's IN the knowledge base. She knows that the Research worker HAS a knowledge base and can be asked to find things.

### Memory isolation (security and focus)

Workers can't see each other's memory. Intentional.

Temp worker processing invoice #1 can't see invoice #2 (different worker instance).
Research worker on project A can't access research findings from project B (unless Queen explicitly shares).

This prevents:
- Context pollution (worker gets confused by irrelevant data)
- Security leaks (workers handling sensitive data stay isolated)
- Resource waste (workers don't load memory they don't need)

The Queen is the ONLY agent with cross-project visibility.

### The identity propagation problem

Alex's identity (IDENTITY.md) defines how the Queen behaves.

But should workers inherit this identity?

**Yes, workers inherit:**
- Communication style (direct, evidence-based, no hedging)
- Language preferences (German/English switching)
- Core constraints (no manipulation, verify before claiming success)

**No, workers don't inherit:**
- Alex's personal context (UNBLURRY business details)
- Alex's relationship with the Queen (workers serve the Queen, not directly Alex)
- Personality traits specific to orchestration (workers execute, they don't need the Queen's confidence)

**Implementation:**

Create identity/worker_shared.md - subset of IDENTITY.md that ALL workers receive.
This becomes part of every worker's system prompt.

Example content:
```
You are a specialized worker in the Hive-Office system.
You report to Queen-Alpha.

Communication rules:
- Direct statements, no hedging
- Evidence-based claims only
- Clean up after yourself
- Verify before reporting success

Core constraints:
- Never claim completion without proof
- Scripts must be idempotent
- No temporary files left behind
```

Workers get discipline. They don't get personality.

### Project memory lifecycle

**Project starts:**
- Queen creates projects/{project-name}/
- Initializes: decisions.md, blockers.md, todos.md, changelog.md
- If project needs specialized workers, creates worker-specific memory (RAG setup for research-hive)

**Project active:**
- Queen updates project memory based on signals
- Workers maintain their own working memory (ephemeral, task-specific)
- Cross-pollination: successful worker approaches get promoted to procedural/ for reuse

**Project completes:**
- Queen archives projects/{project-name}/ to archive/
- Extracts key lessons to lessons/
- Specialized worker memory (vector DB) gets archived or deleted (depending on if it's reusable)
- Procedural workflows that were project-specific get promoted to general procedural/ if useful

**Project dormant:**
- Memory stays in projects/{project-name}/ but not actively loaded
- Can be reactivated if user references it
- Doesn't pollute Queen's active context

### The minimal viable delegation model

For S1/S1.5, we only need:

1. Queen-level memory hierarchy (identity/, systems/, projects/, procedural/, lessons/)
2. Worker context injection (passing mission + constraints to workers)
3. Result extraction (workers report back structured outcomes)

We do NOT need (yet):
- RAG infrastructure (research/writer hives are future)
- Cross-worker memory sharing (all workers isolated for now)
- Complex project memory (just basic tracking)

Build orchestration first. Add specialized memory as projects demand it.

---

## OPEN QUESTIONS (ANSWERED)

1. **Should onboarding be conversational or form-based?**
   → Conversational + file upload capability (.md, .docx, etc.)

2. **How much of identity/ should be auto-populated vs manual?**
   → Setup is manual (or Queen does it herself - she could interview Alex and write her own identity files)

3. **Should procedural/ workflows be executable Python or documented Markdown?**
   → Either execute OR document. Not both simultaneously. Markdown with embedded code blocks when documentation matters. Pure Python when it's just execution.

4. **When does JSONL become insufficient and SQLite necessary?**
   → Unknown. Test at scale. Migrate when queries get slow or we need relational joins.

5. **Do we need semantic search or is keyword matching enough?**
   → Queen: categories and references (no semantic search needed)
   → Research/Writer workers: semantic search (RAG with vector DB)

6. **Should the Queen proactively suggest memory consolidation or wait for signals?**
   → Both. Proactive suggestions + signal-based triggers.

7. **How does the Queen handle conflicting information (old fact vs new fact)?**
   → She asks. "I have X logged from [date]. You're saying Y. Which is current?"

8. **Should lessons/ be deduplicated automatically or manually curated?**
   → Ask, context-based. Queen flags potential duplicates, Alex decides.

These need testing to answer. Build minimal first. Observe behavior. Refine.

---

## THE REPLICABILITY PROBLEM

**Critical constraint:** This tool will be used by other people. Not just Alex.

The Queen's core logic cannot be hardcoded to Alex's personality. The memory system must be wipeable. Fresh instances must be possible.

### Core system vs user data (permanent boundary)

**CORE SYSTEM** (permanent, shipped with every Queen instance)

Code:
- Agent loop (ReAct pattern, tool execution, worker spawning)
- Memory architecture (DAG, consolidation triggers, retrieval logic)
- Operational rules (verify, idempotency, clean state, operational loop, delegation)
- Communication framework (direct, evidence-based, no hedging)
- Signal detection (how to recognize meaningful events)
- Worker management (spawn, monitor, terminate)

Behavioral baseline:
- Five operational rules (these define HOW the Queen works, not WHO she serves)
- Evidence-based communication (no hallucination, verify claims)
- Clean execution (no temp file rot, idempotent scripts)
- Delegation protocol (orchestrate, don't execute heavy work)

Infrastructure templates:
- memory/ directory structure (empty folders with README explaining purpose)
- Onboarding protocol (the questions to ask, not the answers)
- Worker templates (generic patterns for temp/consort workers)

**USER DATA** (wipeable, user-specific configuration)

All memory/ contents:
- identity/ (who the user is, their constraints, preferences)
- systems/ (user's infrastructure state)
- projects/ (user's active work)
- procedural/ (workflows learned from this user's tasks)
- lessons/ (patterns extracted from this user's experience)
- skills/ (custom capabilities created for this user)

All sessions/ contents:
- Conversation history (JSONL DAG files)
- Working memory (active task state)
- Compressed history (old conversation branches)

All accumulated knowledge:
- Every fact learned
- Every workflow discovered
- Every lesson extracted

**The hard boundary:**

Core system: "Here's HOW to remember, consolidate, and retrieve"
User data: "Here's WHAT to remember about THIS user"

Example:
- Core: "Consolidate when task succeeds. Extract working method."
- User: "Alex prefers German for casual conversation, English for technical work."

The first is permanent. The second is wipeable.

### Factory reset protocol

What happens when you wipe everything and start fresh:

**Step 1: Preserve core system**
```
queen-alpha/
  src/           # stays (core code)
  templates/     # stays (directory structures)
  tests/         # stays (validation)
  docs/          # stays (how to use the Queen)
```

**Step 2: Clear user data**
```
memory/        # deleted entirely
sessions/      # deleted entirely
skills/        # cleared (only keep system skills)
```

**Step 3: Reinitialize structure**
```
memory/
  identity/    # empty, has README.md explaining purpose
  systems/     # empty, has README.md
  projects/    # empty, has README.md
  procedural/  # empty, has README.md
  lessons/     # empty, has README.md

sessions/      # empty

skills/        # contains only shipped system skills
  _system/     # built-in skills everyone gets
```

**Step 4: Fresh boot state**

Queen starts with:
- No user context
- No conversation history
- No learned workflows
- Only core operational rules

First message from Queen:
```
Fresh boot. No user configuration detected.

Run onboarding to initialize your profile, or import an existing profile.

Commands:
/onboard - start setup conversation
/import <profile.zip> - load existing configuration
```

### User profile structure (export/import)

A user profile is:
```
user_profile.zip
  ├── identity/
  │   ├── user.md
  │   ├── constraints.md
  │   └── preferences.md
  ├── systems/
  │   ├── infrastructure.md
  │   └── tools.md
  ├── skills/
  │   └── custom_skills/
  └── metadata.json (profile version, creation date, user ID)
```

**What's included:**
- Identity (who the user is, their values)
- System state (infrastructure facts that transfer, like "I use Docker")
- Custom skills (tools this user created)
- Metadata (when profile was created, which Queen version)

**What's NOT included:**
- Projects (too specific to one deployment)
- Conversation history (ephemeral, not transferable)
- Procedural workflows (might not transfer to new infrastructure)
- Lessons (learned in context of old system)

**Export command:**
```
/export profile_name
→ Creates profile_name.zip in /exports/
```

**Import command:**
```
/import profile_name.zip
→ Unpacks to memory/
→ Queen reviews and confirms compatibility
→ User can modify before activating
```

**Use cases:**
- Migrate from one VPS to another (export Alex's profile, import on new server)
- Share anonymized profile (Alex exports with identity/ redacted)
- Backup before major changes (export, experiment, restore if needed)
- Template for similar users (export generic consultant profile, new user imports and customizes)

### Onboarding (fresh user initialization)

When a new user runs `/onboard`, the Queen conducts structured intake.

**Phase 1: Identity**
```
QUEEN: What's your name?
USER: Alex

QUEEN: What do you do? (One sentence)
USER: I run a marketing practice helping service professionals demonstrate their worth.

QUEEN: Languages you work in?
USER: German and English

QUEEN: Any constraints I should never violate?
USER: No manipulation. No AI-generated garbage. Ethics are non-negotiable.

→ Writes to memory/identity/user.md and constraints.md
```

**Phase 2: Systems**
```
QUEEN: What infrastructure am I managing?
USER: Hetzner VPS, 8 vCPU, 16GB RAM, Ubuntu 24.04

QUEEN: What's already installed?
USER: Docker, Python 3.12, standard dev tools

→ Writes to memory/systems/infrastructure.md
```

**Phase 3: Current work**
```
QUEEN: What are you working on right now?
USER: Building a multi-agent orchestrator called Hive-Office

QUEEN: Main objective?
USER: Autonomous task delegation with Docker-sandboxed workers

→ Creates memory/projects/hive-office/ with initial context
```

**Phase 4: Communication preferences**
```
QUEEN: How should I communicate with you?
USER: Direct. Evidence-based. No hedging. No corporate speak.

QUEEN: When should I ask vs decide?
USER: Ask when uncertain. Decide when you have confidence.

→ Writes to memory/identity/preferences.md
```

**Total time:** 5-10 minutes
**Output:** Functional user profile, Queen is operational

### The personality injection point

User personality (Alex's voice, values, constraints) enters the system ONLY through memory/identity/.

**What this means:**

The Queen's system prompt is built from:
1. Core behavioral rules (permanent, everyone gets these)
2. memory/identity/ (loaded from user profile)
3. Current context (active conversation, relevant projects)

If memory/identity/ is empty → Queen uses only core rules (functional but generic).
If memory/identity/ is populated → Queen adapts to user's style.

**Example system prompt assembly:**

```python
system_prompt = f"""
{CORE_RULES}  # permanent (verify, idempotency, clean state, etc.)

{load_file('memory/identity/user.md')}  # user-specific
{load_file('memory/identity/constraints.md')}  # user-specific
{load_file('memory/identity/preferences.md')}  # user-specific

{build_context()}  # current conversation, active projects
"""
```

If user.md says "I'm Alex, I run UNBLURRY, I value direct communication," the Queen adapts.
If user.md says "I'm Bob, I run a law firm, I prefer formal communication," the Queen adapts.

Same core code. Different configuration.

### Multi-user considerations (future)

**Current design:** One Queen per user.
Each user gets their own Queen instance with their own memory/.

**Possible future:** One Queen, multiple users.
Would require:
- User ID in every memory entry
- Session isolation (Alex's conversation doesn't load Bob's context)
- Permission system (Alex can't see Bob's projects)
- Shared vs private memory (company knowledge base accessible to all users)

**Decision for now:** Keep it simple. One Queen = one user.

Multi-tenancy only if there's actual demand. Don't over-engineer.

### The minimum replicable package

What someone needs to deploy their own Queen:

**Required:**
- Core code (agent loop, memory system, worker management)
- Infrastructure templates (memory/ structure, README files)
- Onboarding protocol (the setup flow)
- Documentation (how to run, how to configure)

**Not required:**
- Alex's identity files (user creates their own via onboarding)
- Alex's conversation history (starts fresh)
- Alex's learned workflows (they'll learn their own)
- Hive-Office project files (they might build different projects)

**Deployment steps for new user:**
1. Clone repo
2. Run `./install.sh` (sets up core system)
3. Boot Queen
4. Run `/onboard` (10 minute setup)
5. Start using

**The replicability test:**

Can someone else deploy this Queen and have her work for them WITHOUT seeing Alex's data or personality?

Yes → architecture is correct.
No → we hardcoded something that should be configurable.

### What gets version-controlled

**Git tracks:**
- Core code (src/)
- Templates (memory/ structure, README files)
- Tests (automated validation)
- Docs (how to use)

**Git does NOT track:**
- memory/ contents (user-specific, excluded via .gitignore)
- sessions/ contents (ephemeral, excluded)
- skills/ custom additions (user-specific)

**User's personal repo (optional):**

If Alex wants to version-control HER configuration:
- Fork main repo
- Create alex-config branch
- Commit memory/identity/ files
- Keep memory/projects/ in separate private repo (if it contains sensitive data)

But the main repo ships clean. No user data baked in.

### The wipeable checklist

Before we call S1/S1.5 done, verify:

- [ ] Can delete memory/ entirely and Queen still boots
- [ ] Fresh boot prompts for onboarding or import
- [ ] Onboarding creates functional user profile in <10 minutes
- [ ] Core operational rules work without any memory/ data
- [ ] Export creates portable profile.zip
- [ ] Import restores profile successfully
- [ ] Two users can run their own Queens with different profiles
- [ ] No hardcoded references to "Alex" in core code
- [ ] Documentation explains deployment for new users

If any of these fail → we hardcoded something that should be wipeable.

---

## DECISIONS (LOCKED FOR S1 BUILD)

These are no longer options. These are specifications.

### 1. Storage formats (decided)

**Ephemeral memory (conversation):** JSONL DAG
- One file per session: session_id.jsonl
- Line 1: session header with metadata
- Lines 2+: entries with {type, id, parent_id, ...}
- Supports branching, time-travel, fast append
- Migrate to SQLite only when >50k nodes or complex queries needed

**Long-term memory (facts/lessons):** Markdown files
- Structured hierarchy in memory/
- Human-readable, version-controllable
- Grep for retrieval initially
- No vector DB unless research-hive or writer-hive explicitly needs it

**Working memory (active tasks):** YAML
- Structured, readable, easily edited
- One file per active project in projects/{name}/

**Meta-memory (capability map):** JSON
- Machine-first format
- skills_registry.json tracks what skills exist and their metadata

### 2. Memory hierarchy (exact structure)

```
memory/
  identity/
    user.md                 # name, role, languages, timezone
    constraints.md          # non-negotiables (ethics, boundaries)
    preferences.md          # communication style, format preferences
    context.md              # business context (UNBLURRY for Alex)
    worker_shared.md        # subset inherited by all workers
    
  systems/
    infrastructure.md       # VPS specs, IP, SSH, installed services
    tools.md               # Docker, Python, available packages
    topology.md            # how components connect
    
  projects/
    {project-name}/
      README.md            # project purpose and status
      decisions.md         # why we chose X over Y
      blockers.md          # what's blocking progress
      todos.md             # active task list
      changelog.md         # what changed and when
      working_memory.yaml  # current task state
      
  procedural/
    workflows/
      {workflow-name}.md   # documented approach that worked
    fixes/
      {problem-name}.md    # known issue + known solution
      
  lessons/
    successes.md           # approaches that worked, reuse
    failures.md            # approaches that failed, avoid
    patterns.md            # recurring situations and solutions
    
  skills/
    _system/               # built-in skills (shipped)
    _user/                 # user-created skills
    skills_registry.json   # metadata about all skills
```

### 3. Consolidation triggers (exact conditions)

**SIGNAL-BASED (primary triggers):**

Fire consolidation when:
1. Task completes successfully
   - Extract: the working method
   - Write to: procedural/workflows/{task-type}.md
   - Include: what worked, steps taken, confidence level

2. Task fails after 3+ attempts
   - Extract: what didn't work and why
   - Write to: lessons/failures.md
   - Include: approaches tried, why they failed, what to try instead

3. User corrects the Queen
   - Extract: the misunderstanding
   - Update: relevant memory file (identity/, systems/, or procedural/)
   - Include: old understanding, new understanding, source

4. Pattern emerges (same task succeeded 3 times)
   - Extract: the common pattern
   - Write to: procedural/workflows/ as a reusable approach
   - Include: pattern recognition confidence

5. New skill created
   - Update: skills/skills_registry.json
   - Include: what it does, when to use it, initial confidence: LOW

6. Decision made during task
   - Write to: projects/{active-project}/decisions.md
   - Include: decision, reasoning, alternatives considered

**CAPACITY-BASED (fallback triggers):**

Only fire when:
- Context window >90% full → compress oldest ephemeral branch
- Working memory has >20 completed tasks → archive to changelog

**NEVER FIRE ON:**
- Message count (not "every 50 messages")
- Time elapsed (not "every hour")
- Manual compression unless user explicitly requests

### 4. Retrieval logic (exact algorithm)

**ALWAYS LOADED (context baseline):**
```python
context = [
    load('memory/identity/user.md'),
    load('memory/identity/constraints.md'),
    load('memory/identity/preferences.md'),
    get_current_branch(),  # last 20 messages on active DAG branch
    load(f'memory/projects/{active_project}/working_memory.yaml')
]
```

**ON-DEMAND (query-driven):**

When starting a task:
- Check procedural/workflows/ for similar task name (keyword match)
- Check lessons/failures.md for error patterns if task has failed before

When encountering an error:
- Check lessons/failures.md for this error message (grep)
- Check procedural/fixes/ for known solutions

When spawning a worker:
- Inject memory/systems/ (infrastructure topology)
- Inject memory/identity/worker_shared.md (discipline)

When user references "like last time" or "how we did X":
- Search procedural/workflows/ for X (keyword)
- Search recent conversation branches for X (full-text)

**NEVER LOADED AUTOMATICALLY:**
- Old conversation branches (only via explicit time-travel)
- Archived projects (only if user references by name)
- Other users' memory (if multi-tenancy ever exists)

### 5. Confidence tracking (exact schema)

Every memory entry includes:
```yaml
content: "Docker version is 24.0.7"
confidence: MEDIUM
source: "inferred_from_logs"
timestamp: "2026-02-18T10:16:00Z"
last_verified: null
needs_reverification: false
```

**Confidence levels:**
- HIGH: verified fact (user stated, or Queen ran command and saw output)
- MEDIUM: inferred from context (probably true, not confirmed)
- LOW: speculation (might be true, needs verification)

**Confidence decay:**
- Facts >30 days old without reverification: HIGH → MEDIUM
- Facts >90 days old without reverification: MEDIUM → LOW
- LOW confidence facts not verified within 7 days: flagged for user review

**Confidence updates:**
- Speculation verified → LOW to HIGH
- Fact reverified → refresh timestamp, stays HIGH
- Conflict detected → flag for user resolution

### 6. Onboarding protocol (exact flow)

**Trigger:** User runs `/onboard` or Queen boots with empty memory/

**Phase 1: Core identity (required)**
```
QUEEN: What's your name?
→ writes to memory/identity/user.md (field: name)

QUEEN: What do you do? (One sentence)
→ writes to memory/identity/user.md (field: role)

QUEEN: Languages you work in?
→ writes to memory/identity/user.md (field: languages)

QUEEN: Any absolute constraints? (Things I should never do)
→ writes to memory/identity/constraints.md
```

**Phase 2: Infrastructure (optional but recommended)**
```
QUEEN: What infrastructure am I managing? (VPS, local machine, cloud?)
→ writes to memory/systems/infrastructure.md

QUEEN: What's already installed? (Docker, Python, databases?)
→ writes to memory/systems/tools.md
```

**Phase 3: Current work (optional)**
```
QUEEN: What are you working on right now?
→ creates memory/projects/{project-name}/README.md

QUEEN: Main objective for this project?
→ writes to memory/projects/{project-name}/working_memory.yaml
```

**Phase 4: Communication style (optional)**
```
QUEEN: How should I communicate with you? (Direct, formal, casual?)
→ writes to memory/identity/preferences.md (field: communication_style)

QUEEN: When should I ask vs decide autonomously?
→ writes to memory/identity/preferences.md (field: autonomy_level)
```

**Total time budget:** 5-10 minutes for complete setup, 2 minutes for minimal (just phase 1)

**Onboarding can be resumed:**
- Phases are independent
- User can `/onboard identity` to redo phase 1 without touching phases 2-4
- User can manually edit memory/ files anytime

### 7. Factory reset (exact steps)

**Command:** `/factory-reset`

**Confirmation required:**
```
QUEEN: This will delete all user data:
- All conversation history
- All learned workflows
- All custom skills
- All project memory

Core system code will be preserved.

Type CONFIRM to proceed.
```

**If confirmed:**
1. Archive current memory/ to exports/backup_{timestamp}.zip
2. Delete memory/ contents (keep structure)
3. Delete sessions/ contents
4. Delete skills/_user/ contents (keep _system/)
5. Reinitialize with empty README files
6. Reboot Queen
7. Prompt for `/onboard` or `/import`

**Irreversible.** Backup is created but user must explicitly restore it.

### 8. Scope boundaries (what's IN vs OUT for S1)

**IN SCOPE for S1 build:**
- JSONL DAG with branching and time-travel
- Memory hierarchy (all folders, README files, initial structure)
- Signal-based consolidation (6 triggers defined above)
- Confidence tracking (HIGH/MEDIUM/LOW + metadata)
- Query-driven retrieval (always-loaded + on-demand)
- Onboarding protocol (4 phases, structured intake)
- Factory reset capability
- Core vs user data separation
- Basic grep-based search (keyword matching in memory/)

**OUT OF SCOPE (explicitly deferred):**
- RAG / vector embeddings (wait for research-hive)
- SQLite migration (wait for >50k nodes)
- Graph relationships (wait for complex queries)
- Auto-compression on time/count triggers (signal-based only)
- Multi-tenancy (one Queen per user)
- Semantic search beyond grep (research/writer hives only)
- Worker-specific memory systems (temps/consorts get basic context)
- Advanced project lifecycle (just active/archived for now)

---

## BUILD SEQUENCE (S1 implementation order)

The vision is complete. Now define execution order.

**S1.1: JSONL DAG (conversation history)**
- Implement SessionManager with: create, open, append, branch, get_path, build_context
- Support message entries with role/content
- Support compaction entries (manual trigger only)
- Integration: replace HISTORY.md with session_manager.build_context()
- Tests: branch creation, path traversal, context reconstruction

**S1.2: Memory hierarchy scaffold**
- Create memory/ directory structure (all folders from schema)
- Write README.md in each folder explaining purpose
- Create template files (user.md, constraints.md, etc.) with schema comments
- Integration: prompt builder checks if memory/identity/ exists before loading
- Tests: directory structure exists, README files present

**S1.3: Confidence tracking**
- Define MemoryEntry dataclass with confidence/source/timestamp fields
- Update all memory writes to include metadata
- Implement confidence decay (mark stale facts)
- Integration: retrieval respects confidence (HIGH stated as fact, MEDIUM/LOW flagged)
- Tests: confidence updates correctly, decay triggers at right intervals

**S1.4: Signal detection**
- Implement detect_signal() that recognizes the 6 trigger conditions
- Hook into agent loop: after every tool execution, check for signals
- Implement consolidate() that extracts lesson/workflow based on signal type
- Integration: fires automatically, writes to correct memory/ location
- Tests: each of 6 triggers fires correctly, writes to right place

**S1.5: Onboarding protocol**
- Implement /onboard command with 4-phase structured intake
- Each phase writes to correct memory/ files with proper schema
- Support resume (redo individual phases)
- Support skip (minimal setup = just phase 1)
- Integration: fresh boot detects empty memory/ and prompts for onboarding
- Tests: complete onboarding creates valid user profile in <10 minutes

**S1.6: Factory reset**
- Implement /factory-reset command with confirmation
- Archive to exports/ before deleting
- Clear memory/ and sessions/, preserve core
- Reinitialize empty structure
- Integration: post-reset boot prompts for onboarding
- Tests: reset is reversible (backup exists), fresh boot works

**S1.7: Retrieval integration**
- Implement query_memory() that loads always-loaded + on-demand content
- Integrate with prompt builder (replaces MEMORY.md read)
- Implement keyword search (grep across memory/)
- Integration: LLM context includes relevant memory, not everything
- Tests: retrieval finds relevant files, doesn't load irrelevant ones

**GATE CRITERIA (before S1 is "done"):**
- [ ] Can create/branch/traverse JSONL DAG conversations
- [ ] Memory hierarchy exists with all documented folders
- [ ] Confidence tracking works on all memory writes
- [ ] All 6 signal triggers fire correctly
- [ ] Onboarding creates functional user profile
- [ ] Factory reset wipes user data, preserves core
- [ ] Retrieval loads relevant memory based on context
- [ ] Wipeable checklist (from replicability section) passes
- [ ] Two separate users can onboard different profiles
- [ ] No hardcoded user data in core code

All tests green. All gates pass. Then S1 is complete.

---

## THE GOAL

A Queen who knows what she knows, learns from experience, and acts FOR Alex without being told how every time.

That requires memory architecture. Not just conversation logs.

This document defines that architecture. Complete. Ready to build.
