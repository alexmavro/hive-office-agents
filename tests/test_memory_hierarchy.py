"""Tests for memory hierarchy initialization (S2.1)."""

import json
from pathlib import Path

import pytest

from hive.agent.memory import MEMORY_DIRS, initialize_memory_hierarchy


EXPECTED_DIRS = [
    "identity",
    "systems",
    "projects/_template",
    "procedural/workflows",
    "procedural/fixes",
    "lessons",
    "skills/_system",
    "skills/_user",
]

EXPECTED_READMES = [
    "identity/README.md",
    "systems/README.md",
    "projects/README.md",
    "procedural/README.md",
    "procedural/workflows/README.md",
    "procedural/fixes/README.md",
    "lessons/README.md",
    "skills/README.md",
    "skills/_system/README.md",
    "skills/_user/README.md",
]

EXPECTED_TEMPLATES = [
    "identity/user.md.template",
    "identity/constraints.md.template",
    "identity/preferences.md.template",
    "identity/context.md.template",
    "identity/worker_shared.md.template",
    "systems/infrastructure.md.template",
    "systems/tools.md.template",
    "systems/topology.md.template",
    "projects/_template/README.md",
    "projects/_template/decisions.md",
    "projects/_template/blockers.md",
    "projects/_template/todos.md",
    "projects/_template/changelog.md",
    "projects/_template/working_memory.yaml.template",
    "lessons/successes.md.template",
    "lessons/failures.md.template",
    "lessons/patterns.md.template",
    "skills/skills_registry.json.template",
]


def find_templates_dir() -> Path:
    """Locate the templates/memory directory relative to this file."""
    repo_root = Path(__file__).parent.parent
    return repo_root / "templates" / "memory"


class TestInitializeMemoryHierarchy:
    def test_creates_all_directories(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        initialize_memory_hierarchy(workspace)
        memory_dir = workspace / "memory"
        for subdir in EXPECTED_DIRS:
            assert (memory_dir / subdir).is_dir(), f"Missing directory: memory/{subdir}"

    def test_is_idempotent(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        # Write a file to identity/ before init
        (workspace / "memory" / "identity").mkdir(parents=True)
        sentinel = workspace / "memory" / "identity" / "existing.txt"
        sentinel.write_text("do not overwrite")

        initialize_memory_hierarchy(workspace)
        initialize_memory_hierarchy(workspace)  # second call

        # Existing file must still be there
        assert sentinel.exists()
        assert sentinel.read_text() == "do not overwrite"

    def test_copies_templates_from_templates_dir(self, tmp_path):
        templates_dir = find_templates_dir()
        if not templates_dir.exists():
            pytest.skip("templates/memory/ not found in repo")

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        initialize_memory_hierarchy(workspace, templates_dir)

        memory_dir = workspace / "memory"
        for template_path in EXPECTED_TEMPLATES:
            assert (memory_dir / template_path).exists(), \
                f"Missing template: memory/{template_path}"

    def test_does_not_overwrite_existing_files(self, tmp_path):
        templates_dir = find_templates_dir()
        if not templates_dir.exists():
            pytest.skip("templates/memory/ not found in repo")

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "memory" / "identity").mkdir(parents=True)

        # Pre-create user.md.template with custom content
        existing = workspace / "memory" / "identity" / "user.md.template"
        existing.write_text("custom content — do not overwrite")

        initialize_memory_hierarchy(workspace, templates_dir)

        # Custom content must be preserved
        assert existing.read_text() == "custom content — do not overwrite"

    def test_works_without_templates_dir(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        # Should not raise even without templates
        initialize_memory_hierarchy(workspace, templates_dir=None)
        assert (workspace / "memory" / "identity").is_dir()


class TestAllReadmeFiles:
    def test_all_readme_files_present_in_repo(self):
        templates_dir = find_templates_dir()
        if not templates_dir.exists():
            pytest.skip("templates/memory/ not found in repo")

        for readme_path in EXPECTED_READMES:
            full_path = templates_dir / readme_path
            assert full_path.exists(), f"Missing README: templates/memory/{readme_path}"

    def test_readme_files_have_content(self):
        templates_dir = find_templates_dir()
        if not templates_dir.exists():
            pytest.skip("templates/memory/ not found in repo")

        for readme_path in EXPECTED_READMES:
            full_path = templates_dir / readme_path
            if full_path.exists():
                content = full_path.read_text()
                assert len(content.strip()) > 10, \
                    f"README is too short to be useful: {readme_path}"


class TestAllTemplateFiles:
    def test_all_templates_present_in_repo(self):
        templates_dir = find_templates_dir()
        if not templates_dir.exists():
            pytest.skip("templates/memory/ not found in repo")

        for template_path in EXPECTED_TEMPLATES:
            full_path = templates_dir / template_path
            assert full_path.exists(), \
                f"Missing template: templates/memory/{template_path}"

    def test_skills_registry_template_is_valid_json(self):
        templates_dir = find_templates_dir()
        if not templates_dir.exists():
            pytest.skip("templates/memory/ not found in repo")

        registry = templates_dir / "skills" / "skills_registry.json.template"
        if registry.exists():
            data = json.loads(registry.read_text())
            assert "skills" in data
            assert isinstance(data["skills"], list)


class TestMemoryDirsConstant:
    def test_memory_dirs_is_complete(self):
        for expected in EXPECTED_DIRS:
            assert expected in MEMORY_DIRS, \
                f"MEMORY_DIRS is missing: {expected}"
