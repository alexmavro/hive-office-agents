"""Tests for the skill CLI utilities."""

import os
import zipfile
from pathlib import Path
from click.testing import CliRunner

from hive.cli.skill_utils import init_skill, package_skill


def test_skill_init_scaffolds_correctly(tmp_path: Path):
    """Test that hive skill init creates the right folders and files."""
    runner = CliRunner()
    
    # Run init command
    result = runner.invoke(init_skill, ["my-test-skill", "--desc", "Test skill", "--workspace", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Successfully initialized skill" in result.output
    
    # Check directory structure
    skill_dir = tmp_path / "skills" / "my-test-skill"
    assert skill_dir.is_dir()
    assert (skill_dir / "scripts").is_dir()
    assert (skill_dir / "references").is_dir()
    
    # Check SKILL.md
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.exists()
    
    content = skill_md.read_text()
    assert "name: my-test-skill" in content
    assert "description: Test skill" in content
    assert "---" in content


def test_skill_init_rejects_invalid_name(tmp_path: Path):
    """Test that invalid names are rejected."""
    runner = CliRunner()
    
    # Run init command with spaces and capitals
    result = runner.invoke(init_skill, ["My Invalid Skill!", "--workspace", str(tmp_path)])
    
    assert result.exit_code != 0
    assert "Error: Skill name must be lowercase" in result.output


def test_skill_package_zips_correctly(tmp_path: Path):
    """Test that hive skill package creates a valid zip file."""
    runner = CliRunner()
    
    # 1. Init a skill
    runner.invoke(init_skill, ["hello-world", "--workspace", str(tmp_path)])
    
    skill_dir = tmp_path / "skills" / "hello-world"
    
    # 2. Add a dummy script
    script = skill_dir / "scripts" / "test.py"
    script.write_text("print('hello')", encoding="utf-8")
    
    # 3. Package the skill
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    
    result = runner.invoke(package_skill, ["hello-world", "--workspace", str(tmp_path), "--outdir", str(out_dir)])
    
    assert result.exit_code == 0
    
    # 4. Verify zip contents
    zip_path = out_dir / "hello-world.skill"
    assert zip_path.exists()
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.namelist()
        assert "SKILL.md" in members
        assert "scripts/test.py" in members


def test_skill_package_fails_on_missing_frontmatter(tmp_path: Path):
    """Test that package refuses to zip if SKILL.md is missing YAML frontmatter."""
    runner = CliRunner()
    
    # 1. Setup skill dir manually
    skill_dir = tmp_path / "skills" / "bad-skill"
    skill_dir.mkdir(parents=True)
    
    # 2. Add SKILL.md without YAML
    (skill_dir / "SKILL.md").write_text("# Bad Skill\n\nNo frontmatter here.")
    
    # 3. Package it
    result = runner.invoke(package_skill, ["bad-skill", "--workspace", str(tmp_path), "--outdir", str(tmp_path)])
    
    assert result.exit_code != 0
    assert "Error: SKILL.md is missing YAML frontmatter" in result.output
