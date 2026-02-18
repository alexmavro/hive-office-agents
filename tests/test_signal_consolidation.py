"""Tests for signal detection and consolidation routing (S2.4)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from hive.agent.consolidation import (
    _register_skill,
    _safe_filename,
    _write_decision,
    consolidate,
    detect_signal,
)
from hive.agent.memory import read_memory_entries
from hive.agent.tools.report_task import ReportTaskTool
from hive.session.manager import Session


# ---------------------------------------------------------------------------
# detect_signal
# ---------------------------------------------------------------------------

class TestDetectSignal:
    def test_success_returns_task_success(self):
        assert detect_signal({"status": "success"}) == "task_success"

    def test_failure_returns_task_failure(self):
        assert detect_signal({"status": "failure"}) == "task_failure"

    def test_correction_returns_correction(self):
        assert detect_signal({"status": "correction"}) == "correction"

    def test_decision_returns_decision(self):
        assert detect_signal({"status": "decision"}) == "decision"

    def test_pattern_returns_pattern(self):
        assert detect_signal({"status": "pattern"}) == "pattern"

    def test_skill_created_returns_new_skill(self):
        assert detect_signal({"status": "skill_created"}) == "new_skill"

    def test_unknown_status_returns_none(self):
        assert detect_signal({"status": "unknown"}) is None

    def test_missing_status_returns_none(self):
        assert detect_signal({}) is None


# ---------------------------------------------------------------------------
# consolidate — decision (sync, no LLM needed)
# ---------------------------------------------------------------------------

class TestConsolidateDecision:
    def test_decision_writes_to_project_decisions(self, tmp_path):
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        # Set active project
        (memory_dir / ".active_project").write_text("my-project")
        project_dir = memory_dir / "projects" / "my-project"
        project_dir.mkdir(parents=True)

        event = {
            "status": "decision",
            "summary": "Chose JSONL over SQLite",
            "task_type": "architecture",
        }
        _write_decision(event, memory_dir)

        decisions_file = project_dir / "decisions.md"
        assert decisions_file.exists()
        entries = read_memory_entries(decisions_file)
        assert len(entries) == 1
        assert "JSONL" in entries[0].content

    def test_decision_falls_back_to_lessons_when_no_active_project(self, tmp_path):
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        # No .active_project file

        event = {
            "status": "decision",
            "summary": "Chose Python over Node",
            "task_type": "tech_choice",
        }
        _write_decision(event, memory_dir)

        fallback = memory_dir / "lessons" / "decisions.md"
        assert fallback.exists()
        entries = read_memory_entries(fallback)
        assert "Python" in entries[0].content


# ---------------------------------------------------------------------------
# consolidate — skill registration (sync, no LLM needed)
# ---------------------------------------------------------------------------

class TestRegisterSkill:
    def test_registers_new_skill(self, tmp_path):
        memory_dir = tmp_path / "memory"
        (memory_dir / "skills").mkdir(parents=True)

        event = {
            "status": "skill_created",
            "task_type": "deploy_docker",
            "summary": "Deploy Docker containers to VPS",
        }
        _register_skill(event, memory_dir)

        registry_path = memory_dir / "skills" / "skills_registry.json"
        assert registry_path.exists()
        registry = json.loads(registry_path.read_text())
        assert len(registry["skills"]) == 1
        assert registry["skills"][0]["name"] == "deploy_docker"

    def test_does_not_duplicate_existing_skill(self, tmp_path):
        memory_dir = tmp_path / "memory"
        (memory_dir / "skills").mkdir(parents=True)

        event = {
            "status": "skill_created",
            "task_type": "deploy_docker",
            "summary": "Deploy Docker containers",
        }
        _register_skill(event, memory_dir)
        _register_skill(event, memory_dir)  # second call

        registry = json.loads(
            (memory_dir / "skills" / "skills_registry.json").read_text()
        )
        assert len(registry["skills"]) == 1  # not duplicated


# ---------------------------------------------------------------------------
# consolidate — async dispatcher (mocked LLM)
# ---------------------------------------------------------------------------

class TestConsolidateDispatcher:
    def _make_session(self) -> Session:
        session = Session(key="test:session")
        return session

    def _make_provider(self, response_text: str) -> MagicMock:
        provider = MagicMock()
        response = MagicMock()
        response.content = response_text
        provider.chat = AsyncMock(return_value=response)
        return provider

    @pytest.mark.asyncio
    async def test_task_failure_writes_to_failures_md(self, tmp_path):
        memory_dir = tmp_path / "memory"
        (memory_dir / "lessons").mkdir(parents=True)

        provider = self._make_provider("## Failure\nDon't retry this approach.")
        session = self._make_session()

        await consolidate(
            signal_type="task_failure",
            event={"status": "failure", "summary": "pip install fails", "task_type": "python", "attempts": 3},
            memory_dir=memory_dir,
            provider=provider,
            model="test-model",
            session=session,
        )

        failures_file = memory_dir / "lessons" / "failures.md"
        assert failures_file.exists()
        entries = read_memory_entries(failures_file)
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_task_success_writes_to_workflows(self, tmp_path):
        memory_dir = tmp_path / "memory"
        (memory_dir / "procedural" / "workflows").mkdir(parents=True)

        provider = self._make_provider("# Deploy Workflow\n## Steps\n1. Build image")
        session = self._make_session()

        await consolidate(
            signal_type="task_success",
            event={"status": "success", "summary": "Deployed service", "task_type": "deploy"},
            memory_dir=memory_dir,
            provider=provider,
            model="test-model",
            session=session,
        )

        workflow_file = memory_dir / "procedural" / "workflows" / "deploy.md"
        assert workflow_file.exists()

    @pytest.mark.asyncio
    async def test_unknown_signal_does_not_crash(self, tmp_path):
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        provider = self._make_provider("")
        session = self._make_session()

        # Should log a warning but not raise
        await consolidate(
            signal_type="unknown_signal",
            event={},
            memory_dir=memory_dir,
            provider=provider,
            model="test-model",
            session=session,
        )

    @pytest.mark.asyncio
    async def test_consolidate_error_does_not_propagate(self, tmp_path):
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()

        provider = MagicMock()
        provider.chat = AsyncMock(side_effect=Exception("LLM unavailable"))
        session = self._make_session()

        # Should catch error internally and not raise
        await consolidate(
            signal_type="task_failure",
            event={"status": "failure", "summary": "something failed"},
            memory_dir=memory_dir,
            provider=provider,
            model="test-model",
            session=session,
        )


# ---------------------------------------------------------------------------
# ReportTaskTool
# ---------------------------------------------------------------------------

class TestReportTaskTool:
    def test_name_and_description(self):
        tool = ReportTaskTool()
        assert tool.name == "report_task"
        assert "report_task" in tool.description.lower() or "signal" in tool.description.lower()

    def test_parameters_schema_has_required_fields(self):
        tool = ReportTaskTool()
        params = tool.parameters
        assert "status" in params["properties"]
        assert "summary" in params["properties"]
        assert "status" in params["required"]
        assert "summary" in params["required"]

    def test_status_enum_has_all_six_types(self):
        tool = ReportTaskTool()
        status_enum = tool.parameters["properties"]["status"]["enum"]
        assert set(status_enum) == {
            "success", "failure", "correction", "decision", "pattern", "skill_created"
        }

    @pytest.mark.asyncio
    async def test_calls_callback_with_event(self):
        received = []

        async def fake_callback(event: dict) -> None:
            received.append(event)

        tool = ReportTaskTool(consolidation_callback=fake_callback)
        result = await tool.execute(
            status="success",
            summary="Task done",
            task_type="deploy",
        )

        assert len(received) == 1
        assert received[0]["status"] == "success"
        assert received[0]["summary"] == "Task done"
        assert "Acknowledged" in result

    @pytest.mark.asyncio
    async def test_works_without_callback(self):
        tool = ReportTaskTool(consolidation_callback=None)
        result = await tool.execute(status="success", summary="Done")
        assert "Acknowledged" in result

    @pytest.mark.asyncio
    async def test_callback_error_does_not_raise(self):
        async def bad_callback(event):
            raise ValueError("oops")

        tool = ReportTaskTool(consolidation_callback=bad_callback)
        # Should not raise — returns error message instead
        result = await tool.execute(status="success", summary="Done")
        assert result  # returns something


# ---------------------------------------------------------------------------
# _safe_filename helper
# ---------------------------------------------------------------------------

class TestSafeFilename:
    def test_spaces_become_underscores(self):
        assert _safe_filename("deploy service") == "deploy_service"

    def test_uppercase_becomes_lowercase(self):
        assert _safe_filename("Deploy") == "deploy"

    def test_special_chars_removed(self):
        assert _safe_filename("deploy!service") == "deployservice"

    def test_empty_returns_general(self):
        assert _safe_filename("") == "general"

    def test_already_clean(self):
        assert _safe_filename("deploy_service") == "deploy_service"
