"""Signal detection and memory consolidation routing.

When the Queen calls report_task(), the event flows here:
  1. detect_signal() maps the status to a signal type
  2. consolidate() routes the signal to the appropriate memory writer

Each writer uses the LLM to extract a structured lesson/workflow from
the current session context, then writes to the memory/ hierarchy with
confidence metadata.

Memory writes (by signal type):
    task_success   → procedural/workflows/{task_type}.md
    task_failure   → lessons/failures.md
    correction     → relevant identity/ or systems/ file (LLM decides)
    decision       → projects/{active}/decisions.md
    pattern        → lessons/patterns.md
    new_skill      → skills/skills_registry.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from hive.agent.memory import MemoryEntry, write_memory_entry

if TYPE_CHECKING:
    from hive.providers.base import LLMProvider
    from hive.session.manager import Session


# ---------------------------------------------------------------------------
# Signal detection
# ---------------------------------------------------------------------------

_STATUS_TO_SIGNAL = {
    "success": "task_success",
    "failure": "task_failure",
    "correction": "correction",
    "decision": "decision",
    "pattern": "pattern",
    "skill_created": "new_skill",
}


def detect_signal(event: dict) -> str | None:
    """Map an event dict to a signal type, or return None for unknown events."""
    return _STATUS_TO_SIGNAL.get(event.get("status", ""))


# ---------------------------------------------------------------------------
# Top-level consolidate dispatcher
# ---------------------------------------------------------------------------

async def consolidate(
    signal_type: str,
    event: dict,
    memory_dir: Path,
    provider: "LLMProvider",
    model: str,
    session: "Session",
) -> None:
    """Route a signal to the appropriate memory writer.

    All writers are async and fire-and-forget (called from an asyncio.Task).
    Errors are logged but never propagated — consolidation failure must not
    break the main conversation loop.
    """
    try:
        if signal_type == "task_success":
            await _write_workflow(event, memory_dir, provider, model, session)
        elif signal_type == "task_failure":
            await _write_failure(event, memory_dir, provider, model, session)
        elif signal_type == "correction":
            await _write_correction(event, memory_dir, provider, model, session)
        elif signal_type == "decision":
            _write_decision(event, memory_dir)
        elif signal_type == "pattern":
            await _write_pattern(event, memory_dir, provider, model, session)
        elif signal_type == "new_skill":
            _register_skill(event, memory_dir)
        else:
            logger.warning(f"consolidate: unknown signal_type={signal_type!r}")
    except Exception as exc:
        logger.error(f"consolidate({signal_type}) failed: {exc}")


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

async def _write_workflow(
    event: dict,
    memory_dir: Path,
    provider: "LLMProvider",
    model: str,
    session: "Session",
) -> None:
    """Extract the working method from a successful task and save as a workflow."""
    task_type = _safe_filename(event.get("task_type", "general"))
    summary = event.get("summary", "")
    context = _recent_session_text(session)

    prompt = f"""A task completed successfully. Extract a reusable workflow from this.

Task type: {task_type}
Summary: {summary}

Recent session context:
{context}

Write a workflow document in this exact Markdown format:

# {task_type.replace("_", " ").title()} Workflow

## When to use
[One sentence: what situation triggers this workflow]

## Prerequisites
[What must be true before starting]

## Steps
1. [Step 1]
2. [Step 2]

## Verification
[How to confirm the task succeeded]

## Gotchas
[Known issues to watch for]

Be specific. Use exact commands where applicable. Keep it practical."""

    content = await _llm_extract(provider, model, prompt)
    if not content:
        return

    filepath = memory_dir / "procedural" / "workflows" / f"{task_type}.md"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    entry = MemoryEntry(
        content=content,
        confidence="HIGH",
        source="task_success",
    )
    # Write the workflow as a MemoryEntry block, then append the full content
    write_memory_entry(filepath, entry)
    with filepath.open("a", encoding="utf-8") as f:
        f.write(f"\n{content}\n")

    logger.info(f"Workflow written: {filepath}")


async def _write_failure(
    event: dict,
    memory_dir: Path,
    provider: "LLMProvider",
    model: str,
    session: "Session",
) -> None:
    """Extract a failure lesson and append to lessons/failures.md."""
    summary = event.get("summary", "")
    attempts = event.get("attempts", 1)
    task_type = event.get("task_type", "general")
    context = _recent_session_text(session)

    prompt = f"""A task failed after {attempts} attempt(s). Extract a clear failure lesson.

Task type: {task_type}
Summary: {summary}

Recent session context:
{context}

Write the lesson in this format:

## {datetime.now(timezone.utc).strftime("%Y-%m-%d")} — {task_type} failure

**What was attempted:** [description]
**Why it failed:** [root cause]
**Attempts:** {attempts}
**What to do instead:** [alternative approach]

