"""CLI utilities for skill creation and packaging."""

import os
import re
import shutil
import zipfile
from pathlib import Path

import typer
from rich.console import Console

console = Console()
skill = typer.Typer(help="Manage Hive agent skills.")


@skill.command(name="init")
def init_skill(
    name: str = typer.Argument(..., help="Name of the skill to initialize."),
    desc: str = typer.Option("A new skill.", "--desc", "-d", help="Description of the skill."),
    workspace: str = typer.Option("~/.hive/workspace", "--workspace", help="Path to the agent workspace.")
) -> None:
    """Initialize a new empty skill directory."""
    if not re.match(r"^[a-z0-9-]+$", name):
        console.print("Error: Skill name must be lowercase alphanumeric with dashes.", style="red")
        raise typer.Abort()

    workspace_path = Path(workspace).expanduser().resolve()
    skill_dir = workspace_path / "skills" / name

    if skill_dir.exists():
        console.print(f"Error: Skill '{name}' already exists at {skill_dir}", style="red")
        raise typer.Abort()

    try:
        # Scaffold directory
        skill_dir.mkdir(parents=True)
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)
        
        # Write SKILL.md
        skill_md_content = f"""---
name: {name}
description: {desc}
---

# {name}

## Quick Start
Provide instructions here on how the Queen should use this skill.

## Advanced Usage
Add complex logic references here.
"""
        (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")
        
        console.print(f"Successfully initialized skill '{name}' at {skill_dir}", style="green")
        
    except Exception as e:
        console.print(f"Failed to initialize skill: {e}", style="red")
        raise typer.Abort()


@skill.command(name="package")
def package_skill(
    name: str = typer.Argument(..., help="Name of the skill to package."),
    workspace: str = typer.Option("~/.hive/workspace", "--workspace", help="Path to the agent workspace."),
    outdir: str = typer.Option(".", "--outdir", help="Directory to save the .skill package.")
) -> None:
    """Package a skill directory into a distributable .skill archive."""
    workspace_path = Path(workspace).expanduser().resolve()
    skill_dir = workspace_path / "skills" / name
    
    if not skill_dir.exists():
        console.print(f"Error: Skill '{name}' does not exist at {skill_dir}", style="red")
        raise typer.Abort()
        
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        console.print(f"Error: Skill directory is missing SKILL.md", style="red")
        raise typer.Abort()
        
    # Validate frontmatter exists
    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        console.print(f"Error: SKILL.md is missing YAML frontmatter.", style="red")
        raise typer.Abort()

    out_path = Path(outdir).resolve() / f"{name}.skill"
    
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(skill_dir):
                for file in files:
                    file_path = Path(root) / file
                    # Calculate arcname relative to the skill root directory
                    arcname = file_path.relative_to(skill_dir)
                    zf.write(file_path, arcname)
                    
        console.print(f"Successfully packaged skill '{name}' to {out_path}", style="green")
    except Exception as e:
        console.print(f"Failed to package skill: {e}", style="red")
        raise typer.Abort()
