# S1 Build Specification: Memory Architecture

**Date:** 2026-02-18  
**Status:** Active build specification  
**Companion doc:** memory_architecture_vision.md (read for context)

---

## WHAT WE'RE BUILDING

A memory system that makes the Queen intelligent, not just conversational.

Three capabilities:
1. **Continuity** - branching conversation history (JSONL DAG)
2. **Knowledge** - persistent facts and lessons (structured memory hierarchy)
3. **Agency** - learning from experience without being told how (signal-based consolidation)

This replaces HISTORY.md (flat log) and upgrades MEMORY.md (unstructured text) into a real memory architecture.

---

## WHY THIS MATTERS

Current state: Every conversation starts from scratch. The Queen has no working memory. She doesn't learn from experience. She can't act FOR Alex without being told how every time.

After S1: The Queen remembers who Alex is, what infrastructure she manages, what workflows worked, what approaches failed. She gets smarter over time. She can act autonomously based on learned patterns.

---

## CONTEXT DOCUMENTS

Before starting, read these for full context:

1. **memory_architecture_vision.md** - the complete system design (what and why)
2. **PIMONO_DAG_REFERENCE_v2.md** - JSONL DAG implementation pattern
3. **IDENTITY.md** and **brand_voice.md** - communication standards (but these become USER DATA, not core code)

Key insight from vision doc: Core system (permanent) vs User data (wipeable). Everything in memory/ is user-specific and must be factory-resetable.

---

## IMPLEMENTATION SEQUENCE

Build in this exact order. Each step has: goal, deliverables, tests, integration point.

### S1.1: JSONL DAG (conversation branching)

**Goal:** Replace flat HISTORY.md with branching conversation tree.

**Read first:** PIMONO_DAG_REFERENCE_v2.md (contains Python port code)

**Deliverables:**
```python
# File: queen-alpha/src/memory/session.py

@dataclass
class SessionEntry:
    type: str
    id: str = field(default_factory=lambda: uuid4().hex)
    parent_id: Optional[str] = None

@dataclass
class MessageEntry(SessionEntry):
    type: str = "message"
    role: str = ""           # "user", "assistant", "system", "tool_result"
    content: str = ""
    token_count: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class CompactionEntry(SessionEntry):
    type: str = "compaction"
    summary: str = ""
    first_kept_entry_id: str = ""
    tokens_before: int = 0

class SessionManager:
    def __init__(self, path: Optional[str] = None):
        # In-memory mode if path=None
        # JSONL file mode if path provided
        pass
    
    def append(self, role: str, content: str, **kwargs) -> str:
        # Create message entry, set parent_id to current leaf, write to file
        pass
    
    def branch(self, entry_id: str) -> None:
        # Move leaf pointer to earlier entry (next append creates fork)
        pass
    
    def get_path(self, leaf_id: str = None) -> list[SessionEntry]:
        # Walk from leaf to root, return ordered list
        pass
    
    def build_context(self, leaf_id: str = None) -> list[dict]:
        # Build LLM message list (handle compaction if present)
        pass
    
    @staticmethod
    def create(cwd: str, path: str = None) -> 'SessionManager':
        # Create new session with header
        pass
    
    @staticmethod
    def open(path: str) -> 'SessionManager':
        # Load existing session
        pass
    
    @staticmethod
    def in_memory() -> 'SessionManager':
        # Testing mode, no file I/O
        pass
```

**File format:**
```jsonl
{"type": "session", "id": "abc123", "cwd": "/home/alex/project", "timestamp": "2026-02-18T10:00:00Z"}
{"type": "message", "id": "node_001", "parent_id": null, "role": "user", "content": "Hello", "timestamp": "..."}
{"type": "message", "id": "node_002", "parent_id": "node_001", "role": "assistant", "content": "Hi", "timestamp": "..."}
```

**Integration point:**
```python
# In nanobot's context builder, replace:
# history = read_file("HISTORY.md")

# With:
session = SessionManager.open("sessions/current.jsonl")
history = session.build_context()
```

**Tests:**
- Create session, add 10 messages, all appear in JSONL
- Branch at message 5, add 3 more, both branches exist
- get_path from each leaf returns correct history
- build_context returns only messages on active branch
- Corrupt last line, reload, loads successfully (crash recovery)
- in_memory mode works identically

**Gate:** All tests green. Conversation history is a DAG, not a list.

---

### S1.2: Memory hierarchy scaffold

