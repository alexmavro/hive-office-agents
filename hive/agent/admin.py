"""Factory reset — wipe all user data, preserve core, reinitialize.

Flow:
  1. User sends /factory-reset
  2. Queen returns warning + asks for confirmation string
  3. User sends "CONFIRM FACTORY RESET"
  4. Queen creates backup zip, wipes memory/ + sessions/, reinitialises from templates

Core files (not touched):
  - All Python source code
  - SOUL.md, AGENTS.md, TOOLS.md, IDENTITY.md
  - templates/memory/ (the source templates)
  - skills/_system/ (system-installed skills)

User data (wiped):
  - memory/ (identity, projects, workflows, lessons, skills/_user)
  - sessions/ (DAG conversation history)
"""

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from loguru import logger

from hive.agent.memory import initialize_memory_hierarchy


CONFIRM_PHRASE = "CONFIRM FACTORY RESET"


async def factory_reset(
    workspace: Path,
    templates_dir: Path | None,
    sessions_dir: Path,
    confirm: bool = False,
) -> str:
    """Reset Queen to a clean state.

    Args:
        workspace:     The user's workspace directory (e.g. ~/.hive/workspace).
        templates_dir: Path to templates/memory/ in the repo.
        sessions_dir:  Path to the sessions directory (e.g. ~/.hive/sessions).
        confirm:       If False, returns the warning/confirmation prompt.
                       If True, performs the actual reset.

    Returns:
        A message to send back to the user.
    """
    if not confirm:
        return (
            "⚠️ **Factory Reset Warning**\n\n"
            "This will permanently delete:\n"
            "- All conversation history\n"
            "- All learned workflows and lessons\n"
            "- All project memory\n"
            "- All custom skills\n"
            "- Your identity and preferences\n\n"
            "Core system code, templates, and system skills will be preserved.\n"
            "A backup ZIP will be created before deletion.\n\n"
            f"To confirm, send exactly:\n`{CONFIRM_PHRASE}`"
        )

    memory_dir = workspace / "memory"

    # 1. Create backup before deleting anything
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exports_dir = workspace.parent / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    backup_path = exports_dir / f"backup_{timestamp}.zip"

    _create_backup(backup_path, memory_dir, sessions_dir)
    logger.info(f"Factory reset backup created: {backup_path}")

    # 2. Wipe user data
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
        logger.info(f"Removed memory dir: {memory_dir}")

    if sessions_dir.exists():
        shutil.rmtree(sessions_dir)
        logger.info(f"Removed sessions dir: {sessions_dir}")

    # 3. Reinitialise from templates
    initialize_memory_hierarchy(workspace, templates_dir)
    logger.info("Memory hierarchy reinitialised from templates")

    return (
        f"Reset complete.\n\n"
        f"Backup saved to: `{backup_path}`\n\n"
        "All conversation history and learned memory has been cleared. "
        "Run /onboard to set up your profile."
    )


def _create_backup(backup_path: Path, memory_dir: Path, sessions_dir: Path) -> None:
    """Create a zip archive of memory/ and sessions/."""
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src_dir in (memory_dir, sessions_dir):
            if not src_dir.exists():
                continue
            for file in src_dir.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(src_dir.parent)
                    zf.write(file, arcname)
