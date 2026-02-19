"""Session management for conversation history.

Sessions are backed by DagSession (JSONL DAG, append-only).
Each session maps to a .jsonl file in ~/.hive/sessions/.
The Session class presents a stable interface to the agent loop.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from hive.session.dag import DagSession
from hive.utils.helpers import ensure_dir, safe_filename


@dataclass
class Session:
    """A conversation session backed by a DagSession.

    The _dag field holds all message history as a JSONL tree.
    Messages are written to disk on every add_message() call (append-only).
    last_consolidated tracks how many path entries have been compacted.
    """

    key: str  # channel:chat_id
    _dag: DagSession = field(default_factory=DagSession.in_memory, repr=False)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_consolidated: int = 0  # number of path entries already compacted

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Append a message to the session DAG."""
        self._dag.append(role, content, tools_used=kwargs.get("tools_used"))
        self.updated_at = datetime.now()

    def get_history(self, max_messages: int = 500) -> list[dict[str, Any]]:
        """Return recent messages in LLM format (role + content only)."""
        return self._dag.build_context()[-max_messages:]

    @property
    def message_count(self) -> int:
        """Number of MessageEntry nodes on the current active branch."""
        return self._dag.message_count

    def clear(self) -> None:
        """Reset session to empty state (creates a fresh in-memory DagSession)."""
        self._dag = DagSession.in_memory()
        self.last_consolidated = 0
        self.updated_at = datetime.now()


class SessionManager:
    """Manages conversation sessions stored as JSONL DAG files.

    Session files live in ~/.hive/sessions/{safe_key}.jsonl.
    The DagSession handles all message persistence directly via append-only writes.
    SessionManager handles session lifecycle (create, load, cache, invalidate).
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sessions_dir = ensure_dir(Path.home() / ".hive" / "sessions")
        self._cache: dict[str, Session] = {}

    def _get_session_path(self, key: str) -> Path:
        safe_key = safe_filename(key.replace(":", "_"))
        return self.sessions_dir / f"{safe_key}.jsonl"

    def get_or_create(self, key: str) -> Session:
        """Return cached session, or load from disk, or create a new one."""
        if key in self._cache:
            return self._cache[key]

        session = self._load(key)
        if session is None:
            path = self._get_session_path(key)
            dag = DagSession.create(cwd=str(self.sessions_dir), path=str(path))
            session = Session(key=key, _dag=dag)

        self._cache[key] = session
        return session

    def _load(self, key: str) -> Optional[Session]:
        """Load a session from its .jsonl file, if it exists."""
        path = self._get_session_path(key)
        if not path.exists():
            return None
        try:
            dag = DagSession.open(str(path))
            # Recover created_at from DAG header timestamp
            try:
                created_at = datetime.fromisoformat(dag.header.timestamp)
            except (ValueError, AttributeError):
                created_at = datetime.now()
            return Session(
                key=key,
                _dag=dag,
                created_at=created_at,
            )
        except Exception as e:
            logger.warning(f"Failed to load session {key}: {e}")
            return None

    def save(self, session: Session) -> None:
        """Flush any in-memory DAG to disk.

        DagSession writes each message immediately on append(), so this is
        a no-op for message data. Kept for interface compatibility and for
        any future metadata-only writes.
        """
        self._cache[session.key] = session

    def invalidate(self, key: str) -> None:
        """Remove a session from the in-memory cache."""
        self._cache.pop(key, None)

    def delete(self, key: str) -> bool:
        """Delete a session: remove its file and evict from cache.

        Returns True if the file existed and was removed, False otherwise.
        """
        self._cache.pop(key, None)
        path = self._get_session_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all session files with basic metadata."""
        sessions = []
        for path in self.sessions_dir.glob("*.jsonl"):
            try:
                dag = DagSession.open(str(path))
                sessions.append({
                    "key": path.stem.replace("_", ":", 1),
                    "created_at": dag.header.timestamp,
                    "message_count": dag.message_count,
                    "path": str(path),
                })
            except Exception:
                continue
        return sorted(sessions, key=lambda x: x.get("created_at", ""), reverse=True)