**Goal:** Create the directory structure and templates for all memory types.

**Deliverables:**
```
memory/
  identity/
    README.md              # explains purpose of this folder
    user.md.template       # schema with comments
    constraints.md.template
    preferences.md.template
    context.md.template
    worker_shared.md.template
  
  systems/
    README.md
    infrastructure.md.template
    tools.md.template
    topology.md.template
  
  projects/
    README.md
    _template/            # copy this to start new project
      README.md
      decisions.md
      blockers.md
      todos.md
      changelog.md
      working_memory.yaml.template
  
  procedural/
    README.md
    workflows/
      README.md
    fixes/
      README.md
  
  lessons/
    README.md
    successes.md.template
    failures.md.template
    patterns.md.template
  
  skills/
    README.md
    _system/              # built-in skills
      README.md
    _user/                # user-created skills
      README.md
    skills_registry.json.template
```

**Template format example (user.md.template):**
```markdown
# User Identity

## Core Info
name: [Your name]
role: [What you do in one sentence]
languages: [Languages you work in]
timezone: [Your timezone]

## Metadata
confidence: HIGH
source: user_stated
timestamp: [ISO timestamp]
last_verified: [ISO timestamp or null]
```

**Integration point:**
```python
# In prompt builder:
if os.path.exists("memory/identity/user.md"):
    identity = load_memory_file("memory/identity/user.md")
else:
    identity = None  # fresh boot, needs onboarding
```

**Tests:**
- All directories exist after initialization
- All README files present and have content
- All templates have schema comments
- Fresh boot detects empty memory/ and flags it

**Gate:** Directory structure matches schema. Templates are valid.

---

### S1.3: Confidence tracking

**Goal:** Every memory entry has confidence metadata. Queen knows what she knows vs guesses.

**Deliverables:**
```python
# File: queen-alpha/src/memory/entry.py

@dataclass
class MemoryEntry:
    content: str
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    source: str      # "user_stated", "verified_command", "inferred_from_logs", etc.
    timestamp: str
    last_verified: Optional[str] = None
    needs_reverification: bool = False

def write_memory_entry(filepath: str, entry: MemoryEntry) -> None:
    # Append to file with YAML frontmatter
    pass

def read_memory_entries(filepath: str) -> list[MemoryEntry]:
    # Parse file, return all entries with metadata
    pass

def decay_confidence(entry: MemoryEntry) -> MemoryEntry:
    # If entry is old, reduce confidence level
    age_days = (now - entry.timestamp).days
    if age_days > 90 and entry.confidence == "MEDIUM":
        entry.confidence = "LOW"
    # etc.
    pass
```

**File format (in memory/ files):**
```yaml
---
content: "Docker version is 24.0.7"
confidence: MEDIUM
source: inferred_from_logs
timestamp: 2026-02-18T10:16:00Z
last_verified: null
needs_reverification: false
---
```

**Integration point:**
```python
# When Queen retrieves memory:
entries = read_memory_entries("memory/systems/tools.md")
for entry in entries:
    if entry.confidence == "HIGH":
        # state as fact
    elif entry.confidence == "MEDIUM":
        # state with caveat
    else:
        # flag for verification
```

**Tests:**
- Write entry with HIGH confidence, read back correctly
- Confidence decays after 30/90 days as specified
- Retrieval respects confidence levels in prompt

**Gate:** All memory writes include metadata. Retrieval uses confidence.

---

### S1.4: Signal detection and consolidation

**Goal:** Queen consolidates memory when something meaningful happens, not on count/time triggers.

**Deliverables:**
```python
# File: queen-alpha/src/memory/consolidation.py

def detect_signal(event: dict) -> Optional[str]:
    """
    Detect if event is consolidation-worthy.
    Returns signal type or None.
    """
    if event["type"] == "task_complete" and event["success"]:
        return "task_success"
    
    if event["type"] == "task_complete" and event["attempts"] >= 3:
        return "task_failure"
    
    if event["type"] == "user_correction":
        return "correction"
    
    if event["type"] == "pattern_recognized":
        return "pattern"
    
    if event["type"] == "skill_created":
        return "new_skill"
    
    if event["type"] == "decision_logged":
        return "decision"
    
    return None

def consolidate(signal_type: str, event: dict) -> None:
    """
    Extract lesson/workflow based on signal type.
    Write to appropriate memory location.
    """
    if signal_type == "task_success":
        workflow = extract_workflow(event)
        write_to(f"memory/procedural/workflows/{task_type}.md", workflow)
    
    elif signal_type == "task_failure":
        lesson = extract_failure_lesson(event)
        append_to("memory/lessons/failures.md", lesson)
    
    elif signal_type == "correction":
        update = extract_correction(event)
        update_file(relevant_memory_file, update)
    
    # etc. for other signal types
```

