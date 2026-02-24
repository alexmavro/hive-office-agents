"""Skill Forge tool for creating new capabilities."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import Field

from hive.agent.tools.base import Tool


class SkillForgeTool(Tool):
    """Tool for packaging working code into permanent skills."""
    
    @property
    def name(self) -> str:
        return "forge_skill"
        
    @property
    def description(self) -> str:
        return (
            "Packages working code into a permanent skill in ~/.hive/workspace/skills/. "
            "Use this ONLY AFTER you have tested the code and verified it works "
            "using the docker_exec tool. A skill consists of a name, description, "
            "markdown instructions, and optional python/shell scripts."
        )
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Unique name for the skill (lowercase, alphanumeric, dashes only, e.g., 'eth-fetcher')",
                },
                "description": {
                    "type": "string",
                    "description": "A clear description that helps the Queen know WHEN to use this skill.",
                },
                "instructions": {
                    "type": "string",
                    "description": "The markdown body for SKILL.md. This should tell the agent how to use the provided scripts or perform the task.",
                },
                "scripts": {
                    "type": "object",
                    "description": "Optional mapping of filename to code content (e.g., {'fetch.py': 'print(\"hello\")'}). Will be saved in the scripts/ subdirectory.",
                    "additionalProperties": {"type": "string"}
                },
                "references": {
                    "type": "object",
                    "description": "Optional mapping of filename to markdown content (e.g., {'API.md': '# API Reference'}). Will be saved in the references/ subdirectory.",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["skill_name", "description", "instructions"],
        }
        
    def __init__(self, workspace: Path):
        self._workspace = workspace
        self._skills_dir = workspace / "skills"

    async def execute(self, **kwargs: Any) -> str:
        skill_name = kwargs["skill_name"]
        description = kwargs["description"]
        instructions = kwargs["instructions"]
        scripts = kwargs.get("scripts") or {}
        references = kwargs.get("references") or {}
        
        # Validate name
        if not re.match(r"^[a-z0-9-]+$", skill_name):
            return "Error: skill_name must only contain lowercase letters, numbers, and dashes (e.g., my-cool-skill)."
            
        skill_dir = self._skills_dir / skill_name
        
        # Check if already exists
        if skill_dir.exists():
            return f"Error: A skill named '{skill_name}' already exists at {skill_dir}."
            
        try:
            # 1. Create directory structure
            skill_dir.mkdir(parents=True, exist_ok=True)
            
            # 2. Add scripts
            if scripts:
                scripts_dir = skill_dir / "scripts"
                scripts_dir.mkdir(parents=True, exist_ok=True)
                for filename, content in scripts.items():
                    # Basic filename sanitization to prevent directory traversal
                    safe_filename = Path(filename).name
                    file_path = scripts_dir / safe_filename
                    file_path.write_text(content, encoding="utf-8")
                    
                    # Make shell and python scripts executable just in case
                    if file_path.suffix in [".sh", ".py"]:
                        file_path.chmod(0o755)

            # 3. Add references
            if references:
                refs_dir = skill_dir / "references"
                refs_dir.mkdir(parents=True, exist_ok=True)
                for filename, content in references.items():
                    safe_filename = Path(filename).name
                    file_path = refs_dir / safe_filename
                    file_path.write_text(content, encoding="utf-8")
            
            # 4. Write SKILL.md
            # Note: The skills loader uses simple string parsing for YAML frontmatter
            skill_md_content = f"""---
name: {skill_name}
description: {description}
---

{instructions}
"""
            skill_md_path = skill_dir / "SKILL.md"
            skill_md_path.write_text(skill_md_content, encoding="utf-8")
            
            return f"Successfully created skill '{skill_name}'. It is now available in your context for future operations."
            
        except Exception as e:
            # Attempt cleanup if something failed mid-way
            if skill_dir.exists():
                import shutil
                shutil.rmtree(skill_dir, ignore_errors=True)
            return f"Error creating skill: {str(e)}"
