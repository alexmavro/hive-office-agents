"""Tests for the onboarding flow (S2.5 — LLM-driven redesign).

The onboarding flow is now LLM-driven: /onboard injects a mission prompt
into the LLM conversation instead of running a rigid state machine.
OnboardingFlow is a thin wrapper that:
  - is_active() always returns False (no message interception)
  - start() returns the onboarding mission prompt for the LLM
"""

from pathlib import Path

import pytest

from hive.agent.onboarding import OnboardingFlow, get_onboarding_prompt, get_document_intake_prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_flow(tmp_path: Path) -> tuple[Path, OnboardingFlow]:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(exist_ok=True)
    return memory_dir, OnboardingFlow(memory_dir)


# ---------------------------------------------------------------------------
# is_active — always False (no interception in LLM-driven design)
# ---------------------------------------------------------------------------

class TestIsActive:
    def test_inactive_before_start(self, tmp_path):
        _, flow = make_flow(tmp_path)
        assert flow.is_active() is False

    def test_still_inactive_after_start(self, tmp_path):
        """LLM-driven: start() returns a prompt, never sets blocking state."""
        _, flow = make_flow(tmp_path)
        flow.start()
        assert flow.is_active() is False

    def test_two_instances_both_inactive(self, tmp_path):
        memory_dir, flow1 = make_flow(tmp_path)
        flow1.start()
        flow2 = OnboardingFlow(memory_dir)
        assert flow2.is_active() is False


# ---------------------------------------------------------------------------
# start() — returns the LLM mission prompt
# ---------------------------------------------------------------------------

class TestStart:
    def test_returns_non_empty_string(self, tmp_path):
        _, flow = make_flow(tmp_path)
        result = flow.start()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_result_contains_user_md_path(self, tmp_path):
        _, flow = make_flow(tmp_path)
        result = flow.start()
        assert "user.md" in result

    def test_result_contains_constraints_md_path(self, tmp_path):
        _, flow = make_flow(tmp_path)
        result = flow.start()
        assert "constraints.md" in result

    def test_result_contains_preferences_md_path(self, tmp_path):
        _, flow = make_flow(tmp_path)
        result = flow.start()
        assert "preferences.md" in result

    def test_result_mentions_write_file(self, tmp_path):
        _, flow = make_flow(tmp_path)
        result = flow.start()
        assert "write_file" in result

    def test_result_instructs_to_start(self, tmp_path):
        _, flow = make_flow(tmp_path)
        result = flow.start()
        assert "start" in result.lower() or "question" in result.lower()

    def test_start_twice_is_idempotent(self, tmp_path):
        """Calling start() twice returns the same prompt (no state side effects)."""
        _, flow = make_flow(tmp_path)
        result1 = flow.start()
        result2 = flow.start()
        assert result1 == result2

    def test_state_file_attribute_exists(self, tmp_path):
        """state_file attribute kept for factory_reset compatibility."""
        memory_dir, flow = make_flow(tmp_path)
        assert flow.state_file == memory_dir / ".onboarding_state.json"


# ---------------------------------------------------------------------------
# get_onboarding_prompt()
# ---------------------------------------------------------------------------

class TestGetOnboardingPrompt:
    def test_prompt_contains_memory_path(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        result = get_onboarding_prompt(workspace)
        expected_path = str(workspace / "memory")
        assert expected_path in result

    def test_prompt_mentions_infrastructure(self, tmp_path):
        result = get_onboarding_prompt(tmp_path)
        assert "infrastructure" in result.lower()

    def test_prompt_mentions_constraints(self, tmp_path):
        result = get_onboarding_prompt(tmp_path)
        assert "constraint" in result.lower() or "never" in result.lower()

    def test_prompt_covers_project(self, tmp_path):
        result = get_onboarding_prompt(tmp_path)
        assert "project" in result.lower()

    def test_prompt_asks_for_interpretation_not_verbatim(self, tmp_path):
        result = get_onboarding_prompt(tmp_path)
        assert "verbatim" in result.lower() or "interpret" in result.lower()

    def test_prompt_mentions_active_project_marker(self, tmp_path):
        result = get_onboarding_prompt(tmp_path)
        assert ".active_project" in result


# ---------------------------------------------------------------------------
# get_document_intake_prompt()
# ---------------------------------------------------------------------------

class TestGetDocumentIntakePrompt:
    def test_includes_file_paths(self, tmp_path):
        paths = ["/root/.hive/media/abc_cv.pdf"]
        result = get_document_intake_prompt(paths, tmp_path)
        assert "/root/.hive/media/abc_cv.pdf" in result

    def test_includes_multiple_file_paths(self, tmp_path):
        paths = ["/root/.hive/media/abc_cv.pdf", "/root/.hive/media/def_brand.pdf"]
        result = get_document_intake_prompt(paths, tmp_path)
        assert all(p in result for p in paths)

    def test_mentions_read_file(self, tmp_path):
        result = get_document_intake_prompt(["/some/file.pdf"], tmp_path)
        assert "read_file" in result

    def test_mentions_write_file(self, tmp_path):
        result = get_document_intake_prompt(["/some/file.pdf"], tmp_path)
        assert "write_file" in result

    def test_mentions_user_md_path(self, tmp_path):
        result = get_document_intake_prompt(["/some/file.txt"], tmp_path)
        assert "user.md" in result

    def test_includes_user_text_when_provided(self, tmp_path):
        result = get_document_intake_prompt(["/some/file.pdf"], tmp_path, user_text="Here's my CV")
        assert "Here's my CV" in result

    def test_no_user_text_section_when_empty(self, tmp_path):
        result = get_document_intake_prompt(["/some/file.pdf"], tmp_path, user_text="")
        assert 'also wrote: ""' not in result

    def test_mentions_pdf_fallback(self, tmp_path):
        result = get_document_intake_prompt(["/some/file.pdf"], tmp_path)
        assert "pdftotext" in result

    def test_singular_vs_plural_label(self, tmp_path):
        single = get_document_intake_prompt(["/a.pdf"], tmp_path)
        multi = get_document_intake_prompt(["/a.pdf", "/b.pdf"], tmp_path)
        assert "a file" in single
        assert "files" in multi
