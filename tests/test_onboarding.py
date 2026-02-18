"""Tests for the onboarding flow (S2.5)."""

import json
from pathlib import Path

import pytest

from hive.agent.onboarding import OnboardingFlow, PHASES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_flow(tmp_path: Path) -> tuple[Path, OnboardingFlow]:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    return memory_dir, OnboardingFlow(memory_dir)


def run_all_phases(flow: OnboardingFlow) -> None:
    """Drive the flow through all 4 phases with non-skip answers."""
    flow.start()
    # Phase 1: name, role, languages, constraints
    flow.handle_response("Alex")
    flow.handle_response("Builder")
    flow.handle_response("Python, Docker")
    flow.handle_response("Never delete production data")
    # Phase 2: infrastructure, installed_tools
    flow.handle_response("VPS at 10.0.0.1")
    flow.handle_response("Docker, Python 3.12")
    # Phase 3: project_name, project_objective
    flow.handle_response("hive-office")
    flow.handle_response("Build the AI agent system")
    # Phase 4: communication_style, autonomy_level
    flow.handle_response("Direct and terse")
    flow.handle_response("Ask for destructive actions, decide otherwise")


# ---------------------------------------------------------------------------
# is_active
# ---------------------------------------------------------------------------

class TestIsActive:
    def test_inactive_before_start(self, tmp_path):
        _, flow = make_flow(tmp_path)
        assert flow.is_active() is False

    def test_active_after_start(self, tmp_path):
        _, flow = make_flow(tmp_path)
        flow.start()
        assert flow.is_active() is True

    def test_inactive_after_completion(self, tmp_path):
        _, flow = make_flow(tmp_path)
        run_all_phases(flow)
        assert flow.is_active() is False

    def test_active_state_persists_across_instances(self, tmp_path):
        memory_dir, flow1 = make_flow(tmp_path)
        flow1.start()
        # New instance reads same state file
        flow2 = OnboardingFlow(memory_dir)
        assert flow2.is_active() is True


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------

