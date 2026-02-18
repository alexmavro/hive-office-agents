# Pi-mono session DAG: reference for Python port (v2)

**Purpose:** This document describes how pi-mono (the engine behind OpenClaw) implements its JSONL tree-based session system. VPS-Claude should use this as the pattern to port into Python for Queen-Alpha's memory system. Do NOT clone pi-mono. Do NOT install any TypeScript. Just read this and build the Python equivalent.

**Sources verified against:** pi-mono SDK docs, extensions API, CHANGELOG, OpenClaw session-management deep-dive.

---

## The core idea

Every conversation is stored as a single `.jsonl` file. Each line is a JSON object (a "node"). Each node has an `id` and a `parentId`. This forms a tree, not a list.

Linear chat history looks like this:
```
msg1 -> msg2 -> msg3 -> msg4
```

Pi-mono's tree looks like this:
```
msg1 -> msg2 -> msg3 -> msg4 (branch A)
                  \
                   -> msg3b -> msg4b (branch B, created when user retried from msg2)
```

All branches live in the same file. Nothing gets deleted. Branching just means adding a new node that points to an earlier parent.

---

## File format

### Line 1: session header

```json
{"type": "session", "id": "abc123", "cwd": "/home/user/project", "timestamp": "2026-02-17T10:00:00Z", "parentSession": null}
```

Fields:
- `type`: always "session" for the header
- `id`: unique session identifier
- `cwd`: working directory (context for where this session operates)
- `timestamp`: creation time
- `parentSession`: null or ID of a parent session (for forked sessions)

### Lines 2+: session entries (the tree nodes)

Every entry after the header has this base shape:

```json
{"type": "<entry_type>", "id": "<unique_id>", "parentId": "<parent_node_id_or_null>", ...type-specific fields}
```

For `message` type entries, pi-mono NESTS the message data inside a `message` sub-object:

```json
{"type": "message", "id": "node_001", "parentId": null, "message": {"role": "user", "content": [{"type": "text", "text": "Hello"}]}}
{"type": "message", "id": "node_002", "parentId": "node_001", "message": {"role": "assistant", "content": [{"type": "text", "text": "Hi there"}]}}
{"type": "message", "id": "node_003", "parentId": "node_002", "message": {"role": "user", "content": [{"type": "text", "text": "Write me a script"}]}}
{"type": "message", "id": "node_004", "parentId": "node_003", "message": {"role": "assistant", "content": [{"type": "text", "text": "Here's the script..."}]}}
```

