"""CLI utilities for skill creation and packaging."""

import click
import os
import re
import shutil
import zipfile
from pathlib import Path


@click.group()
def skill():
    """Manage Hive agent skills."""
    pass


@skill.command(name="init")
@click.argument("name")
@click.option("--desc", "-d", default="A new skill.", help="Description of the skill.")
@click.option("--workspace", default="~/.hive/workspace", help="Path to the agent workspace.")
def init_skill(name: str, desc: str, workspace: str) -> None:
    """Initialize a new empty skill directory."""
    if not re.match(r"^[a-z0-9-]+$", name):
        click.secho("Error: Skill name must be lowercase alphanumeric with dashes.", fg="red")
        raise click.Abort()

    workspace_path = Path(workspace).expanduser().resolve()
    skill_dir = workspace_path / "skills" / name

    if skill_dir.exists():
        click.secho(f"Error: Skill '{name}' already exists at {skill_dir}", fg="red")
        raise click.Abort()

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
        
        click.secho(f"Successfully initialized skill '{name}' at {skill_dir}", fg="green")
        
    except Exception as e:
        click.secho(f"Failed to initialize skill: {e}", fg="red")
        raise click.Abort()


@skill.command(name="package")
@click.argument("name")
@click.option("--workspace", default="~/.hive/workspace", help="Path to the agent workspace.")
@click.option("--outdir", default=".", help="Directory to save the .skill package.")
def package_skill(name: str, workspace: str, outdir: str) -> None:
    """Package a skill directory into a distributable .skill archive."""
    workspace_path = Path(workspace).expanduser().resolve()
    skill_dir = workspace_path / "skills" / name
    
    if not skill_dir.exists():
        click.secho(f"Error: Skill '{name}' does not exist at {skill_dir}", fg="red")
        raise click.Abort()
        
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        click.secho(f"Error: Skill directory is missing SKILL.md", fg="red")
        raise click.Abort()
        
    # Validate frontmatter exists
    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        click.secho(f"Error: SKILL.md is missing YAML frontmatter.", fg="red")
        raise click.Abort()

    out_path = Path(outdir).resolve() / f"{name}.skill"
    
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(skill_dir):
                for file in files:
                    file_path = Path(root) / file
                    # Calculate arcname relative to the skill root directory
                    arcname = file_path.relative_to(skill_dir)
                    zf.write(file_path, arcname)
                    
        click.secho(f"Successfully packaged skill '{name}' to {out_path}", fg="green")
    except Exception as e:
        click.secho(f"Failed to package skill: {e}", fg="red")
        raise click.Abort()