Be direct. Include exact error patterns if visible."""

    content = await _llm_extract(provider, model, prompt)
    if not content:
        return

    filepath = memory_dir / "lessons" / "failures.md"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    entry = MemoryEntry(
        content=content,
        confidence="HIGH",
        source="task_failure",
    )
    write_memory_entry(filepath, entry)

    logger.info(f"Failure lesson appended to {filepath}")


async def _write_correction(
    event: dict,
    memory_dir: Path,
    provider: "LLMProvider",
    model: str,
    session: "Session",
) -> None:
    """Apply a user correction to the appropriate memory file."""
    summary = event.get("summary", "")
    what_changed = event.get("what_changed", "")

    # For now, write corrections to a general corrections log.
    # A more sophisticated version would use the LLM to route to
    # the specific identity/systems/procedural file that needs updating.
    filepath = memory_dir / "lessons" / "corrections.md"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    entry = MemoryEntry(
        content=summary,
        confidence="HIGH",
        source="user_correction",
    )
    write_memory_entry(filepath, entry)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prose = f"\n## {date_str} — Correction\n\n"
    if what_changed:
        prose += f"**Change:** {what_changed}\n\n"
    prose += f"**Summary:** {summary}\n"
    with filepath.open("a", encoding="utf-8") as f:
        f.write(prose)

    logger.info(f"Correction logged to {filepath}")


def _write_decision(event: dict, memory_dir: Path) -> None:
    """Append a decision to the active project's decisions.md."""
    summary = event.get("summary", "")
    task_type = event.get("task_type", "")

    # Find active project
    marker = memory_dir / ".active_project"
    if marker.exists():
        active = marker.read_text(encoding="utf-8").strip()
        filepath = memory_dir / "projects" / active / "decisions.md"
    else:
        # Fall back to a general decisions log
        filepath = memory_dir / "lessons" / "decisions.md"

    filepath.parent.mkdir(parents=True, exist_ok=True)

    # MemoryEntry stores the single-line summary for searchability.
    # The formatted prose is appended separately after the YAML block.
    entry = MemoryEntry(
        content=summary,
        confidence="HIGH",
        source="decision_logged",
    )
    write_memory_entry(filepath, entry)

    # Append human-readable prose header
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prose = f"\n## {date_str} — {task_type or 'Decision'}\n\n{summary}\n"
    with filepath.open("a", encoding="utf-8") as f:
        f.write(prose)

    logger.info(f"Decision logged to {filepath}")


async def _write_pattern(
    event: dict,
    memory_dir: Path,
    provider: "LLMProvider",
    model: str,
    session: "Session",
) -> None:
    """Extract a recognized pattern and append to lessons/patterns.md."""
    summary = event.get("summary", "")

    filepath = memory_dir / "lessons" / "patterns.md"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    entry = MemoryEntry(
        content=summary,
        confidence="MEDIUM",
        source="pattern_recognized",
    )
    write_memory_entry(filepath, entry)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prose = f"\n## {date_str} — Pattern\n\n{summary}\n"
    with filepath.open("a", encoding="utf-8") as f:
        f.write(prose)

    logger.info(f"Pattern logged to {filepath}")


def _register_skill(event: dict, memory_dir: Path) -> None:
    """Add a new skill to the skills registry."""
    import json as _json

    registry_path = memory_dir / "skills" / "skills_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    if registry_path.exists():
        try:
            registry = _json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            registry = {"version": "1.0", "skills": []}
    else:
        registry = {"version": "1.0", "skills": []}

    task_type = event.get("task_type", "unknown")
    summary = event.get("summary", "")
    now = datetime.now(timezone.utc).isoformat()

    # Check if already registered
    existing_names = {s.get("name") for s in registry.get("skills", [])}
    if task_type not in existing_names:
        registry.setdefault("skills", []).append({
            "name": task_type,
            "description": summary,
            "confidence": "LOW",
            "created_at": now,
            "last_used": now,
            "use_count": 1,
        })
        registry_path.write_text(
            _json.dumps(registry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"Skill registered: {task_type}")
    else:
        logger.debug(f"Skill already registered: {task_type}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recent_session_text(session: "Session", max_entries: int = 20) -> str:
    """Format recent session messages as readable text for LLM prompts."""
    from hive.session.dag import MessageEntry
    try:
        path = session._dag.get_path()
        recent = [e for e in path if isinstance(e, MessageEntry)][-max_entries:]
        lines = []
        for e in recent:
            if e.content:
                lines.append(f"{e.role.upper()}: {e.content[:500]}")
        return "\n".join(lines)
    except Exception:
        return "(session context unavailable)"


async def _llm_extract(provider: "LLMProvider", model: str, prompt: str) -> str | None:
    """Call the LLM to extract structured content from a prompt."""
    try:
        response = await provider.chat(
            messages=[
                {"role": "system", "content": "You extract structured knowledge from conversation context. Be specific and practical."},
                {"role": "user", "content": prompt},
            ],
            model=model,
            max_tokens=1024,
        )
        return (response.content or "").strip() or None
    except Exception as exc:
        logger.error(f"_llm_extract failed: {exc}")
        return None


def _safe_filename(name: str) -> str:
    """Convert a task type string to a safe filename stem."""
    import re
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s-]+", "_", name)
    return name or "general"
