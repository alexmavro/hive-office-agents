"""Memory system for persistent agent memory."""

from pathlib import Path

from hive.utils.helpers import ensure_dir


class MemoryStore:
    """Long-term memory: MEMORY.md (persistent facts about the user and project).

    Conversation history is stored as CompactionEntry nodes in the DAG session
    (see hive/session/dag.py). HISTORY.md is no longer used.
    """

    def __init__(self, workspace: Path):
        self.memory_dir = ensure_dir(workspace / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"

    def read_long_term(self) -> str:
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:
        self.memory_file.write_text(content, encoding="utf-8")

    def get_memory_context(self) -> str:
        long_term = self.read_long_term()
        return f"## Long-term Memory\n{long_term}" if long_term else ""
