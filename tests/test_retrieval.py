"""Tests for query-driven memory retrieval (S2.2)."""

from pathlib import Path

import pytest

from hive.agent.retrieval import MemoryRetriever


def make_workspace(tmp_path: Path) -> tuple[Path, MemoryRetriever]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    retriever = MemoryRetriever(workspace)
    return workspace, retriever


def write_identity(workspace: Path, filename: str, content: str) -> None:
    identity_dir = workspace / "memory" / "identity"
    identity_dir.mkdir(parents=True, exist_ok=True)
    (identity_dir / filename).write_text(content, encoding="utf-8")


class TestAlwaysLoadedIdentity:
    def test_loads_user_md_when_present(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        write_identity(workspace, "user.md", "name: Alex\nrole: Builder")
        ctx = retriever.build_memory_context()
        assert "Alex" in ctx
        assert "Builder" in ctx

    def test_loads_constraints_when_present(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        write_identity(workspace, "constraints.md", "Never manipulate.")
        ctx = retriever.build_memory_context()
        assert "Never manipulate" in ctx

    def test_loads_preferences_when_present(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        write_identity(workspace, "preferences.md", "style: direct")
        ctx = retriever.build_memory_context()
        assert "direct" in ctx

    def test_loads_all_three_identity_files(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        write_identity(workspace, "user.md", "name: Alex")
        write_identity(workspace, "constraints.md", "No manipulation.")
        write_identity(workspace, "preferences.md", "Direct communication.")
        ctx = retriever.build_memory_context()
        assert "Alex" in ctx
        assert "No manipulation" in ctx
        assert "Direct communication" in ctx


class TestEmptyMemory:
    def test_empty_memory_returns_empty_string(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        ctx = retriever.build_memory_context()
        assert ctx == ""

    def test_no_crash_when_memory_dir_missing(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        retriever = MemoryRetriever(workspace)
        # memory/ doesn't exist at all
        ctx = retriever.build_memory_context()
        assert ctx == ""

    def test_skips_empty_files(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        write_identity(workspace, "user.md", "   \n  ")  # whitespace only
        ctx = retriever.build_memory_context()
        assert ctx == ""


class TestActiveProject:
    def test_loads_working_memory_when_active_project_set(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        # Create project and working memory
        project_dir = workspace / "memory" / "projects" / "hive-office"
        project_dir.mkdir(parents=True)
        (project_dir / "working_memory.yaml").write_text(
            "project: hive-office\nstatus: active", encoding="utf-8"
        )
        # Set active project marker
        (workspace / "memory" / ".active_project").write_text("hive-office")

        ctx = retriever.build_memory_context()
        assert "hive-office" in ctx
        assert "active" in ctx

    def test_no_active_project_file_means_no_project_context(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        project_dir = workspace / "memory" / "projects" / "hive-office"
        project_dir.mkdir(parents=True)
        (project_dir / "working_memory.yaml").write_text("project: hive-office")
        # No .active_project file

        ctx = retriever.build_memory_context()
        assert "hive-office" not in ctx

    def test_active_project_missing_dir_is_ignored(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        (workspace / "memory").mkdir(parents=True)
        # .active_project points to non-existent directory
        (workspace / "memory" / ".active_project").write_text("nonexistent")

        ctx = retriever.build_memory_context()
        assert ctx == ""


class TestOnDemandWorkflows:
    def test_loads_workflow_matching_task_hint(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        workflows_dir = workspace / "memory" / "procedural" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "deploy_service.md").write_text(
            "# Deploy Service\nStep 1: build image"
        )

        ctx = retriever.build_memory_context(task_hint="deploy")
        assert "Deploy Service" in ctx
        assert "build image" in ctx

    def test_does_not_load_nonmatching_workflow(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        workflows_dir = workspace / "memory" / "procedural" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "deploy_service.md").write_text("# Deploy Service\nSecret steps")

        ctx = retriever.build_memory_context(task_hint="research")
        assert "Secret steps" not in ctx

    def test_no_task_hint_loads_no_workflow(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        workflows_dir = workspace / "memory" / "procedural" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "deploy_service.md").write_text("# Deploy Service\nSecret steps")

        ctx = retriever.build_memory_context()  # no task_hint
        assert "Secret steps" not in ctx


class TestOnDemandFailureLessons:
    def test_loads_matching_failure_paragraph(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        lessons_dir = workspace / "memory" / "lessons"
        lessons_dir.mkdir(parents=True)
        (lessons_dir / "failures.md").write_text(
            "## pip install in container\n"
            "Packages lost on restart.\n"
            "\n"
            "## unrelated failure\n"
            "Something else entirely.\n"
        )

        ctx = retriever.build_memory_context(task_hint="pip")
        assert "Packages lost on restart" in ctx
        assert "Something else entirely" not in ctx

    def test_no_failures_file_is_graceful(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        (workspace / "memory" / "lessons").mkdir(parents=True)
        # failures.md doesn't exist

        ctx = retriever.build_memory_context(task_hint="deploy")
        assert ctx == ""


class TestContextFormat:
    def test_sections_separated_by_divider(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        write_identity(workspace, "user.md", "name: Alex")
        write_identity(workspace, "constraints.md", "No manipulation.")

        ctx = retriever.build_memory_context()
        assert "---" in ctx

    def test_active_project_label_in_context(self, tmp_path):
        workspace, retriever = make_workspace(tmp_path)
        project_dir = workspace / "memory" / "projects" / "my-project"
        project_dir.mkdir(parents=True)
        (project_dir / "working_memory.yaml").write_text("status: active")
        (workspace / "memory" / ".active_project").write_text("my-project")

        ctx = retriever.build_memory_context()
        assert "Active Project: my-project" in ctx
