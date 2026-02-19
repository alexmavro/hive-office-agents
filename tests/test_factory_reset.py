"""Tests for factory reset (S2.6)."""

import json
import zipfile
from pathlib import Path

import pytest

from hive.agent.admin import factory_reset, CONFIRM_PHRASE
from hive.agent.onboarding import OnboardingFlow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """Return (workspace, sessions_dir) with some content populated."""
    hive_root = tmp_path / ".hive"
    workspace = hive_root / "workspace"
    sessions_dir = hive_root / "sessions"

    # Populate memory/
    memory_dir = workspace / "memory"
    (memory_dir / "identity").mkdir(parents=True)
    (memory_dir / "identity" / "user.md").write_text("name: Alex", encoding="utf-8")
    (memory_dir / "projects" / "hive-office").mkdir(parents=True)
    (memory_dir / "projects" / "hive-office" / "decisions.md").write_text(
        "# Decisions\nUsed Python.", encoding="utf-8"
    )
    (memory_dir / "lessons").mkdir(parents=True)
    (memory_dir / "lessons" / "failures.md").write_text(
        "## pip fail\nDon't retry.", encoding="utf-8"
    )
    (memory_dir / "skills" / "_system").mkdir(parents=True)
    (memory_dir / "skills" / "_system" / "core.md").write_text(
        "# System skills", encoding="utf-8"
    )

    # Populate sessions/
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "session_001.jsonl").write_text(
        json.dumps({"id": "1", "role": "user", "content": "hello"}) + "\n",
        encoding="utf-8",
    )

    return workspace, sessions_dir


# ---------------------------------------------------------------------------
# Warning (confirm=False)
# ---------------------------------------------------------------------------

class TestFactoryResetWarning:
    @pytest.mark.asyncio
    async def test_returns_warning_without_confirm(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        result = await factory_reset(
            workspace=workspace,
            templates_dir=None,
            sessions_dir=sessions_dir,
            confirm=False,
        )
        assert "Warning" in result or "warning" in result.lower() or "⚠️" in result
        assert CONFIRM_PHRASE in result

    @pytest.mark.asyncio
    async def test_warning_does_not_delete_anything(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=False,
        )
        assert (workspace / "memory" / "identity" / "user.md").exists()
        assert (sessions_dir / "session_001.jsonl").exists()

    @pytest.mark.asyncio
    async def test_warning_does_not_create_backup(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=False,
        )
        exports_dir = workspace.parent / "exports"
        assert not exports_dir.exists() or not list(exports_dir.glob("*.zip"))


# ---------------------------------------------------------------------------
# Reset (confirm=True)
# ---------------------------------------------------------------------------

class TestFactoryResetConfirmed:
    @pytest.mark.asyncio
    async def test_creates_backup_before_deletion(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        exports_dir = workspace.parent / "exports"
        zips = list(exports_dir.glob("*.zip"))
        assert len(zips) == 1

    @pytest.mark.asyncio
    async def test_backup_contains_memory_files(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        exports_dir = workspace.parent / "exports"
        zip_path = list(exports_dir.glob("*.zip"))[0]
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert any("user.md" in n for n in names)

    @pytest.mark.asyncio
    async def test_backup_contains_session_files(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        exports_dir = workspace.parent / "exports"
        zip_path = list(exports_dir.glob("*.zip"))[0]
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert any("session" in n for n in names)

    @pytest.mark.asyncio
    async def test_memory_directory_cleared(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        # identity/user.md should be gone
        assert not (workspace / "memory" / "identity" / "user.md").exists()

    @pytest.mark.asyncio
    async def test_sessions_directory_cleared(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        assert not sessions_dir.exists() or not list(sessions_dir.rglob("*.jsonl"))

    @pytest.mark.asyncio
    async def test_memory_structure_reinitialised_after_reset(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        # Base directories should be recreated by initialize_memory_hierarchy
        assert (workspace / "memory").is_dir()

    @pytest.mark.asyncio
    async def test_result_mentions_backup_path(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        result = await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        assert "backup" in result.lower() or ".zip" in result

    @pytest.mark.asyncio
    async def test_result_mentions_onboard(self, tmp_path):
        workspace, sessions_dir = make_workspace(tmp_path)
        result = await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        assert "/onboard" in result

    @pytest.mark.asyncio
    async def test_reset_works_when_memory_dir_missing(self, tmp_path):
        """Should not crash if memory/ doesn't exist yet."""
        hive_root = tmp_path / ".hive"
        workspace = hive_root / "workspace"
        workspace.mkdir(parents=True)
        sessions_dir = hive_root / "sessions"
        # Don't create memory/ or sessions_dir

        result = await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        assert "complete" in result.lower() or "reset" in result.lower()

    @pytest.mark.asyncio
    async def test_with_templates_dir_copies_templates(self, tmp_path):
        """When templates_dir is provided, files should be copied."""
        workspace, sessions_dir = make_workspace(tmp_path)

        # Create a minimal templates/memory directory
        templates_dir = tmp_path / "templates" / "memory"
        (templates_dir / "identity").mkdir(parents=True)
        (templates_dir / "identity" / "README.md").write_text(
            "# Identity\n", encoding="utf-8"
        )

        await factory_reset(
            workspace=workspace,
            templates_dir=templates_dir,
            sessions_dir=sessions_dir,
            confirm=True,
        )
        assert (workspace / "memory" / "identity" / "README.md").exists()


# ---------------------------------------------------------------------------
# Post-reset state: onboarding possible
# ---------------------------------------------------------------------------

class TestPostResetState:
    @pytest.mark.asyncio
    async def test_onboarding_not_active_after_reset(self, tmp_path):
        """After factory reset, onboarding is ready for a fresh start."""
        workspace, sessions_dir = make_workspace(tmp_path)
        memory_dir = workspace / "memory"

        # In the LLM-driven design, is_active() is always False
        flow = OnboardingFlow(memory_dir)
        assert not flow.is_active()

        # Reset wipes memory/
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )

        # Fresh flow is still inactive (LLM-driven: no blocking state)
        fresh_flow = OnboardingFlow(workspace / "memory")
        assert not fresh_flow.is_active()

    @pytest.mark.asyncio
    async def test_can_onboard_fresh_after_reset(self, tmp_path):
        """After reset, /onboard should work cleanly (LLM-driven: returns mission prompt)."""
        workspace, sessions_dir = make_workspace(tmp_path)
        await factory_reset(
            workspace=workspace, templates_dir=None,
            sessions_dir=sessions_dir, confirm=True,
        )
        flow = OnboardingFlow(workspace / "memory")
        result = flow.start()
        # LLM-driven design: start() returns a mission prompt (not a phase header)
        assert isinstance(result, str) and len(result) > 0
        assert "write_file" in result or "interview" in result.lower()
        # is_active() is always False in the new LLM-driven design
        assert not flow.is_active()
