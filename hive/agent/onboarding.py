"""Onboarding flow for new users (/onboard command).

State machine design:
  - 4 phases, each with hardcoded questions
  - State persisted in memory/.onboarding_state.json
  - Answers written immediately to memory files as given
  - /skip is accepted for any question to skip it
  - Phase 3 (active project) is skipped entirely if project_name is /skip'd
  - NOT an LLM conversation — pure structured intake
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Question definitions
# ---------------------------------------------------------------------------

PHASES = [
    {
        "id": "phase_1",
        "label": "About You",
        "questions": [
            {
                "key": "name",
                "prompt": "What's your name?",
                "target": "identity/user.md",
                "prefix": "**Name:** ",
            },
            {
                "key": "role",
                "prompt": "What do you do? (one sentence — role or job title)",
                "target": "identity/user.md",
                "prefix": "**Role:** ",
            },
            {
                "key": "languages",
                "prompt": "What languages / tools do you work with? (e.g. Python, Docker, TypeScript)",
                "target": "identity/user.md",
                "prefix": "**Languages:** ",
            },
            {
                "key": "constraints",
                "prompt": "Any absolute constraints — things I should never do? (or /skip)",
                "target": "identity/constraints.md",
                "prefix": "- ",
            },
        ],
    },
    {
        "id": "phase_2",
        "label": "Your Infrastructure",
        "questions": [
            {
                "key": "infrastructure",
                "prompt": "What infrastructure am I managing? (e.g. VPS at 10.0.0.1, local Mac, AWS — or /skip)",
                "target": "systems/infrastructure.md",
                "prefix": "**Infrastructure:** ",
            },
            {
                "key": "installed_tools",
                "prompt": "What's installed on the main system? (e.g. Docker, Python 3.12, Postgres — or /skip)",
                "target": "systems/tools.md",
                "prefix": "**Tools:** ",
            },
        ],
    },
    {
        "id": "phase_3",
        "label": "Active Project",
        "questions": [
            {
                "key": "project_name",
                "prompt": 'What are you working on right now? (project name, e.g. "hive-office" — or /skip)',
                "target": None,  # handled specially via _create_project()
                "prefix": None,
            },
            {
                "key": "project_objective",
                "prompt": "Main objective for this project? (one sentence)",
                "target": None,  # handled specially via _write_project_objective()
                "prefix": None,
            },
        ],
    },
    {
        "id": "phase_4",
        "label": "Working Style",
        "questions": [
            {
                "key": "communication_style",
                "prompt": "How should I communicate with you? (e.g. direct and terse, formal, explain your reasoning)",
                "target": "identity/preferences.md",
                "prefix": "**Communication style:** ",
            },
            {
                "key": "autonomy_level",
                "prompt": "When should I ask for permission vs decide autonomously?",
                "target": "identity/preferences.md",
                "prefix": "**Autonomy:** ",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# OnboardingFlow
# ---------------------------------------------------------------------------

class OnboardingFlow:
    """4-phase structured intake flow.

    Callers:
        flow.start()                → welcome message + first question
        flow.handle_response(text)  → saves answer, returns next question / completion
        flow.is_active()            → True while a session is in progress
    """

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.state_file = memory_dir / ".onboarding_state.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_active(self) -> bool:
        """Return True if onboarding is in progress (started but not complete)."""
        state = self._load_state()
        return state.get("active", False) and not state.get("complete", False)

    def start(self) -> str:
        """Initialise (or restart) onboarding. Returns the first question."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "active": True,
            "complete": False,
            "phase_index": 0,
            "question_index": 0,
            "answers": {},
        }
        self._save_state(state)
        phase = PHASES[0]
        first_q = phase["questions"][0]
        return (
            "Starting onboarding — takes about 5 minutes.\n\n"
            f"**Phase 1/4: {phase['label']}**\n\n"
            f"{first_q['prompt']}"
        )

    def handle_response(self, text: str) -> str:
        """Process a user answer. Writes to memory files and returns the next prompt."""
        state = self._load_state()
        if not state.get("active") or state.get("complete"):
            return "Onboarding is not active. Send /onboard to start."

        phase_idx = state["phase_index"]
        q_idx = state["question_index"]
        question = self._get_question(phase_idx, q_idx)
        if question is None:
            return "Onboarding completed."

        is_skip = text.strip().lower() in ("/skip", "skip")

        if not is_skip:
            state["answers"][question["key"]] = text.strip()
            self._write_answer(question, text.strip(), state)

        next_text = self._advance(state, phase_idx, q_idx, is_skip)
        self._save_state(state)
        return next_text

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _advance(self, state: dict, phase_idx: int, q_idx: int, was_skipped: bool) -> str:
        """Move state forward. Returns the next prompt text."""
        phase = PHASES[phase_idx]
        questions = phase["questions"]

        # Phase 3 special rule: if project_name is skipped, skip the entire phase
        if (
            phase["id"] == "phase_3"
            and questions[q_idx]["key"] == "project_name"
            and was_skipped
        ):
            next_phase_idx = phase_idx + 1
            if next_phase_idx >= len(PHASES):
                return self._complete(state)
            state["phase_index"] = next_phase_idx
            state["question_index"] = 0
            return self._phase_header(next_phase_idx) + self._get_question(next_phase_idx, 0)["prompt"]

        # Normal advance: next question within current phase
        next_q_idx = q_idx + 1
        if next_q_idx < len(questions):
            state["question_index"] = next_q_idx
            return self._get_question(phase_idx, next_q_idx)["prompt"]

        # End of phase: move to next phase
        next_phase_idx = phase_idx + 1
        if next_phase_idx >= len(PHASES):
            return self._complete(state)
        state["phase_index"] = next_phase_idx
        state["question_index"] = 0
        return self._phase_header(next_phase_idx) + self._get_question(next_phase_idx, 0)["prompt"]

    def _phase_header(self, phase_idx: int) -> str:
        phase = PHASES[phase_idx]
        return f"\n**Phase {phase_idx + 1}/4: {phase['label']}**\n\n"

    def _complete(self, state: dict) -> str:
        state["active"] = False
        state["complete"] = True
        name = state["answers"].get("name", "")
        greeting = f"Welcome, {name}!" if name else "Setup complete!"
        return (
            f"{greeting} Onboarding complete.\n\n"
            "Your profile has been saved to memory/identity/. "
            "I'm ready to work.\n\n"
            "You can update any details by editing the files in your memory/ directory "
            "or by running /onboard again to restart."
        )

    # ------------------------------------------------------------------
    # File writers
    # ------------------------------------------------------------------

    def _write_answer(self, question: dict, value: str, state: dict) -> None:
        """Write one answer to the appropriate memory file."""
        key = question["key"]

        # Phase 3 special handling
        if key == "project_name":
            self._create_project(value, state)
            return
        if key == "project_objective":
            self._write_project_objective(value, state)
            return

        target = question.get("target")
        prefix = question.get("prefix", "")
        if not target:
            return

        filepath = self.memory_dir / target
        filepath.parent.mkdir(parents=True, exist_ok=True)
        line = f"{prefix}{value}\n"

        if filepath.exists() and filepath.stat().st_size > 0:
            with filepath.open("a", encoding="utf-8") as f:
                f.write(line)
        else:
            filepath.write_text(line, encoding="utf-8")

    def _create_project(self, project_name: str, state: dict) -> None:
        """Create project directory and set .active_project marker."""
        safe_name = re.sub(r"[^\w\-]", "-", project_name.lower().strip())
        safe_name = re.sub(r"-+", "-", safe_name).strip("-") or "my-project"
        state["answers"]["_project_safe_name"] = safe_name

        project_dir = self.memory_dir / "projects" / safe_name
        project_dir.mkdir(parents=True, exist_ok=True)

        for filename in ["decisions.md", "blockers.md", "todos.md", "changelog.md"]:
            f = project_dir / filename
            if not f.exists():
                f.write_text(f"# {filename.replace('.md', '').title()}\n", encoding="utf-8")

        (self.memory_dir / ".active_project").write_text(safe_name, encoding="utf-8")

    def _write_project_objective(self, objective: str, state: dict) -> None:
        """Write working_memory.yaml for the active project."""
        safe_name = (
            state["answers"].get("_project_safe_name")
            or state["answers"].get("project_name", "my-project")
        )
        project_dir = self.memory_dir / "projects" / safe_name
        project_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        content = (
            f"project: {safe_name}\n"
            f"objective: {objective}\n"
            f"status: active\n"
            f"created: {now}\n"
        )
        (project_dir / "working_memory.yaml").write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_question(self, phase_idx: int, q_idx: int) -> dict | None:
        if phase_idx >= len(PHASES):
            return None
        questions = PHASES[phase_idx]["questions"]
        if q_idx >= len(questions):
            return None
        return questions[q_idx]

    def _load_state(self) -> dict:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_state(self, state: dict) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )
