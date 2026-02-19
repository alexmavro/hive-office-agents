# Research Hive: Engineering Specification v3

**Project:** Content Research Hive - AI co-author trained on 8-9 years of teaching corpus  
**Builder:** VPS-Claude (terminal specialist)  
**Date:** 2026-02-17  
**Estimated effort:** 32-40 hours over 6-8 days

---

## Table of Contents

- [Part 1: The Problem](#part-1-the-problem)
- [Part 2: What We're Actually Building](#part-2-what-were-actually-building)
- [Part 3: Architecture Decisions](#part-3-architecture-decisions)
- [Part 4: Technical Requirements](#part-4-technical-requirements)
- [Part 5: Build Phases](#part-5-build-phases)
- [Part 6: Success Criteria & Validation](#part-6-success-criteria--validation)
- [Part 7: What Makes This Different](#part-7-what-makes-this-different)
- [Part 8: Future Extensions](#part-8-future-extensions)
- [Part 9: Your First Task](#part-9-your-first-task)
- [Part 10: Questions to Ask When Stuck](#part-10-questions-to-ask-when-stuck)
- [Appendix A: Implementation Gaps & Open Decisions](#appendix-a-implementation-gaps--open-decisions)
- [Appendix B: Dependencies Reference](#appendix-b-dependencies-reference)

---

## Your Role

You're building a **writing system**, not a search engine.

This spec defines WHAT and WHY. You decide HOW to implement it. If you have a better approach than what's suggested, use it - just document your reasoning in STATUS.md.

The constraints are firm. The implementations are starting points, not mandates.

---

# Part 1: The Problem

## What Alex Has Been Trying to Solve

Alex is a writer and teacher with 8-9 years of accumulated content:
- Workshops (transcribed, some imperfectly)
- Video scripts (polished)
- Client work (deliverables, proposals)
- Teaching materials (slides, notes)
- Personal notes (rough, fragmented)

**Current workflow (broken):**

```
1. "I should write about pricing psychology"
2. Opens blank Google Doc
3. Stares at blinking cursor
4. Tries to remember: "What did I already say about this?"
5. Searches folders manually for 30 minutes
6. Finds 3 relevant pieces, misses 7 others
7. Maybe writes a paragraph
8. Gives up, does something else
```

**Time cost:** 8 hours for a workshop prep becomes mostly archaeology, not creation.

## What Alex Tried (And Why It Failed)

### NotebookLM (Google)

**What worked:**
- Could upload materials
- Generated structure and bullets
- Fast

**What broke:**
- **Manual upload** (high friction, won't scale to 5,000 files)
- **One-shot generation** (can't iterate, can't steer)
- **Generic voice** (sounds like AI, not like Alex)
- **No citations** (can't verify or drill down)
- **Shallow on complex topics** (loses depth when synthesizing)
- **No brand principles** (can't enforce "strategy before tactics")

Result: Used once for a rushed workshop. Okay bullets. Wrong voice. Wouldn't use again.

### Generic RAG (Retrieval-Augmented Generation)

**What worked:**
- Semantic search is better than keyword search

**What broke:**
- Returns chunks, not drafts
- No voice training
- No structure feedback loop
- Alex still starts at blank page

---

# Part 2: What We're Actually Building

## Not a Librarian. A Co-Author.

The system needs to **draft actual content** using Alex's past work as source material.

**The full workflow:**

```
1. Alex: "I'm writing a workshop on pricing psychology for service businesses"

2. LIBRARIAN retrieves 40 relevant chunks from 9 years of work

3. ARCHITECT analyzes chunks, proposes 3 structure options:
   - Option A: Beginner → Advanced (3-hour workshop)
   - Option B: Problem → Solution (90-min talk)
   - Option C: Case study deep-dive (masterclass)
   
4. Alex picks Option A, requests "add section on dynamic pricing"

5. ARCHITECT refines structure, marks gaps (no content on dynamic pricing found)

6. Alex approves structure: "Use this. Write section 1."

7. WRITER drafts Section 1:
   - Synthesizes insights from retrieved chunks
   - Writes in Alex's voice (trained on identity files)
   - Cites sources inline ("from 2021 workshop, slide 12")
   - 800 words of coherent prose

8. CRITIC reviews draft:
   - Checks against BRAND_PRINCIPLES.md
   - Flags violation: "This leads with tactics, not strategy"
   - Returns to WRITER

9. WRITER revises, passes Critic

10. Alex sees 80% finished Section 1
    - Polishes to 100% (rewrites for copyright + creative control)
    - Exports to Obsidian
    - Continues to Section 2
```

**Key insight:** Alex doesn't rewrite because the draft is bad. She rewrites because:
1. **Copyright** (AI-generated text isn't copyrightable, her rewrite is)
2. **Pride** (she's a writer, she LIKES writing)
3. **Control** (final creative decisions are hers)

The system produces **usable drafts**, not just organized bullets.

---

**Note on workflow modes:** The example above combines Discovery (finding past content), Structure Approval (Architect proposes options), and Drafting (Writer creates prose). These are distinct interaction patterns. Let's define each separately:

---

## The Four Interaction Modes

### Mode 1: Discovery ("What do I have?")

**Use case:** "Before I decide what to write, show me everything I've ever said about personal branding"

**What happens:**
- Broad semantic search (top 100 chunks)
- Grouped by year (see evolution over time)
- Duplicates flagged (said same thing in 2017 and 2023?)
- Gaps identified (mentioned X but never developed it)

**Output:** Landscape view in markdown

**Why this matters:** Alex can't decide structure until she knows what raw material exists.

---

### Mode 2: Rebranding ("How would I say this now?")

**Use case:** "I have this 2018 workshop script. It's good content but off-brand now. How would I reframe it?"

**What happens:**
- ARCHITECT analyzes old script
- Compares to BRAND_PRINCIPLES.md
- Identifies what needs changing:
  - Tone (2018: friendly. 2026: confident and direct)
  - Structure (2018: tactics-first. 2026: strategy-first)
  - Examples (2018: product pricing. 2026: service pricing)
- WRITER drafts reframed sections
- CRITIC validates against current brand

**Output:** Before/after structure + rewritten sections

**Why this matters:** 9 years of content isn't trash. Much of it is salvageable with reframing.

---

### Mode 3: Structure Discovery ("What could this become?")

**Use case:** "I have 12 scattered notes on decision-making. What could they turn into?"

**What happens:**
- ARCHITECT analyzes fragments
- Identifies themes (cognitive biases, heuristics, business context)
- Proposes 3 structure options:
  - Workshop (3 sections, beginner to advanced)
  - Video series (5 episodes, one theme each)
  - Long-form article (all themes woven together)
- For each option:
  - Shows what content exists
  - Marks what's missing (gaps)
  - Estimates effort (how much new writing needed)

**Output:** 3 structure proposals with gap analysis

**Why this matters:** Alex often has pieces but no direction. The system helps her see possibilities.

---

### Mode 4: Quote Bank ("Give me usable snippets")

**Use case:** "I need 5 LinkedIn posts this week about business strategy"

**What happens:**
- LIBRARIAN searches for short, punchy statements (1-3 sentences)
- Filters for standalone readability (no unclear references like "this" or "that")
- Checks against BRAND_PRINCIPLES (filters out off-brand stuff)
- Returns 20-30 options

**Output:** List of ready-to-post quotes with citations

**Why this matters:** 10 minutes instead of 2 hours. Highest ROI use case.

**Time savings breakdown:**
- Weekly content: 1h 50min/week saved
- Workshop prep: 5 hours/workshop saved
- Video scripts: 2.5 hours/script saved

---

## The Missing Piece: The Writer Worker

Previous spec had Librarian, Architect, Critic. Missing: **Writer**.

**What the Writer does:**

1. **Receives approved structure** from Architect
2. **Receives retrieved chunks** from Librarian
3. **Loads identity training** (IDENTITY.md, VOICE_TRAINING.md, THINKING_TEMPLATES.md)
4. **Drafts actual prose**:
   - Synthesizes insights from chunks
   - Writes in Alex's voice
   - Cites sources inline
   - Fills gaps with new thinking (when needed)
5. **Submits to Critic** for QA
6. **Revises** based on feedback
7. **Delivers** 80% finished content to Alex

**The Writer is NOT:**
- A summarizer (doesn't just stitch quotes)
- A paraphraser (doesn't just reword chunks)
- A generic LLM (it's trained on Alex's corpus + identity)

**The Writer IS:**
- A synthesizer (combines insights into coherent new text)
- A voice mimic (sounds like Alex because it learned from Alex)
- A drafter (produces usable first drafts)

---

## The Feedback Loop (Critical Feature)

**Before drafting, the system MUST get approval on structure.**

**Why:** If the Writer produces 3,000 words in the wrong direction, that's wasted tokens and time.

**The loop:**

```
1. Alex: "Write a chapter on pricing"

2. ARCHITECT (not Writer): 
   "I found 42 chunks on pricing. Here are 3 structure options:
    A) Psychology → Strategy → Tactics
    B) Common mistakes → Solutions
    C) Service vs Product comparison
    
    Which direction? Any sections to add/remove?"

3. Alex: "Option A, but add a section on value perception"

4. ARCHITECT: "Updated structure with value perception section.
   Note: Only 2 chunks on value perception found. Writer will need to create new content there.
   Approve to proceed?"

5. Alex: "Approved"

6. WRITER starts drafting
```

**No writing happens until structure is locked.**

This prevents:
- Wasted tokens on wrong direction
- Having to throw away large drafts
- Frustration from misalignment

---

## The Identity Training System

**Not just brand rules. Voice training.**

Four files the Writer loads before every draft:

### 1. IDENTITY.md - Core frameworks and mental models

```markdown
# Who Alex Is

## Core Frameworks

### The Strategy-First Principle
Strategy creates context for tactics. Tactics without strategy are noise.
When writing:
- Always explain WHY before HOW
- Show the pattern before the example
- Give the reader the thinking, not just the answer

### The Trade-Off Naming Convention
Every approach has costs. Acknowledging them builds trust.
When presenting solutions:
- Name the trade-off explicitly
- Never present one approach as universally correct
- Show what you gain AND what you give up

[etc - more frameworks]
```

### 2. VOICE_TRAINING.md - Example-based learning

```markdown
# Voice Examples

## Good (Sounds Like Alex)

"The pattern is simple. Most businesses overvalue tactics and undervalue strategy. 
Not because they're stupid. Because tactics are concrete and strategy feels abstract. 
But abstract work is what scales."

"You don't need more content. You need better thinking. One deep idea beats ten shallow posts. Every time."

## Bad (Doesn't Sound Like Alex)

"In today's fast-paced business environment, organizations must leverage cutting-edge 
strategies to optimize their value propositions and foster meaningful customer relationships."

"Here are 7 secrets to 10x your revenue! (You won't believe #4!)"

## Why It Matters

The Writer compares its output to these examples. If it sounds like "Bad", it revises.
Not by following rules, but by learning patterns from real examples.
```

### 3. STRUCTURE_TEMPLATES.md - Format-specific patterns

```markdown
# Structure Templates

## Workshop Format
- Open with pattern (not definition)
- 3-5 main sections
- Beginner → Advanced flow
- Each section: Pattern → Example → Practice
- Close with synthesis (not summary)

## Video Script Format
- Hook (first 10 seconds)
- Thesis (what you'll prove)
- 3 beats (supporting points)
- Each beat: Claim → Evidence → Implication
- Close with actionable insight (not recap)

## Article Format
- Lead with observation (not claim)
- Build argument piece by piece
- Use subheads as signposts (not decorations)
- Paragraphs vary in length (short for impact, long for depth)
- End with implication (what this means), not conclusion (what you said)

[etc]
```

### 4. THINKING_TEMPLATES.md - Recurring analytical patterns

```markdown
# Thinking Templates

## How Alex Approaches Pricing

1. Start with psychology (value perception)
2. Move to strategy (positioning)
3. Then tactics (pricing models)
4. Always name the trade-offs
5. Give examples from service businesses (her niche)

## How Alex Handles Objections

- Don't rebut, reframe
- Acknowledge the truth in the objection
- Show the hidden assumption
- Offer alternative framing
- Let reader decide

[etc - more patterns]
```

**How the Writer uses these:**

Before drafting, the Writer loads all 4 files into its context. Then it drafts using:
- Insights from retrieved chunks (WHAT to say)
- Identity training (HOW to say it)
- Structure templates (FORMAT to use)
- Thinking templates (LOGIC to follow)

Result: Drafts that sound like Alex because they're written using Alex's patterns.

**Implementation pattern (example, not prescription):**

The general approach: System prompt includes identity file contents + retrieved chunks + task instruction. Something like:

```
[Load IDENTITY.md contents]
[Load VOICE_TRAINING.md contents]
[Load relevant STRUCTURE_TEMPLATES.md section]

Source material from Alex's past work:
[chunks with citations]

Task: [specific drafting instruction]
```

**IMPLEMENTATION DETAIL:** Exact prompt structure, token management, and file loading mechanics are open decisions for VPS-Claude to determine based on model context limits and performance testing.

---

# Part 3: Architecture Decisions

## Decision 1: RAG + Voice Training (Not Fine-Tuning)

**Alternatives considered:**
- Fine-tune a model on Alex's corpus
- Use generic RAG without voice training
- Build custom LLM from scratch

**Why RAG + Voice Training:**

**Fine-tuning costs:**
- GPT-4: ~$30-100 for initial, recurring cost for updates
- Gemini: Free tier doesn't cover fine-tuning
- Would need to retrain every time Alex writes new content
- Hard to debug (can't see why it makes decisions)

**Generic RAG problems:**
- Returns chunks, doesn't draft
- No voice consistency
- Can't enforce brand principles

**Our approach:**
- Retrieve relevant chunks (standard RAG)
- Load identity training files (voice/structure/thinking patterns)
- Let LLM synthesize using both
- Much cheaper than fine-tuning
- Easy to update (just edit markdown files)
- Transparent (can see what it's using)

**Trade-off accepted:** Quality is 90% of fine-tuned model, but cost is 1% and flexibility is 10x better.

---

## Decision 2: Four Workers, Not One

**Why separate workers:**

**Single "smart" agent problems:**
- Context bloat (tries to do everything in one context)
- No clear handoff points
- Hard to debug (which part failed?)
- Can't optimize each role separately

**Four specialist workers:**
- **Librarian:** Search and retrieval only
- **Architect:** Structure and organization only
- **Writer:** Drafting only
- **Critic:** QA and brand enforcement only

**Benefits:**
- Each worker's context stays clean
- Clear handoff protocol
- Easy to improve one without breaking others
- Can use different models per worker (cheap for search, smart for writing)

**Example flow:**
```
Librarian (Gemini Flash, cheap) 
  → Architect (Gemini Flash, cheap)
  → Alex approval checkpoint
  → Writer (Gemini Pro, smart)
  → Critic (Gemini Flash, cheap)
  → Alex polishes
```

**Cost optimization:** Only the Writer uses expensive model. Others use cheap.

---

## Decision 3: Pre-Writing Approval (Feedback Loop)

**Why this is non-negotiable:**

Without approval before drafting:
- Writer produces 3,000 words in wrong direction
- Alex: "This isn't what I meant"
- Have to regenerate (wasted time and tokens)
- Frustration builds

With approval:
- Architect proposes structure
- Alex steers: "Option A, but add X, remove Y"
- Architect refines
- Alex: "Approved"
- Writer drafts with confidence

**Technical requirement:** System MUST pause between structure and drafting. No auto-progression.

---

## Decision 4: Gradio UI (Not Terminal, Not Web App)

**Alternatives:**
- Pure terminal (too limiting for multi-panel view)
- Custom React app (too much work)
- Streamlit (similar to Gradio, but Gradio has better chat widgets)

**Why Gradio:**
- Multi-panel layouts (chat + results + source preview)
- Hot reload during development
- Built-in chat components
- Can expose via tunnel for remote access
- Pure Python (no JS needed)

**Trade-off:** Less customizable than custom UI, but 90% of needs met with 10% of effort.

---

## Decision 5: LanceDB + SQLite (Not Vector DB Service)

**Why local:**
- **Privacy:** Corpus stays on VPS
- **Cost:** Zero marginal cost (no per-query pricing)
- **Speed:** No network latency
- **Control:** Can inspect and debug

**Why LanceDB specifically:**
- Embedded (no server to manage)
- Handles 1M+ vectors easily
- Fast queries (<100ms for 100K vectors)
- Open source

**Why SQLite for metadata:**
- Built into Python
- Perfect for relational queries ("all files from 2022")
- Atomic transactions
- Zero setup

**Trade-off:** Not as feature-rich as Pinecone/Weaviate, but we don't need those features.

---

## Decision 6: Local Embeddings (sentence-transformers)

**Why local:**
- **Privacy:** Text never leaves VPS
- **Cost:** Zero (vs $0.01 per 1K tokens for OpenAI)
- **Speed:** Fast enough for 384-dim model

**Model choice:** `all-MiniLM-L6-v2`
- 384 dimensions (small, fast)
- 80MB download (one-time)
- 85-90% quality of OpenAI's ada-002

**Trade-off:** Slightly lower quality than OpenAI embeddings, but good enough and free.

---

## Decision 7: Gemini Flash for Workers (Not Claude/GPT)

**Why Gemini:**
- **Free tier:** 15 RPM, 1M TPM (good for dev/testing)
- **Fast:** Low latency
- **Good at structure:** Handles organization tasks well
- **Upgradable:** Can switch to Gemini Pro later if needed

**Model assignment:**
- Librarian: Gemini Flash (retrieval doesn't need smart model)
- Architect: Gemini Flash (structure is pattern-based)
- Writer: Gemini 2.5 Pro (needs to sound like Alex)
- Critic: Gemini Flash (rule-checking is mechanical)

**Cost estimate during development:** ~$0.10-0.30/day

**Trade-off:** Writer quality not as good as Claude, but 1/10th the cost and good enough.

---

# Part 4: Technical Requirements

## Scale Parameters

| Metric | Current | Design For | Validation |
|---|---|---|---|
| Files | 2,000-5,000 | 50,000 | LanceDB benchmarks show 1M+ capacity |
| Text volume | 500MB-2GB | 10GB | Standard SSD handles this easily |
| Tokens | 20-50M | 250M | Chunking at 500 tokens = ~500K chunks max |
| Chunks | ~100K | 1M | LanceDB query time stays <100ms |
| Embeddings storage | 1-3GB | 15GB | 384-dim vectors, manageable |
| VPS storage used | 5-10GB | 50GB | VPS has 320GB available |
| Concurrent users | 1 (Alex) | 1 | No scale needed |

---

## Functional Requirements

### MUST Support

**File formats:**
- Text: .txt, .md, .html
- Documents: .docx, .pdf
- Transcripts: .srt, .vtt (from workshops)
- Structured: .json, .yaml (SOPs)

**Search capabilities:**
- Semantic similarity (not just keywords)
- Time filtering ("only content from 2022-2024")
- Source filtering ("only workshops, not client work")
- Top-K retrieval (default 30, configurable up to 100)

**Interaction modes:**
- Discovery (broad search, grouped by year, duplicates flagged)
- Rebranding (old content → current voice)
- Structure Discovery (fragments → possible structures)
- Quote Bank (extract 1-3 sentence standalone quotes)

**Output capabilities:**
- Draft prose (paragraphs, not bullets)
- Synthesize multiple chunks
- Cite sources inline
- Version outputs (v001, v002, etc.)
- Export to markdown

**Quality gates:**
- Brand principle enforcement (strategy before tactics, etc.)
- Voice consistency check (sounds like Alex, not generic AI)
- Citation accuracy (every claim traceable to source)
- Gap detection (missing content flagged)

### MUST NOT

- Send corpus data to external services (privacy violation)
- Auto-generate final content without Alex approval (she's the writer)
- Use paid vector DBs or embedding APIs (cost constraint)
- Require manual file upload (must auto-ingest via Syncthing)
- Block on long operations (must be async)

---

## Non-Functional Requirements

### Performance

- **First-time indexing:** <30 minutes for full corpus (5,000 files)
- **Single file indexing:** <10 seconds
- **Query latency:** <3 seconds for top-30 results
- **Draft generation:** <60 seconds for 500-word section
- **UI responsiveness:** No blocking on main thread

### Quality

- **Retrieval precision:** 83%+ of top-30 results must be relevant (manual inspection)
- **Citation accuracy:** 100% (every chunk must have correct source file + timestamp)
- **Brand violation detection:** 100% of clear violations must be flagged by Critic
- **Voice consistency:** 80%+ of drafts should "sound like Alex" on first pass (subjective)

### Reliability

- **Corrupted file handling:** Skip and log, don't crash
- **Partial sync handling:** Wait for file stability (Syncthing in progress)
- **System restart:** No data loss (atomic writes)
- **Worker failure:** Graceful degradation (e.g., if Writer fails, return raw chunks)

### Scalability

- **Memory footprint:** <2GB during indexing, <500MB at rest
- **10x growth support:** Architecture must handle 50,000 files without redesign
- **Storage efficiency:** Embeddings cache to avoid recomputation

---

## Component Boundaries

### 1. Ingestion Pipeline

**Input:** File path (string)  
**Output:** Success/failure (boolean)

**Responsibilities:**
- Convert any format → plain text
- Chunk text (500 tokens, 100 overlap)
- Generate embeddings
- Store in LanceDB + SQLite
- Cache embeddings
- Skip duplicates (hash-based)

**Error handling:**
- Conversion fails → skip file, log error, continue
- Embedding fails → retry 3x, then skip
- Database write fails → rollback, log, alert

**Subcomponents:**
1. Format converter (docx/pdf/html/srt → text)
2. Chunker (text → list of chunks with metadata)
3. Embedder (chunks → vectors, with caching)
4. Metadata tracker (SQLite operations)
5. Vector store (LanceDB operations)

---

### 2. Librarian (Retrieval Worker)

**Input:** 
- Query text (string)
- Mode (discovery/search/quotes/assessment)
- Filters (optional: year, file_type)

**Output:**
- List of chunks with full metadata:
  ```
  {
    'chunk_id': str,
    'chunk_text': str,
    'file_path': str,
    'file_name': str,
    'chunk_index': int,
    'similarity': float (0-1),
    'citation': str (formatted),
    'indexed_at': str (ISO datetime)
  }
  ```

**Responsibilities:**
- Query embedding generation
- Semantic search
- Result filtering
- Duplicate detection (for discovery mode)
- Quote filtering (for quote mode)
- Format output (markdown)

**Does NOT:**
- Organize by theme (that's Architect)
- Draft content (that's Writer)
- Check brand principles (that's Critic)

---

### 3. Architect (Structure Worker)

**Input:**
- List of chunks (from Librarian)
- Task context (what Alex is trying to build)

**Output:**
- Structure proposals (2-3 options):
  ```
  {
    'option_name': str,
    'format': str (workshop/article/video),
    'sections': [
      {
        'title': str,
        'content_available': int (chunk count),
        'gaps': [str] (missing topics)
      }
    ],
    'estimated_effort': str (how much new writing)
  }
  ```

**Responsibilities:**
- Thematic clustering
- Gap detection
- Structure proposal
- Effort estimation
- Feedback loop management (wait for approval)

**Does NOT:**
- Draft prose (that's Writer)
- Retrieve chunks (that's Librarian)
- Enforce brand (that's Critic)

---

### 4. Writer (Drafting Worker)

**Input:**
- Approved structure (from Architect)
- Retrieved chunks (from Librarian)
- Section to draft (from Alex)

**Output:**
- Draft prose (markdown):
  ```
  {
    'section_title': str,
    'content': str (markdown formatted),
    'citations': [str] (inline citations),
    'word_count': int,
    'gaps_filled': [str] (new content created)
  }
  ```

**Responsibilities:**
- Load identity training (IDENTITY.md, VOICE_TRAINING.md, etc.)
- Synthesize insights from chunks
- Write coherent prose
- Insert citations
- Fill gaps with new thinking (when needed)
- Match Alex's voice and patterns

**Does NOT:**
- Decide structure (that's Architect)
- Retrieve chunks (that's Librarian)
- Validate brand (submits to Critic for that)

**Critical behavior:**
- MUST cite sources inline
- MUST synthesize (not copy/paste chunks)
- MUST sound like Alex (not generic AI)
- MUST fill gaps when no chunks available (but flag them)

---

### 5. Critic (QA Worker)

**Input:**
- Draft content (from Writer)
- Context (what section this is)

**Output:**
- Critique report:
  ```
  {
    'passed': bool,
    'violations': [
      {
        'principle': str (which rule violated),
        'location': str (which part of draft),
        'severity': str (critical/warning)
      }
    ],
    'suggestions': [str],
    'voice_score': float (0-1, how Alex-like)
  }
  ```

**Responsibilities:**
- Load BRAND_PRINCIPLES.md
- Load VOICE_TRAINING.md
- Check draft against principles
- Compare voice to examples
- Flag violations
- Return to Writer if fails

**Does NOT:**
- Rewrite content (sends back to Writer)
- Make final decisions (Alex does)
- Retrieve or draft (pure QA)

**Critical behavior:**
- MUST catch "strategy before tactics" violations
- MUST flag generic AI voice
- MUST return specific feedback (not vague)
- SHOULD pass 80%+ of drafts on first try (if failing more, Writer needs tuning)

---

## Data Schemas

### SQLite Schema (Metadata)

```sql
CREATE TABLE files (
    file_hash TEXT PRIMARY KEY,           -- SHA256 of path+size+mtime
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,                       -- extension
    indexed_at TEXT NOT NULL,             -- ISO datetime
    chunk_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'indexed'
);

CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,            -- hash of file_hash + chunk_index
    file_hash TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    token_count INTEGER,
    FOREIGN KEY (file_hash) REFERENCES files(file_hash)
);

CREATE INDEX idx_file_path ON files(file_path);
CREATE INDEX idx_file_hash ON chunks(file_hash);
```

### LanceDB Schema (Vectors)

```python
# Conceptual schema (LanceDB uses PyArrow)
{
    'chunk_id': string,
    'file_hash': string,
    'file_path': string,
    'chunk_index': int,
    'chunk_text': string,
    'token_count': int,
    'vector': list[float] (384 dimensions)
}
```

### Identity Training Files (Markdown)

**IDENTITY.md:** Core frameworks and mental models  
**VOICE_TRAINING.md:** Good/bad examples  
**STRUCTURE_TEMPLATES.md:** Format-specific patterns  
**THINKING_TEMPLATES.md:** Analytical patterns  
**BRAND_PRINCIPLES.md:** Non-negotiable rules

Format: Standard markdown with clear sections. No special syntax required.

---

## Workflow Specifications

### Workflow 1: Discovery

```
1. Alex: "Show me everything on personal branding"
2. Librarian searches (mode: discovery, top_k: 100)
3. Librarian groups by year
4. Librarian detects duplicates (similarity > 0.9)
5. Librarian saves to workspace/discovery_personal_branding.md
6. Alex reviews, decides next step
```

### Workflow 2: Structure Approval Loop

```
1. Alex: "I'm writing a workshop on pricing"
2. Librarian retrieves chunks (mode: search, top_k: 50)
3. Architect analyzes chunks
4. Architect proposes 3 structures
5. SYSTEM PAUSES (waiting for approval)
6. Alex: "Option A, add section on value perception"
7. Architect refines structure
8. Architect shows updated structure
9. SYSTEM PAUSES (waiting for approval)
10. Alex: "Approved"
11. Architect passes to Writer
```

**Critical:** Steps 5 and 9 are blocking. No auto-progression.

**IMPLEMENTATION DETAIL:** How the UI handles "pause and wait for approval" is open. Possible approaches: button clicks, form submission, inline editing before approval, conversational confirmation, or other patterns. Choose based on Gradio capabilities and UX testing.

### Workflow 3: Drafting with QA Gate

```
1. Writer receives: approved structure, chunks, section to draft
2. Writer loads identity files
3. Writer drafts Section 1
4. Writer submits to Critic
5. Critic checks brand principles
6. Critic checks voice consistency
7. IF violations found:
   - Critic returns feedback to Writer
   - Writer revises
   - Loop back to step 4
8. IF passed:
   - Content goes to Alex
9. Alex polishes (rewrites for copyright + creative control)
10. Alex saves to Obsidian
```

### Workflow 4: Quote Bank (Fast Path)

```
1. Alex: "Give me 20 quotes on business strategy"
2. Librarian retrieves (mode: quotes, top_k: 50)
3. Librarian filters:
   - Length: 50-300 chars
   - Complete sentences
   - No unclear references ("this", "that")
   - Passes brand check
4. Librarian returns top 20 by similarity
5. Alex picks 5, posts to LinkedIn
6. Total time: <10 minutes
```

---

# Part 5: Build Phases

## R0: Infrastructure Setup

**Goal:** Working environment, directories, dependencies

**Deliverables:**
- Directory structure created
- Python venv with dependencies
- Syncthing configured (VPS side)
- Embedding model downloaded
- Config files created
- Git initialized

**Success criteria:**
- `python -c "import lancedb, sentence_transformers, gradio"` works
- Syncthing test file appears within 60 seconds
- Config files validate (correct YAML syntax)

**Test:** Drop test file on desktop → appears in ~/content-vault/ on VPS

**Estimated time:** 3-4 hours

---

## R1: Ingestion Pipeline

**Goal:** Any file → indexed chunks

**Deliverables:**
- File converters (all supported formats)
- Text chunker (500 tokens, 100 overlap, tiktoken)
- Embedding generator with caching
- LanceDB table + insertion
- SQLite metadata tracking
- Deduplication (hash-based)
- File watcher (auto-process new files)

**IMPLEMENTATION DETAIL - File Watcher:** How often to check for new files, whether to batch process, and how to handle stability (Syncthing mid-transfer) are open decisions. Consider: polling frequency, stability detection (file size unchanging for N seconds), batch vs one-at-a-time processing, and handling sudden large influx of files.

**Success criteria:**
- Drop .docx → indexed in <10 seconds
- Drop same file → skipped (already indexed)
- Query by filename → chunks return with citations
- Corrupted file → skipped with error log
- 100 files → indexed in <5 minutes

**Test cases:**
```python
# Automated (pytest)
def test_index_text_file():
    result = pipeline.process_file("test.txt")
    assert result == True
    assert metadata_db.is_indexed("test.txt") == True

def test_skip_duplicate():
    pipeline.process_file("test.txt")
    result = pipeline.process_file("test.txt")  # second time
    assert result == False  # skipped

def test_search_returns_citations():
    results = search("test content")
    assert len(results) > 0
    assert 'citation' in results[0]
    assert 'test.txt' in results[0]['citation']
```

**Estimated time:** 6-8 hours

---

## R2: Librarian Worker

**Goal:** Semantic search with all modes

**Deliverables:**
- Basic search (query → top-K)
- Discovery mode (group by year, find duplicates)
- Quote mode (filter for standalone quotes)
- Assessment mode (analyze single new file vs corpus)
- Citation formatting
- Markdown output

**Success criteria:**
- Search returns relevant results (manual inspection)
- Citations include source file + timestamp + chunk index
- Discovery groups by year correctly
- Quotes are 50-300 chars, standalone readable
- Assessment identifies unique vs redundant content

**Test cases:**
```python
def test_search():
    results = librarian.search("pricing strategy", top_k=30)
    assert len(results) == 30
    assert all('citation' in r for r in results)
    assert all('similarity' in r for r in results)

def test_quote_bank():
    quotes = librarian.quote_bank("business advice", count=20)
    assert len(quotes) <= 20
    assert all(50 <= len(q['text']) <= 300 for q in quotes)
```

**Estimated time:** 4-5 hours

---

## R3: Architect Worker

**Goal:** Structure proposals with feedback loop

**Deliverables:**
- Thematic analysis (using LLM)
- Gap detection
- Structure proposals (2-3 options per request)
- Effort estimation
- Markdown formatting

**Success criteria:**
- Given 30 chunks → identifies 3-5 themes
- Gaps are specific (not generic)
- Structure options are distinct (not just reworded)
- Output is actionable (Alex can pick and refine)

**Note:** LLM outputs vary, so testing is qualitative (manual inspection).

**Estimated time:** 4-5 hours

---

## R4: Writer Worker (NEW)

**Goal:** Draft prose using chunks + identity training

**DEPENDENCY NOTE:** Writer is specified to "submit to Critic" but Critic doesn't exist until R5. Implementation options:
- Build Writer with stub Critic (always returns "pass") in R4, wire real Critic in R5
- Build Writer standalone in R4, add Critic integration as part of R5
- Other approach that satisfies the requirement

**DECISION NEEDED:** VPS-Claude chooses implementation approach based on testing convenience and code organization preferences.

**Deliverables:**
- Identity file loader (all 4 markdown files)
- Chunk synthesis (combine insights)
- Voice mimicry (sound like Alex)
- Citation insertion (inline)
- Gap filling (create new content when needed)
- Submit to Critic protocol

**Success criteria:**
- Produces 500-1000 word drafts
- Cites sources inline
- Sounds like Alex (80%+ on manual inspection)
- Passes Critic on first try (80% of time)
- Flags gaps filled

**Test approach:**
```python
# Manual inspection required
def test_writer_draft():
    structure = architect.propose_structure(chunks)[0]  # pick first option
    draft = writer.draft_section(
        structure=structure,
        chunks=chunks,
        section_index=0
    )
    
    # Assertions
    assert 500 <= draft['word_count'] <= 1000
    assert len(draft['citations']) > 0
    assert all(c in draft['content'] for c in draft['citations'])
    
    # Manual: Does it sound like Alex? (subjective)
    print(draft['content'])
```

**Estimated time:** 8-10 hours (most complex worker)

---

## R5: Critic Worker

**Goal:** Brand + voice QA gate

**Deliverables:**
- Load BRAND_PRINCIPLES.md
- Load VOICE_TRAINING.md
- Violation detection
- Voice scoring (compare to examples)
- Feedback generation
- Pass/fail decision

**Success criteria:**
- Catches "tactics before strategy" violation (100%)
- Flags generic AI voice (80%+)
- Feedback is specific (not vague)
- Passes 80% of Writer drafts on first try

**Test approach:**
```python
def test_critic_catches_violation():
    bad_draft = "Here are 7 pricing hacks..."  # tactics-first
    critique = critic.critique(bad_draft, context="pricing section")
    assert critique['passed'] == False
    assert any('strategy' in v['principle'].lower() for v in critique['violations'])

def test_critic_passes_good_draft():
    good_draft = load_example_alex_draft()
    critique = critic.critique(good_draft, context="pricing section")
    assert critique['passed'] == True or len(critique['violations']) == 0
```

**Estimated time:** 4-5 hours

---

## R6: UI Integration

**Goal:** Gradio interface for full workflow

**Deliverables:**
- Multi-tab UI (Query, Structure, Draft, Save)
- Project management (create/switch)
- All worker integration
- Feedback loop implementation (blocking prompts)
- Version management (v001, v002)
- Export to markdown

**IMPLEMENTATION DETAIL - Versioning:** When versions are created (every save? manual naming? timestamp-based?) is open. Decide based on Alex's workflow preferences during testing.

**Success criteria:**
- Full workflow works: query → structure → approve → draft → critique → save
- Feedback loop blocks correctly (doesn't auto-progress)
- Outputs version properly
- Can switch between projects
- UI doesn't block on long operations

**Estimated time:** 6-8 hours

---

## Total Build Time: 35-45 hours

Across 6-9 days if working 5-6 hours/day.

---

# Part 6: Success Criteria & Validation

## How to Know It Works

### Quantitative Metrics

1. **Indexing performance:**
   - 100 files in <5 minutes ✓
   - Single file in <10 seconds ✓
   - No crashes on corrupted files ✓

2. **Query performance:**
   - Top-30 results in <3 seconds ✓
   - 83%+ relevance (manual spot-check) ✓
   - 100% citation accuracy ✓

3. **Draft quality:**
   - 500-1000 words per section ✓
   - 80%+ pass Critic on first try ✓
   - All sources cited inline ✓

### Qualitative Validation

**The Real Test (After R6):**

Alex runs this workflow:

```
1. Create project: "workshop_pricing_feb2026"
2. Query: "pricing psychology for service businesses"
3. Architect proposes 3 structures
4. Alex picks one, requests "add dynamic pricing section"
5. Architect refines, Alex approves
6. Writer drafts Section 1 (800 words)
7. Alex reads it

QUESTIONS:
- Does it sound like Alex wrote it? (voice check)
- Are sources cited correctly? (trust check)
- Is it 80% done or 20% done? (utility check)
- Would she use this workflow again? (adoption check)
```

**If Alex answers:**
- Voice: Yes, sounds like me (or close enough)
- Sources: Yes, I can verify claims
- Utility: 80% done, I just need to polish
- Adoption: Yes, this saves me hours

**Then it works.**

**If any answer is "No":**
- Voice problem → tune VOICE_TRAINING.md, adjust Writer prompts
- Source problem → fix citation logic
- Utility problem → Writer isn't synthesizing well, needs better prompts
- Adoption problem → workflow friction, UX issue

---

## Edge Cases & Error Handling

### When Things Go Wrong

**No results found:**
```
User: "Show me content on quantum physics"
System: "No results found. Searched 5,000 files, 0 matches.
        Suggestions: Check spelling, try broader terms, verify content exists."
```

**Too many results:**
```
User: "Everything on business"
System: "Found 10,000+ results. Showing top 100.
        Consider adding filters: year (2022-2024), type (workshops), or narrower topic."
```

**Corrupted file:**
```
System log: "Skipped 3 files during indexing:
- workshop_2019.docx (conversion failed: invalid format)
- notes.pdf (extraction failed: encrypted)
- transcript.srt (malformed: no text found)"

User sees: "Indexed 97/100 files. 3 skipped. See logs for details."
```

**LLM API timeout:**
```
Writer: [makes API call]
API: [timeout after 30 seconds]
Writer: Retry 1/3 [exponential backoff]
API: [timeout]
Writer: Retry 2/3
API: [timeout]
Writer: Retry 3/3
API: [timeout]
System: "Writer unavailable (API timeout). Returning raw chunks instead."
```

**Critic rejects draft 5 times:**
```
Writer → Critic: Draft v1
Critic: "Violation: tactics-first"
Writer → Critic: Draft v2
Critic: "Violation: generic voice"
Writer → Critic: Draft v3
Critic: "Violation: still generic"
Writer → Critic: Draft v4
Critic: "Violation: missing citations"
Writer → Critic: Draft v5
Critic: "Violation: tactics-first again"

System: "Writer failed to produce acceptable draft after 5 attempts.
         Returning best attempt (v3) for manual review.
         This may indicate Writer prompts need tuning."
```

---

# Part 7: What Makes This Different

## vs NotebookLM

| Feature | NotebookLM | Research Hive |
|---|---|---|
| Upload | Manual | Automatic (Syncthing) |
| Iteration | One-shot | Full feedback loop |
| Voice | Generic | Trained on Alex's corpus |
| Citations | None | Inline, traceable |
| Depth | Shallow synthesis | Deep, multi-chunk synthesis |
| Brand enforcement | None | Critic validates |
| Output | Bullets | Prose drafts |

## vs Generic RAG

| Feature | Generic RAG | Research Hive |
|---|---|---|
| Returns | Chunks | Drafted prose |
| Voice | Random | Alex's patterns |
| Structure | User decides | Architect proposes |
| QA | None | Critic validates |
| Workflow | Search → write | Search → structure → approve → draft → QA |

## vs Fine-Tuned Model

| Feature | Fine-Tuned | Research Hive |
|---|---|---|
| Cost | $30-100 initial + retraining | ~$0.30/day |
| Updates | Retrain entire model | Edit markdown files |
| Transparency | Black box | Can see what it uses |
| Flexibility | Locked after training | Adjust anytime |
| Quality | 95% | 90% (good enough) |

---

# Part 8: Future Extensions (Not Now)

After R6 is stable and validated:

**Journalism Hive:**
- Fact-checker worker (verify claims)
- Quote verifier (find original sources)
- Gap researcher (identify uncovered topics)

**Book Drafter:**
- Chapter-by-chapter organization
- Narrative arc tracking
- Character/concept consistency (for business books)
- Multi-chapter synthesis

**Integration:**
- Main Hive-Office integration (as optional Consorts)
- Shared infrastructure (Docker sandboxing)
- Cross-project memory

**DO NOT BUILD THESE NOW.** Validate core system first.

---

# Part 9: Your First Task

## Start with R0

1. Create directory structure
2. Set up Python venv
3. Install dependencies
4. Configure Syncthing (VPS side)
5. Download embedding model
6. Create config files
7. Initialize git

**Report progress in STATUS.md.**

**When R0 is complete:** Commit with `R0 GATE: infrastructure ready`

Then move to R1.

---

# Part 10: Questions to Ask When Stuck

**On requirements:**  
"Does X meet the success criteria for this phase?"

**On implementation:**  
"Is there a simpler way to achieve Y that still meets requirements?"

**On scope:**  
"Is Z essential for this phase or can it wait until later?"

**On testing:**  
"How do I prove this component works?"

**On architecture:**  
"Does this decision conflict with the stated constraints or rationale?"

Document all decisions in STATUS.md. Alex reviews at gates.

---

# End of Specification

You have:
- **Context** (the problem Alex is solving)
- **Vision** (what we're building)
- **Architecture** (decisions with rationale)
- **Requirements** (clear, testable)
- **Phases** (sequential build plan)

Now build it. Make it work. Make it good.

---

## Appendix: Key Insights

**The system is a co-author, not a librarian.**

Alex rewrites for copyright and pride, not because drafts are bad. The goal is usable 80% drafts, not perfect final copy.

**The feedback loop is non-negotiable.**

No writing happens until structure is approved. This prevents wasted tokens and frustration.

**Identity training, not fine-tuning.**

Loading markdown files is cheaper and more flexible than fine-tuning models.

**Four workers, not one.**

Specialized roles keep contexts clean and costs low.

**Privacy is a hard constraint.**

Corpus never leaves VPS. No external APIs for embeddings or vectors.

**The Writer is the missing piece.**

Previous specs had search and organization. This adds actual drafting.

Build this well. Alex needs it.

---

## Appendix A: Implementation Gaps & Open Decisions

This section consolidates all areas where VPS-Claude has implementation freedom. Make decisions based on testing, performance, and code clarity.

### 1. Worker Prompt Engineering

**Gap:** Exact prompt structures for Writer and Critic workers

**What's specified:** 
- Writer loads 4 identity files + chunks
- Critic loads brand principles + voice examples
- Both produce structured outputs

**What's open:**
- Exact wording of system prompts
- How to format identity files in prompts
- Token budget allocation
- Whether to use separate prompts for different content types
- Retry strategies when outputs are malformed

**Decide based on:** Model performance testing, token efficiency, output quality

---

### 2. R4/R5 Build Sequencing

**Gap:** How Writer interacts with non-existent Critic during R4

**Options:**
- Stub Critic in R4 (always returns pass)
- Build Writer standalone, add Critic integration in R5
- Build both workers in parallel, integrate in R5
- Other approach

**Decide based on:** Testing convenience, code organization preference

---

### 3. Feedback Loop UI Mechanics

**Gap:** How Gradio implements "pause and wait for approval"

**What's specified:**
- System must block before drafting
- Alex must be able to revise structure
- No auto-progression

**What's open:**
- Button-based approval vs conversational
- Inline editing of structure vs separate revision step
- How to display structure options (tabs, dropdown, radio buttons)
- Whether Alex can jump back to earlier approval points

**Decide based on:** Gradio capabilities, UX testing with Alex

---

### 4. File Watcher Implementation

**Gap:** How to detect and process new files from Syncthing

**What's specified:**
- Auto-process files that appear in watched directory
- Must handle Syncthing mid-transfer (partial files)
- Must handle large influx (100+ files at once)

**What's open:**
- Polling frequency (every N seconds?)
- Stability detection method (file size check? Syncthing metadata?)
- Batch processing vs one-at-a-time
- Queue management for large batches
- Error recovery if processing fails mid-batch

**Decide based on:** Performance testing, Syncthing behavior observation

---

### 5. Version Management

**Gap:** When and how versions are created

**What's specified:**
- System supports versioning (v001, v002, etc.)
- Versions persist

**What's open:**
- Auto-version on every save vs manual naming
- Timestamp-based vs sequential numbering
- Whether to keep all versions or prune old ones
- UI for switching between versions

**Decide based on:** Alex's workflow preferences during R6 testing

---

### 6. Configuration Structure

**Gap:** Config file format and contents

**What's needed:**
- Model assignments (which LLM for which worker)
- API keys storage
- Default parameters (top_k, chunk size, etc.)
- File paths (Syncthing directory, output directory)

**What's open:**
- YAML vs TOML vs JSON
- Environment variables vs config file vs both
- How to handle secrets (API keys)
- Whether to support multiple config profiles

**Decide based on:** Security best practices, ease of editing

---

### 7. Embedding Cache Strategy

**Gap:** How to cache embeddings to avoid recomputation

**What's specified:**
- Must cache to avoid re-embedding on every query
- Must invalidate when file changes

**What's open:**
- Cache storage (SQLite table, separate file, in-memory)
- Cache key (file hash, content hash, both)
- Invalidation strategy (timestamp, hash comparison)
- Cache size limits

**Decide based on:** Storage efficiency, lookup speed

---

### 8. Error Recovery and Logging

**Gap:** How to handle and log failures

**What's specified:**
- Must handle corrupted files gracefully
- Must retry LLM API calls
- Must not crash on malformed data

**What's open:**
- Logging level and format
- Where logs are stored
- Whether to alert Alex on errors vs silent logging
- Retry backoff strategy (exponential, linear, fixed)
- Maximum retry attempts

**Decide based on:** Debugging needs, production stability

---

### 9. Chunk Size and Overlap

**Gap:** Exact chunking parameters

**What's suggested:** 500 tokens, 100 overlap (using tiktoken)

**What's open:**
- Whether these are optimal (may need tuning based on retrieval quality)
- Whether to vary by content type (transcripts vs polished docs)
- Whether to use sentence boundaries vs hard token cuts

**Decide based on:** Retrieval quality testing, semantic coherence

---

### 10. Query Result Ranking

**Gap:** How to rank and filter search results

**What's specified:**
- Use semantic similarity
- Return top-K (default 30, max 100)

**What's open:**
- Whether to apply re-ranking after initial retrieval
- Whether to diversify results (avoid all chunks from same file)
- Whether to boost recent content vs old content
- How to handle ties in similarity scores

**Decide based on:** Retrieval quality, Alex's feedback

---

## Notes on Decision-Making

**When in doubt:**
1. Choose simpler over complex
2. Choose testable over clever
3. Choose documented over assumed
4. Ask in STATUS.md if a decision feels architectural (not just tactical)

**Document all decisions:** When you make a choice on any gap above, note it in STATUS.md with brief rationale. This creates a decision log for future reference.

---

## Appendix B: Dependencies Reference

Complete list of external libraries and tools required.

### Core Dependencies

```
# Vector storage and search
lancedb>=0.3.0

# Embeddings
sentence-transformers>=2.2.0
torch>=2.0.0  # Required by sentence-transformers

# LLM providers
google-generativeai>=0.3.0  # Gemini API
# OR anthropic>=0.8.0  # If using Claude
# OR openai>=1.0.0  # If using OpenAI

# UI framework
gradio>=4.0.0

# File processing
python-docx>=0.8.11  # Word documents
PyPDF2>=3.0.0  # PDF extraction
pypandoc>=1.11  # Format conversion (requires pandoc system package)
pysrt>=1.1.2  # Subtitle/transcript files

# Chunking and tokens
tiktoken>=0.5.0  # OpenAI's tokenizer

# Database
# (sqlite3 included in Python standard library)

# Utilities
pyyaml>=6.0  # Config files (if using YAML)
python-dotenv>=1.0.0  # Environment variables
watchdog>=3.0.0  # File system watching (if using)
```

### System Dependencies

```bash
# Pandoc (for document conversion)
# Installation varies by OS - VPS-Claude to determine method

# Python 3.10+ (specified earlier: Python 3.12 preferred)
```

### Optional/Alternative Dependencies

```
# If using ChromaDB instead of LanceDB:
# chromadb>=0.4.0

# If using Pinecone instead of local:
# pinecone-client>=2.2.0

# Additional format support:
# openpyxl>=3.1.0  # Excel files
# markdown>=3.5.0  # Enhanced markdown parsing
# beautifulsoup4>=4.12.0  # HTML cleaning
```

### Development Dependencies

```
pytest>=7.4.0
pytest-asyncio>=0.21.0  # If using async
black>=23.0.0  # Code formatting
ruff>=0.1.0  # Linting
```

### Installation Notes

**All dependencies should be installed in a virtual environment.**

**DECISION NEEDED:** 
- Exact version pinning strategy (pin major.minor or major only?)
- Whether to use requirements.txt, pyproject.toml, or both
- Whether to separate dev dependencies

**System package requirements:**
- Pandoc must be installed at system level
- Installation method depends on VPS OS (apt, yum, etc.)

### Model Downloads

**sentence-transformers model:** `all-MiniLM-L6-v2`
- ~80MB download
- Happens automatically on first import
- Cached in `~/.cache/torch/sentence_transformers/`

**IMPLEMENTATION NOTE:** First run will download model. Add progress indicator or pre-download in R0 setup.

---

## End of Specification

Complete spec with:
- Context and problem statement
- Architecture and decisions
- Requirements and constraints
- Build phases
- Success criteria
- Open decisions documented
- Dependencies listed

Ready for VPS-Claude implementation.
