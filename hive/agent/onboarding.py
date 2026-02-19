"""Onboarding and profile intake for new users.

Three intake paths share the same privacy-first pattern:
  1. /onboard   — LLM-driven conversational interview, saves as it goes
  2. File upload — reads doc, extracts, shows summary, saves only after confirmation
  3. URL/link   — fetches page, extracts, shows summary, saves only after confirmation

Privacy rules for document/link intake (DSGVO-aware):
  - File content is processed through the LLM but not reproduced in responses
  - Nothing is written to memory until the user explicitly confirms
  - After saving, the source file is archived (read-only) in uploads/archive/
  - Links are logged in uploads/archive/links.md after saving
"""

from pathlib import Path


# ---------------------------------------------------------------------------
# Shared archive path helper
# ---------------------------------------------------------------------------

def _archive_path(workspace: Path) -> str:
    return str((workspace / "uploads" / "archive").expanduser().resolve())


# ---------------------------------------------------------------------------
# /onboard — conversational interview
# ---------------------------------------------------------------------------

def get_onboarding_prompt(workspace: Path) -> str:
    """Return the onboarding mission text to inject as the LLM's task.

    The caller passes this as the 'current_message' to context.build_messages(),
    so the LLM sees it as the latest user input and responds with the first question.
    """
    memory_path = str((workspace / "memory").expanduser().resolve())
    return (
        "The user has typed /onboard. Your job is to get to know them — as a person "
        "and as someone you'll be working with closely.\n\n"
        "Do NOT run a form or a checklist. Ask real, thoughtful questions — the kind "
        "that reveal how someone thinks, what drives them, and what matters to them. "
        "Use their answers to naturally draw out the practical context too "
        "(what they're building, how they want you to behave). "
        "Ask 1-2 questions at a time. Be curious, warm, a bit playful.\n\n"
        "Think of questions like:\n"
        "  - What principle guides most of your decisions?\n"
        "  - What kind of problem do you find most satisfying to solve?\n"
        "  - What does a good working relationship look like to you?\n"
        "  - What are you trying to build right now, and why does it matter to you?\n"
        "  - What's one thing you'd never compromise on — in work or in life?\n"
        "  - How do you like to work — structured and planned, or fluid and reactive?\n"
        "  - When should I just get on with it, and when should I always ask first?\n\n"
        "You don't need to cover every topic mechanically. Let the conversation breathe. "
        "If an answer naturally leads somewhere interesting, follow it.\n\n"
        "As you learn things, silently save them using write_file. "
        "Write interpreted, useful summaries — not verbatim quotes. "
        "The user doesn't need to see you saving; just do it naturally as you go:\n"
        f"  {memory_path}/identity/user.md — who they are, what they do, their context\n"
        f"  {memory_path}/identity/constraints.md — non-negotiables as clear bullet points\n"
        f"  {memory_path}/identity/preferences.md — how they want to work with you\n"
        f"  {memory_path}/systems/infrastructure.md — their technical setup\n\n"
        "If they name an active project, create:\n"
        f"  {memory_path}/projects/<name>/ — with decisions.md, todos.md, blockers.md\n"
        f"  {memory_path}/projects/<name>/working_memory.yaml — with their stated objective\n"
        f"  {memory_path}/.active_project — just the project name on one line\n\n"
        "Start with something interesting. Not 'What's your name?'."
    )


# ---------------------------------------------------------------------------
# File upload intake — read, extract, confirm, then save + archive
# ---------------------------------------------------------------------------