**Hook into agent loop:**
```python
# After every tool execution:
event = {
    "type": infer_event_type(tool_result),
    "success": tool_result.success,
    # ... other fields
}

signal = detect_signal(event)
if signal:
    consolidate(signal, event)
```

**Tests:**
- Task success triggers workflow extraction
- Task failure after 3 attempts triggers failure logging
- User correction triggers memory update
- Pattern recognition triggers workflow creation
- No consolidation on message count or time elapsed

**Gate:** All 6 triggers fire correctly. Memory gets written to right location.

---

### S1.5: Onboarding protocol

**Goal:** New user can initialize their profile in 5-10 minutes via structured conversation.

**Deliverables:**
```python
# File: queen-alpha/src/onboarding.py

class OnboardingFlow:
    def __init__(self, user_interface):
        self.ui = user_interface
        self.responses = {}
    
    def run_phase_1_identity(self):
        """Core identity (required)"""
        self.responses["name"] = self.ui.ask("What's your name?")
        self.responses["role"] = self.ui.ask("What do you do? (One sentence)")
        self.responses["languages"] = self.ui.ask("Languages you work in?")
        self.responses["constraints"] = self.ui.ask("Any absolute constraints?")
        
        write_to("memory/identity/user.md", self.responses)
    
    def run_phase_2_systems(self):
        """Infrastructure (optional)"""
        # similar structure
        pass
    
    def run_phase_3_projects(self):
        """Current work (optional)"""
        # similar structure
        pass
    
    def run_phase_4_preferences(self):
        """Communication style (optional)"""
        # similar structure
        pass
    
    def run_complete(self):
        """All phases in sequence"""
        self.run_phase_1_identity()
        if self.ui.ask("Continue to systems setup? (yes/no)") == "yes":
            self.run_phase_2_systems()
        # etc.
```

**Integration:**
```python
# On boot:
if not os.path.exists("memory/identity/user.md"):
    print("Fresh boot. Run /onboard to initialize.")

# When user runs /onboard:
flow = OnboardingFlow(telegram_interface)
flow.run_complete()
```

**Tests:**
- Complete onboarding creates all identity files
- Minimal onboarding (phase 1 only) creates functional profile
- Phases can be run independently (redo just identity)
- Fresh boot detects missing profile and prompts

**Gate:** New user can onboard in <10 minutes. Profile is functional.

---

### S1.6: Factory reset

**Goal:** Wipe all user data while preserving core system. Make Queen replicable.

**Deliverables:**
```python
# File: queen-alpha/src/admin.py

def factory_reset(confirm: bool = False) -> None:
    """
    Reset Queen to fresh state.
    Requires confirmation to prevent accidents.
    """
    if not confirm:
        print("This will delete all user data.")
        print("Type CONFIRM to proceed.")
        return
    
    # 1. Create backup
    timestamp = datetime.now().isoformat()
    backup_path = f"exports/backup_{timestamp}.zip"
    create_zip(backup_path, ["memory/", "sessions/", "skills/_user/"])
    
    # 2. Clear user data
    shutil.rmtree("memory/")
    shutil.rmtree("sessions/")
    shutil.rmtree("skills/_user/")
    
    # 3. Reinitialize structure
    initialize_memory_hierarchy()  # S1.2 function
    
    # 4. Reboot
    print(f"Reset complete. Backup saved to {backup_path}")
    print("Run /onboard to initialize new profile.")
```

**Integration:**
```python
# Command handler:
if command == "/factory-reset":
    factory_reset()
    if input("Type CONFIRM: ") == "CONFIRM":
        factory_reset(confirm=True)
```

**Tests:**
- Reset creates backup before deleting
- Reset clears memory/, sessions/, skills/_user/
- Reset preserves src/, templates/, docs/
- Post-reset boot works (prompts for onboarding)
- Backup can be restored manually

**Gate:** Can reset to fresh state. Core system survives. Backup exists.

---

### S1.7: Retrieval integration

**Goal:** Queen loads relevant memory based on context, not everything.

