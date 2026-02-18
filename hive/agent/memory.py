"""Memory system for persistent agent memory."""

import shutil
from pathlib import Path

from hive.utils.helpers import ensure_dir


# Subdirectories that must exist in every memory/ hierarchy.
# Relative to the memory/ root.
MEMORY_DIRS = [
    "identity",
    "systems",
    "projects/_template",
    "procedural/workflows",
    "procedural/fixes",
    "lessons",
    "skills/_system",
    "skills/_user",
]


def initialize_memory_hierarchy(workspace: Path, templates_dir: Path | None = None) -> None:
    """Initialize the memory/ directory structure from templates.

    Called on AgentLoop startup when memory/identity/ doesn't exist yet.
    Idempotent: skips files that already exist, never overwrites existing content.

    Args:
        workspace: The user's workspace directory (e.g. ~/.hive/workspace).
        templates_dir: Path to the templates/memory/ directory in the repo.
                       If None, only creates empty directories (no template files).
    """
    memory_dir = workspace / "memory"

    # Create all required subdirectories
    for subdir in MEMORY_DIRS:
        ensure_dir(memory_dir / subdir)

    if templates_dir is None or not templates_dir.exists():
        return

    # Copy template files; skip files that already exist (idempotent)
    for src in templates_dir.rglob("*"):
        if src.is_file():
            relative = src.relative_to(templates_dir)
            dest = memory_dir / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(src, dest)


class MemoryStore:
    """Long-term memory: MEMORY.md (legacy flat file) and the memory/ hierarchy.

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
