"""End-to-end integration tests for the SkillForgeTool."""

import os
import json
import pytest
from pathlib import Path

from hive.agent.tools.forge import SkillForgeTool
from hive.agent.skills import SkillsLoader


@pytest.mark.asyncio
async def test_forge_tool_creates_valid_skill(tmp_path: Path):
    """Test that the Queen can autonomously create a valid skill with scripts."""
    # Setup
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # 1. Queen exercises the tool directly
    forge_tool = SkillForgeTool(workspace=workspace)
    
    # Simulate LLM tool arguments for an exact scenario
    kwargs = {
        "skill_name": "eth-price",
        "description": "Fetches the current price of Ethereum from CoinGecko.",
        "instructions": "# Usage\nRun the `eth-fetcher.py` script and parse the JSON output.",
        "scripts": {
            "eth-fetcher.py": "import json\nprint('{\"price\": 2500}')"
        },
        "references": {
            "API.md": "CoinGecko API v3 documentation."
        }
    }
    
    # 2. Execute tool
    result = await forge_tool.execute(**kwargs)
    
    # Verify exact success response is passed back to LLM
    assert "Successfully created skill 'eth-price'" in result
    
    # 3. Assert precise file layout was mapped to disk correctly
    skill_dir = workspace / "skills" / "eth-price"
    assert skill_dir.is_dir()
    
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.exists()
    content = skill_md.read_text()
    assert "name: eth-price" in content
    assert "description: Fetches the current price" in content
    
    script_file = skill_dir / "scripts" / "eth-fetcher.py"
    assert script_file.exists()
    assert "import json" in script_file.read_text()
    
    # Verify executable permission was implicitly set by the tool
    assert os.access(script_file, os.X_OK)

    ref_file = skill_dir / "references" / "API.md"
    assert ref_file.exists()
    assert "CoinGecko" in ref_file.read_text()
    
    # 4. Verify the rest of the ecosystem (SkillsLoader) can now consume it
    mock_builtin = tmp_path / "builtin"
    mock_builtin.mkdir()
    loader = SkillsLoader(workspace=workspace, builtin_skills_dir=mock_builtin)
    skills = loader.list_skills()
    
    # Should only be one skill, and it should match our forged one
    assert len(skills) == 1
    assert skills[0]["name"] == "eth-price"
    assert skills[0]["source"] == "workspace"
    
    # Verify XML Context formatting logic
    summary = loader.build_skills_summary()
    assert "<name>eth-price</name>" in summary
    assert "<description>Fetches the current price" in summary


@pytest.mark.asyncio
async def test_forge_tool_rejects_invalid_names(tmp_path: Path):
    """Test that the forge tool safely rejects non-kebab-case names to prevent traversal/weird chars."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    forge_tool = SkillForgeTool(workspace=workspace)
    
    # Uppercase and Spaces
    result1 = await forge_tool.execute(
        skill_name="Ethereum Fetcher!",
        description="Fails.",
        instructions="Fails."
    )
    assert "Error: skill_name must only contain lowercase" in result1
    
    # Directory Traversal attempt
    result2 = await forge_tool.execute(
        skill_name="../hacked-skill",
        description="Fails.",
        instructions="Fails."
    )
    assert "Error: skill_name must only contain lowercase" in result2
    
    # Assert nothing was incorrectly written
    skills_dir = workspace / "skills"
    assert not skills_dir.exists() or len(list(skills_dir.iterdir())) == 0


@pytest.mark.asyncio
async def test_forge_tool_rejects_duplicates(tmp_path: Path):
    """Test that the tool protects existing skills from blind overwrite."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    skills_dir = workspace / "skills"
    skills_dir.mkdir()
    
    # Mock existing skill
    (skills_dir / "test-skill").mkdir()
    
    forge_tool = SkillForgeTool(workspace=workspace)
    result = await forge_tool.execute(
        skill_name="test-skill",
        description="Duplicate",
        instructions="Fails."
    )
    assert "Error: A skill named 'test-skill' already exists" in result