**Deliverables:**
```python
# File: queen-alpha/src/memory/retrieval.py

def build_prompt_context() -> str:
    """
    Load always-loaded memory + on-demand based on current task.
    """
    context = []
    
    # Always loaded
    context.append(load_if_exists("memory/identity/user.md"))
    context.append(load_if_exists("memory/identity/constraints.md"))
    context.append(load_if_exists("memory/identity/preferences.md"))
    
    # Current conversation branch (last 20 messages)
    session = SessionManager.open("sessions/current.jsonl")
    context.append(session.build_context(limit=20))
    
    # Active project (if any)
    if active_project := get_active_project():
        context.append(load(f"memory/projects/{active_project}/working_memory.yaml"))
    
    # On-demand based on current task
    if current_task_type := infer_task_type():
        # Check for similar workflow
        workflow = search_memory(f"memory/procedural/workflows/{current_task_type}.md")
        if workflow:
            context.append(workflow)
        
        # Check for known failures
        failures = search_memory("memory/lessons/failures.md", current_task_type)
        if failures:
            context.append(failures)
    
    return "\n\n".join(context)
```

**Search implementation (basic grep):**
```python
def search_memory(filepath: str, keyword: str = None) -> Optional[str]:
    """
    Basic keyword search in memory files.
    Upgrade to semantic search later if needed.
    """
    if not keyword:
        return load_if_exists(filepath)
    
    # Grep for keyword
    with open(filepath) as f:
        lines = f.readlines()
    
    # Return paragraphs containing keyword
    matches = [line for line in lines if keyword.lower() in line.lower()]
    return "\n".join(matches) if matches else None
```

**Integration:**
```python
# In LLM prompt builder:
system_prompt = f"""
{CORE_RULES}  # permanent operational rules

{build_prompt_context()}  # memory retrieval

You are Queen-Alpha. [rest of prompt]
"""
```

**Tests:**
- Identity always loaded (if exists)
- Current conversation branch loaded (last 20 messages)
- Relevant workflow loaded when task starts
- Irrelevant memory NOT loaded (doesn't pollute context)
- Search finds keywords in memory files

**Gate:** Context is focused. Relevant memory loads. Irrelevant doesn't.

---

## VERIFICATION CHECKLIST

Before S1 is "done", verify all of these:

**Functional:**
- [ ] Can create/branch/traverse JSONL DAG conversations
- [ ] Memory hierarchy exists with all documented folders
- [ ] Confidence tracking works on all memory writes
- [ ] All 6 signal triggers fire correctly and write to right location
- [ ] Onboarding creates functional user profile in <10 minutes
- [ ] Factory reset wipes user data, preserves core, creates backup
- [ ] Retrieval loads relevant memory based on context

**Replicability (critical):**
- [ ] Can delete memory/ entirely and Queen still boots
- [ ] Fresh boot prompts for onboarding or import
- [ ] No hardcoded references to "Alex" in core code
- [ ] Two separate users can onboard different profiles
- [ ] Core operational rules work without any memory/ data

**Quality:**
- [ ] All pytest tests green
- [ ] No temp files left after execution
- [ ] Idempotent (can run twice safely)
- [ ] Evidence-based (claims verified before reporting)

All boxes checked → S1 complete.

---

## COMMON PITFALLS (AVOID THESE)

**Don't:**
- Hardcode user data in core code (IDENTITY.md belongs in memory/, not src/)
- Fire consolidation on message count (signal-based only)
- Load all memory into context (query-driven, focused retrieval)
- Skip confidence metadata (every memory entry needs it)
- Make onboarding longer than 10 minutes (keep it fast)
- Delete data without backup (factory reset must create archive)
- Assume JSONL is forever (design for SQLite migration later)

**Do:**
- Keep core system separate from user data
- Test with two different user profiles to verify replicability
- Verify before claiming success (operational rule #1)
- Clean up temp files (operational rule #3)
- Write idempotent scripts (operational rule #2)
- Document decisions in code comments

---

## SUCCESS CRITERIA

S1 is successful when:

1. **The Queen has memory** - she remembers who Alex is, what infrastructure she manages, what approaches worked/failed
2. **The Queen learns** - after doing something successfully, she doesn't need to be told how next time
3. **The Queen is replicable** - Bob can deploy his own Queen with zero Alex-specific data
4. **The Queen gets smarter** - over time, her procedural memory grows and she becomes more capable

Not just a chatbot. An agent with persistent knowledge who improves through experience.

That's what S1 delivers.
