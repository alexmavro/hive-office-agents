"""JSONL DAG session storage.

Each conversation is stored as a single append-only .jsonl file.
Every message is a node with a parent_id, forming a branch tree.
Context reconstruction walks from the current leaf back to the root.
Compaction entries embed summaries directly in the DAG (replaces HISTORY.md).

Design notes (vs pi-mono original):
- Flat fields on MessageEntry (not nested under "message" sub-object)
- Plain string content (not content array) for Phase 1
- snake_case field names
- uuid4().hex for IDs (not Snowflake)
- tools_used stored as optional metadata on MessageEntry
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Union
from uuid import uuid4


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid4().hex


@dataclass
class SessionHeader:
    type: str = "session"
    id: str = field(default_factory=_new_id)
    cwd: str = ""
    timestamp: str = field(default_factory=_now_iso)
    parent_session: Optional[str] = None


@dataclass
class MessageEntry:
    type: str = "message"
    id: str = field(default_factory=_new_id)
    parent_id: Optional[str] = None
    role: str = ""          # "user" | "assistant" | "system" | "tool_result"
    content: str = ""
    timestamp: str = field(default_factory=_now_iso)
    tools_used: Optional[list] = None   # metadata only, not sent to LLM


@dataclass
class CompactionEntry:
    type: str = "compaction"
    id: str = field(default_factory=_new_id)
    parent_id: Optional[str] = None
    summary: str = ""
    first_kept_entry_id: str = ""
    tokens_before: int = 0


SessionEntry = Union[MessageEntry, CompactionEntry]


# ---------------------------------------------------------------------------
# DagSession
# ---------------------------------------------------------------------------


class DagSession:
    """Single-session JSONL DAG manager.

    In-memory index: dict[id -> entry] for O(1) lookup.
    Insertion order: _order list for sequential access.
    Active branch: tracked via current_leaf_id.
    Persistence: append-only writes on each .append() / .compact().
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.header: SessionHeader = SessionHeader()
        self._entries: dict[str, SessionEntry] = {}
        self._order: list[str] = []
        self.current_leaf_id: Optional[str] = None

        if path and os.path.exists(path):
            self._load()

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @staticmethod
    def create(cwd: str, path: str) -> "DagSession":
        """Create a new session, writing the header line."""
        dag = DagSession.__new__(DagSession)
        dag.path = path
        dag.header = SessionHeader(cwd=cwd)
        dag._entries = {}
        dag._order = []
        dag.current_leaf_id = None
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(asdict(dag.header)) + "\n")
        return dag

    @staticmethod
    def open(path: str) -> "DagSession":
        """Open an existing session file."""
        return DagSession(path)

    @staticmethod
    def in_memory() -> "DagSession":
        """Create an in-memory session (no file I/O). Useful for testing."""
        return DagSession(path=None)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_entries(self) -> list:
        """All entries in insertion order (excluding header)."""
        return [self._entries[eid] for eid in self._order]

    def get_path(self, leaf_id: Optional[str] = None) -> list:
        """Walk from root to the given leaf (or current_leaf_id).

        Returns entries in root-first order. Only entries on the active
        branch are included — sibling branches are invisible.
        """
        target = leaf_id or self.current_leaf_id
        if target is None:
            return []
        path: list[SessionEntry] = []
        current_id: Optional[str] = target
        while current_id is not None:
            entry = self._entries.get(current_id)
            if entry is None:
                break
            path.append(entry)
            current_id = entry.parent_id
        path.reverse()
        return path

    def build_context(self, leaf_id: Optional[str] = None) -> list[dict]:
        """Build the LLM message list for the current branch.

        If a CompactionEntry exists on the path, uses its summary as a
        system message and includes only messages after first_kept_entry_id.
        Returns list of {"role": str, "content": str} dicts.
        """
        path = self.get_path(leaf_id)

        # Find the most recent compaction entry on this branch
        compaction: Optional[CompactionEntry] = None
        for entry in reversed(path):
            if isinstance(entry, CompactionEntry):
                compaction = entry
                break

        if compaction:
            messages = [{"role": "system", "content": f"[Earlier conversation summary]: {compaction.summary}"}]
            if not compaction.first_kept_entry_id:
                # archive_all compaction: nothing kept from before.
                # Include all MessageEntry nodes that appear AFTER this compaction in the path.
                past_compaction = False
                for entry in path:
                    if entry.id == compaction.id:
                        past_compaction = True
                        continue
                    if past_compaction and isinstance(entry, MessageEntry):
                        messages.append({"role": entry.role, "content": entry.content})
            else:
                past_boundary = False
                for entry in path:
                    if entry.id == compaction.first_kept_entry_id:
                        past_boundary = True
                    if past_boundary and isinstance(entry, MessageEntry):
                        messages.append({"role": entry.role, "content": entry.content})
            return messages
        else:
            return [
                {"role": e.role, "content": e.content}
                for e in path
                if isinstance(e, MessageEntry)
            ]

    def get_leaf_id(self) -> Optional[str]:
        return self.current_leaf_id

    def get_leaf_entry(self) -> Optional[SessionEntry]:
        if self.current_leaf_id:
            return self._entries.get(self.current_leaf_id)
        return None

    def get_entry(self, entry_id: str) -> Optional[SessionEntry]:
        return self._entries.get(entry_id)

    def get_children(self, entry_id: str) -> list:
        return [e for e in self._entries.values() if e.parent_id == entry_id]

    @property
    def message_count(self) -> int:
        """Number of MessageEntry nodes on the current active branch."""
        return sum(1 for e in self.get_path() if isinstance(e, MessageEntry))

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def append(self, role: str, content: str, tools_used: Optional[list] = None) -> str:
        """Append a message entry. parent_id is set to current_leaf_id automatically.

        Returns the new entry's ID.
        """
        entry = MessageEntry(
            parent_id=self.current_leaf_id,
            role=role,
            content=content,
            tools_used=tools_used,
        )
        self._register(entry)
        return entry.id

    def compact(
        self,
        summary: str,
        first_kept_entry_id: str,
        tokens_before: int = 0,
    ) -> str:
        """Append a compaction entry. parent_id is set to current_leaf_id.

        Returns the new entry's ID.
        """
        entry = CompactionEntry(
            parent_id=self.current_leaf_id,
            summary=summary,
            first_kept_entry_id=first_kept_entry_id,
            tokens_before=tokens_before,
        )
        self._register(entry)
        return entry.id

    def branch(self, entry_id: str) -> None:
        """Move the leaf pointer to an earlier entry.

        The next append() will fork from that point.
        Raises KeyError if entry_id is not in this session.
        """
        if entry_id not in self._entries:
            raise KeyError(f"Entry {entry_id!r} not found in session")
        self.current_leaf_id = entry_id

    # ------------------------------------------------------------------
    # Persistence (private)
    # ------------------------------------------------------------------

    def _register(self, entry: SessionEntry) -> None:
        """Add entry to in-memory index and write to file."""
        self._entries[entry.id] = entry
        self._order.append(entry.id)
        self.current_leaf_id = entry.id
        if self.path:
            self._write_line(entry)

    def _write_line(self, entry: SessionEntry) -> None:
        """Append one JSON line to the .jsonl file."""
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def _load(self) -> None:
        """Read .jsonl file into memory. Skips malformed lines (crash recovery)."""
        with open(self.path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue  # skip corrupted lines

                entry_type = data.get("type")

                if i == 0 and entry_type == "session":
                    # Header line
                    self.header = SessionHeader(
                        id=data.get("id", _new_id()),
                        cwd=data.get("cwd", ""),
                        timestamp=data.get("timestamp", _now_iso()),
                        parent_session=data.get("parent_session"),
                    )
                    continue

                if entry_type == "message":
                    entry = MessageEntry(
                        id=data.get("id", _new_id()),
                        parent_id=data.get("parent_id"),
                        role=data.get("role", ""),
                        content=data.get("content", ""),
                        timestamp=data.get("timestamp", _now_iso()),
                        tools_used=data.get("tools_used"),
                    )
                elif entry_type == "compaction":
                    entry = CompactionEntry(
                        id=data.get("id", _new_id()),
                        parent_id=data.get("parent_id"),
                        summary=data.get("summary", ""),
                        first_kept_entry_id=data.get("first_kept_entry_id", ""),
                        tokens_before=data.get("tokens_before", 0),
                    )
                else:
                    continue  # unknown type — skip, forward-compat

                self._entries[entry.id] = entry
                self._order.append(entry.id)
                self.current_leaf_id = entry.id  # last entry in file is the leaf
