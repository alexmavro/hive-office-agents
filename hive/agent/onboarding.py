"""Onboarding for new users (/onboard command).

LLM-driven design:
  - /onboard injects a mission prompt into the LLM conversation
  - The LLM conducts a friendly intake interview
  - The LLM uses write_file to save structured summaries to memory files
  - No state machine — the LLM handles the flow naturally, interprets answers intelligently
"""

from pathlib import Path


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


def get_document_intake_prompt(file_paths: list[str], workspace: Path, user_text: str = "") -> str:
    """Return the document intake mission for the LLM.

    Injected when the user uploads one or more non-image files. The Queen reads
    them, determines what they are, and extracts useful information to memory.
    """
    memory_path = str((workspace / "memory").expanduser().resolve())
    files_str = "\n".join(f"  {p}" for p in file_paths)
    context_line = f'\nThe user also wrote: "{user_text}"\n' if user_text.strip() else ""

    return (
        f"The user has uploaded {'a file' if len(file_paths) == 1 else 'files'}:\n"
        f"{files_str}\n"
        f"{context_line}\n"
        "Steps:\n"
        "1. Read the file(s) using read_file.\n"
        "   - If content looks garbled or binary (e.g. a PDF), try: exec with 'pdftotext <path> -'\n"
        "   - If you still can't read it, tell the user what format works best.\n"
        "2. Decide what it is:\n"
        "   a) Profile/context document (CV, LinkedIn export, company bio, brand guide, about page):\n"
        "      Extract and save structured summaries using write_file — interpreted facts, not verbatim:\n"
        f"      {memory_path}/identity/user.md — who they are, their role, background, context\n"
        f"      {memory_path}/identity/constraints.md — non-negotiables (if mentioned)\n"
        f"      {memory_path}/identity/preferences.md — working style (if mentioned)\n"
        f"      {memory_path}/systems/infrastructure.md — technical setup (if mentioned)\n"
        "      Then tell the user what you've learned and saved — conversationally, not a report.\n"
        "   b) Technical file (code, config, data, logs):\n"
        "      Help with what they need. Ask if the intent isn't clear.\n"
        "   c) Something else: use good judgement.\n"
    )


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