Important details about pi-mono's format:
- The first entry has `parentId: null` (it's the root).
- `content` in pi-mono is an ARRAY of content blocks (supporting multimodal: text, images, etc.), not a plain string.
- Tool results use `role: "toolResult"` (camelCase) and include `toolName` and optional `details` fields.

### Entry types

Pi-mono supports several entry types:

| type | What it is | Enters LLM context? |
|---|---|---|
| `message` | User, assistant, or tool result message | Yes |
| `custom_message` | Extension-injected message | Yes (but can be hidden from UI) |
| `custom` | Extension state storage | No |
| `compaction` | Summary of older messages after compaction | Yes (replaces the messages it summarized) |
| `branch_summary` | Summary created when navigating away from a branch | Yes |
| `label` | Bookmark/marker on an entry | No |

For Queen-Alpha's initial port, you only need `message` and `compaction`. The others come later.

---

## How branching works

Branching happens when you create a new node whose `parentId` points to an EARLIER node (not the current leaf). The old branch stays in the file. The new branch grows from the fork point.

Example: User has a 4-message conversation, then wants to retry from message 2.

Before retry:
```
node_001 (user) -> node_002 (assistant) -> node_003 (user) -> node_004 (assistant)
                                                                ^ current leaf
```

After retry (user sends a different message from node_002):
```
node_001 (user) -> node_002 (assistant) -> node_003 (user) -> node_004 (assistant)
                                       \
                                        -> node_005 (user, new branch) -> node_006 (assistant)
                                                                           ^ new leaf
```

In the JSONL file, node_005 simply has `"parentId": "node_002"`. That's it. No deletion, no restructuring.

---

## Context reconstruction (the critical algorithm)

When the LLM needs to generate a response, it needs a LINEAR history (not a tree). Pi-mono reconstructs this by walking from the current leaf node backward through `parentId` links to the root.

### Algorithm: get_path(leaf_id)

```
function get_path(leaf_id):
    path = []
    current = get_entry(leaf_id)
    while current is not null:
        path.prepend(current)
        current = get_entry(current.parentId)
    return path
```

This returns a flat list: [root, ..., leaf]. That list IS the conversation history for this branch.

Nodes on OTHER branches are invisible. They exist in the file but are never included in the context for this branch. Each branch has its own "subjective reality."

### Building LLM context (separate from raw path)

Pi-mono has a separate `buildSessionContext()` method that transforms the raw path into what actually gets sent to the LLM. This method:

1. Calls get_path() to get the raw node chain
2. Checks for compaction entries in the path (see Compaction section below)
3. Filters out non-message entry types (custom, label, etc.)
4. Formats the remaining message entries into the LLM's expected message format

This separation matters: `get_path()` gives you ALL nodes on the branch. `build_context()` gives you only what the LLM should see.

---

## SessionManager API (the interface to port)

Pi-mono's SessionManager exposes these methods. Verified against SDK docs and extensions API.

### Core read operations

| Method | Returns | What it does |
|---|---|---|
| `getEntries()` | All entries | Every entry in the file, excluding the header. Returns a defensive copy. |
| `getTree()` | Tree structure | All entries organized as a tree (each node knows its children). |
| `getPath()` | List of entries | Walk from root to current leaf. The raw branch history. |
| `getBranch()` | List of entries | Same concept as getPath(). Used in the extensions API. |
| `getLeafEntry()` | Single entry | The current tip of the active branch (the full entry object). |
| `getLeafId()` | String | Just the ID of the current leaf entry. |
| `getEntry(id)` | Single entry | Look up any entry by ID. |
| `getChildren(id)` | List of entries | Direct children of a given entry. Used for tree visualization. |
| `getLabel(id)` | String or null | Get the label/bookmark on an entry. |
| `buildSessionContext()` | LLM-ready messages | Builds the actual context to send to the LLM (handles compaction, filters non-message types). |

### Core write operations

| Method | What it does |
|---|---|
| `append(entry)` | Add a new entry to the JSONL file. The entry's parentId should be the current leaf. |
| `branch(entryId)` | Move the "current leaf pointer" to an earlier entry. The next append creates a fork. |
| `branchWithSummary(id, summary)` | Same as branch, but also creates a branch_summary entry for the old branch. |
| `appendLabelChange(id, label)` | Set a bookmark/label on an entry. |
| `appendCustomEntry(type, data)` | Store extension/plugin state (not sent to LLM). |

### Session lifecycle

| Method | What it does |
|---|---|
| `create(cwd)` | Create a new session file with a header. |
| `open(path)` | Open an existing session file. |
| `inMemory()` | Create an in-memory session (no file). Useful for testing. |
| `list(cwd)` | List available session files for a given working directory. |
| `createBranchedSession(leafId)` | Extract a branch into a new separate session file. |

---

## Compaction (context window management)

Sessions grow. Eventually they exceed the LLM's context window. Compaction summarizes older messages into a single `compaction` entry while keeping recent messages intact.

### How it works

1. Determine which messages to keep (the recent ones, based on `keepRecentTokens` setting).
2. Everything before the kept messages gets summarized by the LLM.
3. A `compaction` entry is appended to the file:
   ```json
   {"type": "compaction", "id": "compact_001", "parentId": "node_014", "summary": "The user asked about Python scripts. The assistant provided three examples...", "firstKeptEntryId": "node_015", "tokensBefore": 45000}
   ```
4. When reconstructing context, the compaction summary replaces all older messages.

### Context reconstruction WITH compaction

```
function build_context(leaf_id):
    path = get_path(leaf_id)
    
    # Filter to only message and compaction types
    relevant = [e for e in path if e.type in ("message", "compaction")]
    
    # Check if there's a compaction entry in the path
    compaction = find_most_recent_compaction(relevant)
    
    if compaction exists:
        # Start from compaction summary + messages after firstKeptEntryId
        context = [system_msg_from(compaction.summary)] + messages_after(compaction.firstKeptEntryId)
    else:
        # Use full message path
        context = [format_for_llm(e) for e in relevant if e.type == "message"]
    
    return context
```

The full conversation history is NEVER deleted from the file. Compaction only affects what the LLM sees. You can always use `getEntries()` or `getTree()` to see everything.

### When compaction triggers (pi-mono's rules)

Two triggers in pi-mono:
- **Overflow recovery:** The LLM returns a context-too-long error. Compact, then retry.
- **Threshold maintenance:** After a successful turn, if `contextTokens > contextWindow - reserveTokens`, compact proactively.

For Queen-Alpha Phase 1: implement compaction as a manual method. Don't auto-trigger it yet. That comes later when we have the token tracker.

---

## The current leaf pointer

The "current leaf" is just the last entry in the active branch. Pi-mono tracks this internally. When you `branch(entryId)`, you move the pointer to an earlier node. The next `append()` creates a child of that node, starting a new branch.

For the Python port, track this as a simple variable: `self.current_leaf_id`. It gets updated on `append()` and `branch()`.

---

## What to port (Python implementation plan)

### Design decisions: where we deliberately simplify

Pi-mono is TypeScript and built for a TUI coding agent with extensions, themes, and package management. We're building a Python orchestrator. Some things should be different:

1. **Flat message fields, not nested.** Pi-mono nests message data inside `{"message": {"role": ..., "content": ...}}`. Our Python entries will flatten this: the entry itself carries `role` and `content` as top-level fields. Simpler to work with, less indirection. The JSONL file format will reflect this (our files won't be compatible with pi-mono's files, and that's fine).

2. **Content as string, not array.** Pi-mono uses content arrays for multimodal support (`[{"type": "text", "text": "..."}]`). We use plain strings for Phase 1. When we need multimodal later, we change `content` to accept `Union[str, list]`.

3. **snake_case, not camelCase.** Pi-mono uses `parentId`, `toolResult`, `firstKeptEntryId`. We use `parent_id`, `tool_result`, `first_kept_entry_id`. Python convention.

4. **UUID for IDs.** Pi-mono uses Snowflake-style hex IDs. We use `uuid4().hex` (32-char hex string). Simpler, no need for a Snowflake generator.

### Data structures

```python
from dataclasses import dataclass, field, asdict
from typing import Optional, Union
from uuid import uuid4
from datetime import datetime, timezone
import json

@dataclass
class SessionHeader:
    type: str = "session"
    id: str = field(default_factory=lambda: uuid4().hex)
    cwd: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    parent_session: Optional[str] = None

@dataclass
class SessionEntry:
    """Base for all entry types. Every entry has these fields."""
    type: str               # "message", "compaction"
    id: str = field(default_factory=lambda: uuid4().hex)
    parent_id: Optional[str] = None

@dataclass
class MessageEntry(SessionEntry):
    type: str = "message"
    role: str = ""          # "user", "assistant", "system", "tool_result"
    content: str = ""       # plain string for Phase 1
    # metadata (optional, not sent to LLM, useful for tracking)
    token_count: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class CompactionEntry(SessionEntry):
    type: str = "compaction"
    summary: str = ""
    first_kept_entry_id: str = ""
    tokens_before: int = 0
```

### SessionManager class

```python
class SessionManager:
    def __init__(self, path: Optional[str] = None):
        self.path = path           # None = in-memory mode (for testing)
        self.header: SessionHeader = SessionHeader()
        self._entries: dict[str, SessionEntry] = {}   # id -> entry (in-memory index)
        self._order: list[str] = []                   # insertion order (for getEntries)
        self.current_leaf_id: Optional[str] = None
        if path and os.path.exists(path):
            self._load()
    
    # --- Read operations ---
    
    def get_entries(self) -> list[SessionEntry]:
        """All entries in insertion order, excluding header."""
        return [self._entries[eid] for eid in self._order]
    
    def get_path(self, leaf_id: str = None) -> list[SessionEntry]:
        """Walk from root to the given leaf (or current leaf). Returns list ordered root-first."""
        target = leaf_id or self.current_leaf_id
        path = []
        current_id = target
        while current_id is not None:
            entry = self._entries[current_id]
            path.append(entry)
            current_id = entry.parent_id
        path.reverse()
        return path
    
    def get_leaf_entry(self) -> Optional[SessionEntry]:
        """The current tip of the active branch."""
        if self.current_leaf_id:
            return self._entries.get(self.current_leaf_id)
        return None
    
    def get_leaf_id(self) -> Optional[str]:
        """Just the ID of the current leaf."""
        return self.current_leaf_id
    
    def get_entry(self, entry_id: str) -> Optional[SessionEntry]:
        """Look up any entry by ID."""
        return self._entries.get(entry_id)
    
    def get_children(self, entry_id: str) -> list[SessionEntry]:
        """Direct children of a given entry. Used for tree visualization."""
        return [e for e in self._entries.values() if e.parent_id == entry_id]
    
    # --- Write operations ---
    
    def append(self, role: str, content: str, **kwargs) -> str:
        """Create and append a message entry. Returns the new entry's ID.
        Sets parent_id to current leaf automatically."""
        entry = MessageEntry(
            parent_id=self.current_leaf_id,
            role=role,
            content=content,
            **kwargs
        )
        self._entries[entry.id] = entry
        self._order.append(entry.id)
        self.current_leaf_id = entry.id
        if self.path:
            self._append_to_file(entry)
        return entry.id
    
    def append_entry(self, entry: SessionEntry) -> str:
        """Append a raw entry (compaction, etc.). Sets parent_id to current leaf if not set."""
        if entry.parent_id is None:
            entry.parent_id = self.current_leaf_id
        self._entries[entry.id] = entry
        self._order.append(entry.id)
        self.current_leaf_id = entry.id
        if self.path:
            self._append_to_file(entry)
        return entry.id
    
    def branch(self, entry_id: str) -> None:
        """Move the leaf pointer to an earlier entry. Next append creates a fork."""
        if entry_id not in self._entries:
            raise KeyError(f"Entry {entry_id} not found")
        self.current_leaf_id = entry_id
    
    # --- Context for LLM ---
    
    def build_context(self, leaf_id: str = None) -> list[dict]:
        """Build the message list to send to the LLM.
        Handles compaction: if a compaction entry exists in the path,
        uses its summary + only messages after first_kept_entry_id.
        Returns list of {"role": str, "content": str} dicts."""
        path = self.get_path(leaf_id)
        
        # Find the most recent compaction entry in the path
        compaction = None
        for entry in reversed(path):
            if isinstance(entry, CompactionEntry):
                compaction = entry
                break
        
        if compaction:
            # Include compaction summary as a system message,
            # then only messages after the kept boundary
            messages = [{"role": "system", "content": f"Previous conversation summary: {compaction.summary}"}]
            past_boundary = False
            for entry in path:
                if entry.id == compaction.first_kept_entry_id:
                    past_boundary = True
                if past_boundary and isinstance(entry, MessageEntry):
                    messages.append({"role": entry.role, "content": entry.content})
            return messages
        else:
            # No compaction, return all messages on the path
            return [
                {"role": e.role, "content": e.content}
                for e in path
                if isinstance(e, MessageEntry)
            ]
    
    # --- Persistence ---
    
    def _load(self) -> None:
        """Read JSONL file into memory. Skip malformed lines (crash recovery)."""
        with open(self.path, 'r') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue  # skip corrupted lines
                
                if i == 0 and data.get("type") == "session":
                    self.header = SessionHeader(**{k: v for k, v in data.items() 
                                                    if k in SessionHeader.__dataclass_fields__})
                    continue
                
                entry_type = data.get("type")
                if entry_type == "message":
                    entry = MessageEntry(**{k: v for k, v in data.items() 
                                            if k in MessageEntry.__dataclass_fields__})
                elif entry_type == "compaction":
                    entry = CompactionEntry(**{k: v for k, v in data.items() 
                                                if k in CompactionEntry.__dataclass_fields__})
                else:
                    continue  # skip unknown entry types for now
                
                self._entries[entry.id] = entry
                self._order.append(entry.id)
                self.current_leaf_id = entry.id  # last entry becomes the leaf
        
        # After loading, find the actual leaf (last entry on the longest branch)
        # The simple approach: last entry in the file IS the leaf.
        # This works because pi-mono appends new entries at the end.
    
    def _append_to_file(self, entry: SessionEntry) -> None:
        """Append one JSON line to the JSONL file."""
        with open(self.path, 'a') as f:
            f.write(json.dumps(asdict(entry)) + '\n')
    
    # --- Factory methods ---
    
    @staticmethod
    def create(cwd: str, path: str = None) -> 'SessionManager':
        """Create a new session with a fresh JSONL file."""
        if path is None:
            session_id = uuid4().hex
            path = os.path.join(cwd, f"{session_id}.jsonl")
        sm = SessionManager(path)
        sm.header = SessionHeader(cwd=cwd)
        # Write header as first line
        with open(path, 'w') as f:
            f.write(json.dumps(asdict(sm.header)) + '\n')
        return sm
    
    @staticmethod
    def open(path: str) -> 'SessionManager':
        """Open an existing session file."""
        sm = SessionManager(path)
        return sm
    
    @staticmethod
    def in_memory() -> 'SessionManager':
        """Create an in-memory session (no file persistence). Good for testing."""
        return SessionManager(path=None)
```

### Key implementation notes

1. **Append-only file.** Never rewrite the whole file. Just append new JSON lines. This makes it crash-safe (a partial write only corrupts the last line, which you can detect and skip on reload).

2. **In-memory index.** On load, read every line into `_entries` dict (id -> entry) and `_order` list (insertion order). `get_entry()` is O(1). `get_children()` scans the dict (O(n) but fine for <10k entries; optimize later if needed).

3. **ID generation.** Use `uuid4().hex` for entry IDs. 32-char hex string. No dashes.

4. **get_path() is the hot path.** Called before every LLM request. With the in-memory dict, it's a linked-list walk: O(depth of branch). For typical conversations (<1000 messages) this is instant.

5. **build_context() is separate from get_path().** `get_path()` returns raw entries (all types). `build_context()` returns only what the LLM should see (messages, with compaction applied). Do not merge these into one method.

6. **append() auto-sets parent_id.** The caller doesn't need to manage the tree structure manually. Just call `append("user", "Hello")` and the entry gets linked to the current leaf.

7. **File locking.** If multiple async tasks might write simultaneously, use `fcntl.flock()` on the file. For Phase 1, the Queen is single-threaded, so this can wait.

8. **Line-by-line read.** On load, read with `open(path).readlines()`, parse each with `json.loads()`. Skip lines that fail to parse (crash recovery). Don't load the whole file into memory as one string.

9. **Current leaf on load.** After loading, `current_leaf_id` is set to the last entry in the file. This works because new entries are always appended at the end. If the user had previously branched to an earlier node, the branch operation itself doesn't write anything to the file. The leaf is determined by what was last appended.

10. **Testing.** Use `SessionManager.in_memory()` for pytest tests. No file I/O, no cleanup needed, same API.

---

## What NOT to port (yet)

- Labels (bookmarks): nice to have, not needed for the core
- branch_summary entries: only needed when tree navigation UI exists
- custom and custom_message entries: these are pi-mono's extension state system
- createBranchedSession (fork to new file): defer until session management UI exists
- Auto-compaction triggers: build the compaction method, trigger manually
- Extension hooks (session_before_compact, session_tree, etc.): pi-mono's plugin system, irrelevant
- Multimodal content arrays: use plain strings for Phase 1

---

## How this connects to nanobot

Nanobot currently uses MEMORY.md (long-term facts) and HISTORY.md (flat conversation log). The port replaces HISTORY.md with the JSONL DAG. MEMORY.md stays as-is for now (it serves a different purpose: persistent facts vs conversation history).

The integration point is wherever nanobot builds the LLM context. Currently it reads HISTORY.md and formats it as a message list. After the port, it calls `session_manager.build_context()` instead. Same output shape (a list of `{"role": ..., "content": ...}` dicts), different source.

Nanobot's context builder probably also injects the system prompt and tool descriptions. Those stay unchanged. The SessionManager only replaces the conversation history part of the context.
