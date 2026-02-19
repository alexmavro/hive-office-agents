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
        "The user has typed /onboard. Conduct a warm, conversational intake interview "
        "to build a profile of who they are and how they want to work with you. "
        "Ask 1-2 questions at a time — never dump all questions at once. "
        "Cover these topics in a natural order:\n"
        "  1. Their name and what they do (role/company)\n"
        "  2. Absolute constraints — things you must NEVER do\n"
        "  3. Their infrastructure (servers, cloud, local machine)\n"
        "  4. The project they're currently working on\n"
        "  5. Working style — how they want you to communicate and when to ask vs decide\n\n"
        "As you learn each fact, immediately save it using write_file — write clear, "
        "structured summaries (NOT verbatim quotes; interpret and organise the info):\n"
        f"  {memory_path}/identity/user.md — name, role, context\n"
        f"  {memory_path}/identity/constraints.md — never-do rules as a bullet list\n"
        f"  {memory_path}/identity/preferences.md — communication style, autonomy level\n"
        f"  {memory_path}/systems/infrastructure.md — servers, cloud, tools installed\n\n"
        "If they name an active project:\n"
        f"  Create {memory_path}/projects/<name>/ with decisions.md, todos.md, blockers.md\n"
        f"  Write {memory_path}/projects/<name>/working_memory.yaml with their objective\n"
        f"  Write {memory_path}/.active_project with just the project name on one line\n\n"
        "Start now: greet the user and ask your first question."
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