class TestStart:
    def test_returns_welcome_and_first_question(self, tmp_path):
        _, flow = make_flow(tmp_path)
        result = flow.start()
        assert "Phase 1" in result
        assert "name" in result.lower() or "what" in result.lower()

    def test_start_creates_state_file(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        flow.start()
        assert (memory_dir / ".onboarding_state.json").exists()

    def test_start_resets_state_when_called_again(self, tmp_path):
        _, flow = make_flow(tmp_path)
        flow.start()
        flow.handle_response("Alex")  # advance one step
        flow.start()  # restart
        # Should be back at phase_index=0, question_index=0
        state_file = (tmp_path / "memory" / ".onboarding_state.json")
        state = json.loads(state_file.read_text())
        assert state["phase_index"] == 0
        assert state["question_index"] == 0

    def test_start_includes_phase_label(self, tmp_path):
        _, flow = make_flow(tmp_path)
        result = flow.start()
        phase_label = PHASES[0]["label"]
        assert phase_label in result


# ---------------------------------------------------------------------------
# handle_response() — advancing through phases
# ---------------------------------------------------------------------------

class TestHandleResponse:
    def test_first_answer_advances_to_second_question(self, tmp_path):
        _, flow = make_flow(tmp_path)
        flow.start()
        result = flow.handle_response("Alex")
        # Next question should be about role
        assert "role" in result.lower() or "do you do" in result.lower()

    def test_skip_moves_to_next_question(self, tmp_path):
        _, flow = make_flow(tmp_path)
        flow.start()
        flow.handle_response("Alex")  # name
        flow.handle_response("Builder")  # role
        flow.handle_response("Python")  # languages
        result = flow.handle_response("/skip")  # skip constraints
        # Should now be in phase 2
        assert "Phase 2" in result or "infrastructure" in result.lower()

    def test_phase_transition_shows_phase_header(self, tmp_path):
        _, flow = make_flow(tmp_path)
        flow.start()
        flow.handle_response("Alex")
        flow.handle_response("Builder")
        flow.handle_response("Python")
        result = flow.handle_response("Never delete prod")
        assert "Phase 2" in result

    def test_completion_returns_welcome_message(self, tmp_path):
        memory_dir = tmp_path / "mem2"
        memory_dir.mkdir()
        flow = OnboardingFlow(memory_dir)
        flow.start()
        flow.handle_response("Alex")
        flow.handle_response("Builder")
        flow.handle_response("Python")
        flow.handle_response("No constraints")
        flow.handle_response("VPS")
        flow.handle_response("Docker")
        flow.handle_response("my-project")
        flow.handle_response("Build stuff")
        flow.handle_response("Direct")
        result = flow.handle_response("Ask first")
        assert "complete" in result.lower() or "welcome" in result.lower()

    def test_handle_response_when_not_active_returns_error(self, tmp_path):
        _, flow = make_flow(tmp_path)
        result = flow.handle_response("hello")
        assert "not active" in result.lower() or "/onboard" in result


# ---------------------------------------------------------------------------
# File writing — Phase 1
# ---------------------------------------------------------------------------

class TestPhase1Writes:
    def test_name_written_to_user_md(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        flow.start()
        flow.handle_response("Alex")
        user_md = memory_dir / "identity" / "user.md"
        assert user_md.exists()
        assert "Alex" in user_md.read_text()

    def test_role_written_to_user_md(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        flow.start()
        flow.handle_response("Alex")
        flow.handle_response("Software Builder")
        user_md = memory_dir / "identity" / "user.md"
        assert "Software Builder" in user_md.read_text()

    def test_languages_written_to_user_md(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        flow.start()
        flow.handle_response("Alex")
        flow.handle_response("Builder")
        flow.handle_response("Python, TypeScript")
        user_md = memory_dir / "identity" / "user.md"
        assert "Python, TypeScript" in user_md.read_text()

    def test_constraints_written_to_constraints_md(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        flow.start()
        flow.handle_response("Alex")
        flow.handle_response("Builder")
        flow.handle_response("Python")
        flow.handle_response("Never delete prod")
        constraints_md = memory_dir / "identity" / "constraints.md"
        assert constraints_md.exists()
        assert "Never delete prod" in constraints_md.read_text()

    def test_skip_constraints_does_not_write_file(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        flow.start()
        flow.handle_response("Alex")
        flow.handle_response("Builder")
        flow.handle_response("Python")
        flow.handle_response("/skip")
        # constraints.md should not exist (no content written)
        constraints_md = memory_dir / "identity" / "constraints.md"
        assert not constraints_md.exists()


# ---------------------------------------------------------------------------
# Phase 3 — project creation
# ---------------------------------------------------------------------------

class TestPhase3Project:
    def _reach_phase3(self, flow: OnboardingFlow) -> None:
        """Drive through phases 1 and 2."""
        flow.start()
        # Phase 1
        flow.handle_response("Alex")
        flow.handle_response("Builder")
        flow.handle_response("Python")
        flow.handle_response("/skip")
        # Phase 2
        flow.handle_response("/skip")
        flow.handle_response("/skip")

    def test_project_dir_created(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        self._reach_phase3(flow)
        flow.handle_response("hive-office")
        assert (memory_dir / "projects" / "hive-office").is_dir()

    def test_active_project_marker_set(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        self._reach_phase3(flow)
        flow.handle_response("hive-office")
        marker = memory_dir / ".active_project"
        assert marker.exists()
        assert marker.read_text().strip() == "hive-office"

    def test_project_name_sanitised(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        self._reach_phase3(flow)
        flow.handle_response("My Cool Project!")
        # Should be sanitised to "my-cool-project"
        assert (memory_dir / "projects" / "my-cool-project").is_dir()

    def test_project_objective_written_to_working_memory(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        self._reach_phase3(flow)
        flow.handle_response("hive-office")
        flow.handle_response("Build the AI agent system")
        wm = memory_dir / "projects" / "hive-office" / "working_memory.yaml"
        assert wm.exists()
        assert "Build the AI agent system" in wm.read_text()

    def test_skip_project_name_skips_entire_phase_3(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        self._reach_phase3(flow)
        result = flow.handle_response("/skip")
        # Should jump to phase 4, not ask for project_objective
        assert "Phase 4" in result
        assert not (memory_dir / ".active_project").exists()

    def test_standard_project_files_created(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        self._reach_phase3(flow)
        flow.handle_response("my-project")
        project_dir = memory_dir / "projects" / "my-project"
        for filename in ["decisions.md", "blockers.md", "todos.md", "changelog.md"]:
            assert (project_dir / filename).exists(), f"{filename} missing"


# ---------------------------------------------------------------------------
# Resumability
# ---------------------------------------------------------------------------

class TestResumability:
    def test_onboarding_resumes_from_saved_state(self, tmp_path):
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()

        # First instance: start and answer 2 questions
        flow1 = OnboardingFlow(memory_dir)
        flow1.start()
        flow1.handle_response("Alex")
        flow1.handle_response("Builder")

        # New instance: should still be active, at phase 1 question 2 (languages)
        flow2 = OnboardingFlow(memory_dir)
        assert flow2.is_active() is True

        result = flow2.handle_response("Python")
        # Should ask next question (constraints)
        assert "constraint" in result.lower() or "never" in result.lower() or "skip" in result.lower()

    def test_answers_accumulate_across_instances(self, tmp_path):
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()

        flow1 = OnboardingFlow(memory_dir)
        flow1.start()
        flow1.handle_response("Alex")

        # user.md should already have name
        user_md = memory_dir / "identity" / "user.md"
        assert "Alex" in user_md.read_text()

        # Continue with new instance
        flow2 = OnboardingFlow(memory_dir)
        flow2.handle_response("Builder")

        # role should be appended
        assert "Builder" in user_md.read_text()


# ---------------------------------------------------------------------------
# Complete onboarding creates all expected files
# ---------------------------------------------------------------------------

class TestCompleteOnboarding:
    def test_all_files_created_after_full_run(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        run_all_phases(flow)

        assert (memory_dir / "identity" / "user.md").exists()
        assert (memory_dir / "identity" / "constraints.md").exists()
        assert (memory_dir / "systems" / "infrastructure.md").exists()
        assert (memory_dir / "systems" / "tools.md").exists()
        assert (memory_dir / ".active_project").exists()
        assert (memory_dir / "projects" / "hive-office" / "working_memory.yaml").exists()
        assert (memory_dir / "identity" / "preferences.md").exists()

    def test_user_md_contains_all_phase1_answers(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        run_all_phases(flow)
        content = (memory_dir / "identity" / "user.md").read_text()
        assert "Alex" in content
        assert "Builder" in content
        assert "Python" in content

    def test_preferences_md_contains_phase4_answers(self, tmp_path):
        memory_dir, flow = make_flow(tmp_path)
        run_all_phases(flow)
        prefs = (memory_dir / "identity" / "preferences.md").read_text()
        assert "Direct" in prefs
        assert "Ask for destructive actions" in prefs
