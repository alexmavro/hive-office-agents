"""Memory system for persistent agent memory."""

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from hive.utils.helpers import ensure_dir


# ---------------------------------------------------------------------------
# MemoryEntry — structured metadata for every memory write
# ---------------------------------------------------------------------------

@dataclass
class MemoryEntry:
    """A single fact stored in the memory hierarchy.

    Uses YAML frontmatter blocks embedded in Markdown files so that files
    remain human-readable while still carrying machine-readable metadata.

    Confidence levels:
        HIGH   — verified fact (user stated, or Queen ran a command and saw output)
        MEDIUM — inferred from context (probably true, not confirmed)
        LOW    — speculation (might be true, needs verification before acting)
    """

    content: str
    confidence: str              # "HIGH" | "MEDIUM" | "LOW"
    source: str                  # e.g. "user_stated", "verified_command", "inferred_from_logs"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_verified: Optional[str] = None
    needs_reverification: bool = False


_YAML_BLOCK_RE = re.compile(r"^---\n(.*?)\n---$", re.DOTALL | re.MULTILINE)


def write_memory_entry(filepath: Path, entry: MemoryEntry) -> None:
    """Append a MemoryEntry as a YAML frontmatter block to a Markdown file.

    The format is compatible with standard YAML frontmatter parsers.
    Multiple entries in one file are separated by blank lines.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

    block_lines = [
        "---",
        f"content: {_yaml_str(entry.content)}",
        f"confidence: {entry.confidence}",
        f"source: {entry.source}",
        f"timestamp: {entry.timestamp}",
        f"last_verified: {entry.last_verified or 'null'}",
        f"needs_reverification: {'true' if entry.needs_reverification else 'false'}",
        "---",
    ]
    block = "\n".join(block_lines) + "\n"

    # Append with blank line separator if file already has content
    if filepath.exists() and filepath.stat().st_size > 0:
        with filepath.open("a", encoding="utf-8") as f:
            f.write("\n" + block)
    else:
        filepath.write_text(block, encoding="utf-8")


def read_memory_entries(filepath: Path) -> list[MemoryEntry]:
    """Parse all YAML frontmatter blocks from a Markdown file.

    Returns an empty list if the file doesn't exist or has no valid blocks.
    Non-YAML content between blocks (plain Markdown prose) is ignored.
    """
    if not filepath.exists():
        return []

    text = filepath.read_text(encoding="utf-8")
    entries: list[MemoryEntry] = []

    for match in _YAML_BLOCK_RE.finditer(text):
        body = match.group(1)
        parsed = _parse_simple_yaml(body)
        try:
            entries.append(MemoryEntry(
                content=parsed.get("content", ""),
                confidence=parsed.get("confidence", "LOW"),
                source=parsed.get("source", "unknown"),
                timestamp=parsed.get("timestamp", ""),
                last_verified=parsed.get("last_verified") if parsed.get("last_verified") != "null" else None,
                needs_reverification=parsed.get("needs_reverification", "false").lower() == "true",
            ))
        except Exception:
            continue  # Skip malformed blocks

    return entries


def decay_confidence(entry: MemoryEntry, now: Optional[datetime] = None) -> MemoryEntry:
    """Return a copy of entry with confidence reduced based on age.

    Decay schedule:
        HIGH   → MEDIUM after 30 days without reverification
        MEDIUM → LOW    after 90 days without reverification
        LOW             → needs_reverification = True after 7 days
    """
    if not entry.timestamp:
        return entry

    if now is None:
        now = datetime.now(timezone.utc)

    try:
        entry_time = datetime.fromisoformat(entry.timestamp)
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=timezone.utc)
    except ValueError:
        return entry

    age = now - entry_time
    confidence = entry.confidence
    needs_reverification = entry.needs_reverification

    if confidence == "HIGH" and age > timedelta(days=30):
        confidence = "MEDIUM"
    elif confidence == "MEDIUM" and age > timedelta(days=90):
        confidence = "LOW"
    elif confidence == "LOW" and age > timedelta(days=7):
        needs_reverification = True

    # Return new instance only if something changed
    if confidence != entry.confidence or needs_reverification != entry.needs_reverification:
        from dataclasses import replace
        return replace(entry, confidence=confidence, needs_reverification=needs_reverification)
    return entry


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _yaml_str(value: str) -> str:
    """Quote a YAML string value if it contains special characters."""
    if any(c in value for c in (':', '#', '"', "'", '\n', '{', '}')):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _parse_simple_yaml(body: str) -> dict[str, str]:
    """Parse a minimal YAML block (key: value pairs only)."""
    result: dict[str, str] = {}
    for line in body.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # Strip surrounding quotes
            if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                val = val[1:-1].replace('\\"', '"')
            result[key] = val
    return result


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

    def __init__(self, workspace: Path, memory_dir: Path | None = None):
        if memory_dir:
            self.memory_dir = ensure_dir(memory_dir)
        else:
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
