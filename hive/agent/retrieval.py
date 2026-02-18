"""Query-driven memory retrieval for the agent context builder.

Replaces flat MEMORY.md loading with structured memory/ hierarchy.
Loads identity files always; other files on-demand based on task context.
"""

from pathlib import Path


class MemoryRetriever:
    """Load relevant memory from the memory/ hierarchy for the system prompt.

    Always loaded:
        - identity/user.md, constraints.md, preferences.md

    Loaded when active project exists:
        - projects/{active}/working_memory.yaml

    Loaded on-demand (keyword match against task_hint):
        - procedural/workflows/{name}.md  — when task_hint matches filename
        - lessons/failures.md             — when task_hint appears in content

    Never loaded automatically:
        - Archived projects
        - Old conversation branches
        - Raw lesson entries not relevant to current task
    """

    ALWAYS_IDENTITY = ["user.md", "constraints.md", "preferences.md"]

    def __init__(self, workspace: Path):
        self.memory_dir = workspace / "memory"

    def build_memory_context(self, task_hint: str | None = None) -> str:
        """Assemble context string for injection into the system prompt.

        Args:
            task_hint: Optional keyword describing current task type.
                       Used for on-demand workflow/lesson loading.

        Returns:
            Assembled context string, or empty string if no memory files exist.
        """
        parts: list[str] = []

        # --- ALWAYS LOADED: identity ---
        for filename in self.ALWAYS_IDENTITY:
            content = self._load_if_exists(f"identity/{filename}")
            if content:
                parts.append(content.strip())

        # --- ALWAYS LOADED: active project working memory ---
        active = self._get_active_project()
        if active:
            wm = self._load_if_exists(f"projects/{active}/working_memory.yaml")
            if wm:
                parts.append(f"## Active Project: {active}\n\n{wm.strip()}")

        # --- ON-DEMAND: relevant workflow ---
        if task_hint:
            workflow = self._find_workflow(task_hint)
            if workflow:
                parts.append(f"## Relevant Workflow\n\n{workflow.strip()}")

            failure = self._search_file_for_keyword("lessons/failures.md", task_hint)
            if failure:
                parts.append(f"## Known Failure Pattern\n\n{failure.strip()}")

        if not parts:
            return ""

        return "\n\n---\n\n".join(parts)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_if_exists(self, relative_path: str) -> str | None:
        """Load a file from the memory/ directory, or return None if missing."""
        path = self.memory_dir / relative_path
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8").strip()
            return content if content else None
        return None

    def _get_active_project(self) -> str | None:
        """Return the name of the active project, or None.

        The active project is stored in memory/.active_project (one-line file).
        Set during /onboard or by the user manually.
        """
        marker = self.memory_dir / ".active_project"
        if marker.exists():
            name = marker.read_text(encoding="utf-8").strip()
            if name and (self.memory_dir / "projects" / name).is_dir():
                return name
        return None

    def _find_workflow(self, task_hint: str) -> str | None:
        """Find a workflow file whose name contains task_hint (case-insensitive).

        Checks procedural/workflows/{name}.md files.
        Returns content of first match, or None.
        """
        workflows_dir = self.memory_dir / "procedural" / "workflows"
        if not workflows_dir.is_dir():
            return None

        hint_lower = task_hint.lower()
        for md_file in sorted(workflows_dir.glob("*.md")):
            if hint_lower in md_file.stem.lower():
                content = md_file.read_text(encoding="utf-8").strip()
                if content:
                    return content
        return None

    def _search_file_for_keyword(self, relative_path: str, keyword: str) -> str | None:
        """Search a file for a keyword, return matching paragraphs.

        Returns the surrounding context of lines that contain the keyword,
        or None if no matches found or file doesn't exist.
        """
        path = self.memory_dir / relative_path
        if not path.exists():
            return None

        lines = path.read_text(encoding="utf-8").splitlines()
        keyword_lower = keyword.lower()

        matching_paragraphs: list[str] = []
        current_paragraph: list[str] = []

        for line in lines:
            if line.strip() == "":
                # Paragraph boundary
                if current_paragraph:
                    paragraph_text = "\n".join(current_paragraph)
                    if keyword_lower in paragraph_text.lower():
                        matching_paragraphs.append(paragraph_text)
                    current_paragraph = []
            else:
                current_paragraph.append(line)

        # Handle last paragraph
        if current_paragraph:
            paragraph_text = "\n".join(current_paragraph)
            if keyword_lower in paragraph_text.lower():
                matching_paragraphs.append(paragraph_text)

        return "\n\n".join(matching_paragraphs) if matching_paragraphs else None