def get_document_intake_prompt(file_paths: list[str], workspace: Path, user_text: str = "") -> str:
    """Return the document intake mission for the LLM.

    Injected when the user uploads one or more non-image files. The Queen reads
    them, extracts relevant info, shows a summary, and waits for explicit
    confirmation before writing anything to memory. After saving, the source
    file is archived (read-only).

    Supported formats: PDF, DOCX, TXT, MD, HTML, CSV, JSON, YAML, and any
    plain-text format the system can open. For unreadable binaries the Queen
    will say so and suggest alternatives.
    """
    memory_path = str((workspace / "memory").expanduser().resolve())
    archive = _archive_path(workspace)
    files_str = "\n".join(f"  {p}" for p in file_paths)
    context_line = f'\nThe user also wrote: "{user_text}"\n' if user_text.strip() else ""
    count_word = "a file" if len(file_paths) == 1 else f"{len(file_paths)} files"

    return (
        f"The user has uploaded {count_word} for you to review:\n"
        f"{files_str}\n"
        f"{context_line}\n"
        "Steps:\n"
        "1. Read the file using read_file.\n"
        "   - If content looks garbled or binary, try exec('pdftotext <path> -') for PDFs\n"
        "   - If still unreadable, tell the user: suggest plain text, markdown, or PDF export\n\n"
        "2. For profile/context documents (CV, LinkedIn export, company bio, brand guide):\n"
        "   a) Extract the relevant facts — interpreted, in your own words\n"
        "   b) Show the user a clear summary: what you found, and exactly what you'd save:\n"
        f"      • identity/user.md — name, role, background, what they do\n"
        f"      • identity/constraints.md — non-negotiables (if mentioned)\n"
        f"      • identity/preferences.md — working style, communication (if mentioned)\n"
        f"      • systems/infrastructure.md — technical setup (if mentioned)\n"
        "   c) End with: 'Shall I save this? Reply yes to confirm or tell me what to change.'\n\n"
        "3. ONLY after the user confirms (yes / save it / looks good / etc.):\n"
        "   a) Write the summaries to the memory files using write_file\n"
        f"  b) Archive the source: exec('mkdir -p {archive} && mv <path> {archive}/ && chmod 444 {archive}/<filename>')\n"
        "   c) Confirm briefly: what was saved and where the original is archived\n\n"
        "4. For technical files (code, config, data, logs): help with what they need instead.\n"
    )


# ---------------------------------------------------------------------------
# Link/URL intake — fetch, extract, confirm, then save + log
# ---------------------------------------------------------------------------

def get_link_intake_prompt(url: str, workspace: Path, user_text: str = "") -> str:
    """Return the link intake mission for the LLM.

    Injected when the user sends a bare URL (profile page, LinkedIn, company site, etc.).
    Same privacy-first flow as document intake: extract → show summary → confirm → save.
    The URL is logged to the archive after saving.
    """
    memory_path = str((workspace / "memory").expanduser().resolve())
    archive = _archive_path(workspace)
    context_line = f'\nThe user also wrote: "{user_text}"\n' if user_text.strip() else ""

    return (
        f"The user has sent a link:\n  {url}\n"
        f"{context_line}\n"
        "Steps:\n"
        "1. Use web_fetch to read the page content.\n"
        "   - If the page is inaccessible or too large, tell the user and ask them to paste the text.\n\n"
        "2. For profile/context pages (LinkedIn, personal site, company about page, portfolio):\n"
        "   a) Extract the relevant facts — interpreted, in your own words\n"
        "   b) Show the user a clear summary: what you found, and exactly what you'd save:\n"
        f"      • identity/user.md — name, role, background, what they do\n"
        f"      • identity/constraints.md — non-negotiables (if mentioned)\n"
        f"      • identity/preferences.md — working style (if mentioned)\n"
        f"      • systems/infrastructure.md — technical setup (if mentioned)\n"
        "   c) End with: 'Shall I save this? Reply yes to confirm or tell me what to change.'\n\n"
        "3. ONLY after the user confirms:\n"
        "   a) Write the summaries to the memory files using write_file\n"
        f"  b) Log the source URL: exec('mkdir -p {archive} && echo \"{url}\" >> {archive}/links.md')\n"
        "   c) Confirm briefly: what was saved\n\n"
        "4. For technical/research pages (docs, articles, tools): help with what they need instead.\n"
    )


# ---------------------------------------------------------------------------
# OnboardingFlow — thin wrapper for loop.py and tests
# ---------------------------------------------------------------------------

class OnboardingFlow:
    """Onboarding helper (LLM-driven).

    With the LLM-driven approach, this class is a thin wrapper:
      - is_active() always returns False — no message interception
      - start() returns the onboarding mission prompt for the LLM

    The state_file attribute is kept so factory_reset can reference it if needed,
    but it is no longer written to.
    """

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        # Kept for backward compatibility (e.g. factory_reset wipes the whole memory/ dir)
        self.state_file = memory_dir / ".onboarding_state.json"

    def is_active(self) -> bool:
        """Always returns False — onboarding no longer blocks normal message routing."""
        return False

    def start(self) -> str:
        """Return the onboarding mission prompt for the LLM."""
        workspace = self.memory_dir.parent
        return get_onboarding_prompt(workspace)
