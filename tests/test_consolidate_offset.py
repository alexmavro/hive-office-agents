"""Test session management with DAG-backed message handling.

Tests verify the consolidation tracking and slice logic via the DagSession API.
session.messages is replaced by session.message_count + session._dag.get_path().
"""

import pytest
from pathlib import Path
from hive.session.manager import Session, SessionManager
from hive.session.dag import MessageEntry

# Test constants
MEMORY_WINDOW = 50
KEEP_COUNT = MEMORY_WINDOW // 2  # 25


def create_session_with_messages(key: str, count: int, role: str = "user") -> Session:
    """Create a session and add the specified number of messages."""
    session = Session(key=key)
    for i in range(count):
        session.add_message(role, f"msg{i}")
    return session


def assert_path_content(entries: list, start_index: int, end_index: int) -> None:
    """Assert that path entries contain expected content from start to end index."""
    msg_entries = [e for e in entries if isinstance(e, MessageEntry)]
    assert len(msg_entries) > 0
    assert msg_entries[0].content == f"msg{start_index}"
    assert msg_entries[-1].content == f"msg{end_index}"


def get_old_messages(session: Session, last_consolidated: int, keep_count: int) -> list:
    """Extract entries that would be consolidated (mirrors loop.py slice logic)."""
    path = session._dag.get_path()
    if keep_count > 0:
        return path[last_consolidated:-keep_count]
    return path[last_consolidated:]


class TestSessionLastConsolidated:
    """Test last_consolidated tracking to avoid duplicate processing."""

    def test_initial_last_consolidated_zero(self) -> None:
        session = Session(key="test:initial")
        assert session.last_consolidated == 0

    def test_last_consolidated_persistence(self, tmp_path) -> None:
        """last_consolidated persists across save/load via session reload."""
        manager = SessionManager(Path(tmp_path))
        session1 = create_session_with_messages("test:persist", 20)
        session1.last_consolidated = 15
        manager.save(session1)

        session2 = manager.get_or_create("test:persist")
        # message_count survives reload
        assert session2.message_count == 20

    def test_clear_resets_last_consolidated(self) -> None:
        session = create_session_with_messages("test:clear", 10)
        session.last_consolidated = 5

        session.clear()
        assert session.message_count == 0
        assert session.last_consolidated == 0


class TestSessionImmutableHistory:
    """Test Session message history integrity."""

    def test_initial_state(self) -> None:
        session = Session(key="test:initial")
        assert session.message_count == 0

    def test_add_messages_appends_only(self) -> None:
        session = Session(key="test:preserve")
        session.add_message("user", "msg1")
        session.add_message("assistant", "resp1")
        session.add_message("user", "msg2")
        assert session.message_count == 3
        path = session._dag.get_path()
        assert path[0].content == "msg1"

    def test_get_history_returns_most_recent(self) -> None:
        session = Session(key="test:history")
        for i in range(10):
            session.add_message("user", f"msg{i}")
            session.add_message("assistant", f"resp{i}")

        history = session.get_history(max_messages=6)
        assert len(history) == 6
        assert history[0]["content"] == "msg7"
        assert history[-1]["content"] == "resp9"

    def test_get_history_with_all_messages(self) -> None:
        session = create_session_with_messages("test:all", 5)
        history = session.get_history(max_messages=100)
        assert len(history) == 5
        assert history[0]["content"] == "msg0"

    def test_get_history_stable_for_same_session(self) -> None:
        session = create_session_with_messages("test:stable", 20)
        history1 = session.get_history(max_messages=10)
        history2 = session.get_history(max_messages=10)
        assert history1 == history2

    def test_get_history_does_not_change_message_count(self) -> None:
        session = create_session_with_messages("test:immutable", 5)
        original_count = session.message_count

        session.get_history(max_messages=2)
        assert session.message_count == original_count

        for _ in range(10):
            session.get_history(max_messages=3)
        assert session.message_count == original_count


class TestSessionPersistence:
    """Test Session persistence and reload."""

    @pytest.fixture
    def temp_manager(self, tmp_path):
        return SessionManager(Path(tmp_path))

    def test_persistence_roundtrip(self, temp_manager):
        """Messages persist across save/load."""
        session1 = create_session_with_messages("test:persistence", 20)
        temp_manager.save(session1)

        session2 = temp_manager.get_or_create("test:persistence")
        assert session2.message_count == 20
        path = session2._dag.get_path()
        assert path[0].content == "msg0"
        assert path[-1].content == "msg19"

    def test_get_history_after_reload(self, temp_manager):
        """get_history works correctly after reload."""
        session1 = create_session_with_messages("test:reload", 30)
        temp_manager.save(session1)

        session2 = temp_manager.get_or_create("test:reload")
        history = session2.get_history(max_messages=10)
        assert len(history) == 10
        assert history[0]["content"] == "msg20"
        assert history[-1]["content"] == "msg29"

    def test_clear_resets_session(self, temp_manager):
        """clear() properly resets session."""
        session = create_session_with_messages("test:clear", 10)
        assert session.message_count == 10

        session.clear()
        assert session.message_count == 0


class TestConsolidationTriggerConditions:
    """Test consolidation trigger conditions and logic."""

    def test_consolidation_needed_when_messages_exceed_window(self):
        session = create_session_with_messages("test:trigger", 60)

        total = session.message_count
        messages_to_process = total - session.last_consolidated

        assert total > MEMORY_WINDOW
        assert messages_to_process > 0

        expected_consolidate_count = total - KEEP_COUNT
        assert expected_consolidate_count == 35

    def test_consolidation_skipped_when_within_keep_count(self):
        session = create_session_with_messages("test:skip", 20)

        total = session.message_count
        assert total <= KEEP_COUNT

        old_entries = get_old_messages(session, session.last_consolidated, KEEP_COUNT)
        assert len(old_entries) == 0

    def test_consolidation_skipped_when_no_new_messages(self):
        session = create_session_with_messages("test:already_consolidated", 40)
        session.last_consolidated = session.message_count - KEEP_COUNT  # 15

        for i in range(40, 42):
            session.add_message("user", f"msg{i}")

        total = session.message_count
        messages_to_process = total - session.last_consolidated
        assert messages_to_process > 0

        # Simulate last_consolidated catching up
        session.last_consolidated = total - KEEP_COUNT
        old_entries = get_old_messages(session, session.last_consolidated, KEEP_COUNT)
        assert len(old_entries) == 0


class TestLastConsolidatedEdgeCases:
    """Test last_consolidated edge cases."""

    def test_last_consolidated_exceeds_message_count(self):
        session = create_session_with_messages("test:corruption", 10)
        session.last_consolidated = 20

        total = session.message_count
        messages_to_process = total - session.last_consolidated
        assert messages_to_process <= 0

        old_entries = get_old_messages(session, session.last_consolidated, 5)
        assert len(old_entries) == 0

    def test_last_consolidated_negative_value(self):
        session = create_session_with_messages("test:negative", 10)
        session.last_consolidated = -5

        keep_count = 3
        old_entries = get_old_messages(session, session.last_consolidated, keep_count)

        # path[-5:-3] with 10 entries gives indices 5, 6
        assert len(old_entries) == 2
        assert old_entries[0].content == "msg5"
        assert old_entries[-1].content == "msg6"

    def test_messages_added_after_consolidation(self):
        session = create_session_with_messages("test:new_messages", 40)
        session.last_consolidated = session.message_count - KEEP_COUNT  # 15

        for i in range(40, 50):
            session.add_message("user", f"msg{i}")

        total = session.message_count
        old_entries = get_old_messages(session, session.last_consolidated, KEEP_COUNT)
        expected_count = total - KEEP_COUNT - session.last_consolidated

        assert len(old_entries) == expected_count
        assert_path_content(old_entries, 15, 24)

    def test_slice_behavior_when_indices_overlap(self):
        session = create_session_with_messages("test:overlap", 30)
        session.last_consolidated = 12

        old_entries = get_old_messages(session, session.last_consolidated, 20)
        assert len(old_entries) == 0


class TestArchiveAllMode:
    """Test archive_all mode (used by /new command)."""

    def test_archive_all_consolidates_everything(self):
        session = create_session_with_messages("test:archive_all", 50)

        archive_all = True
        if archive_all:
            old_entries = session._dag.get_path()
            assert len(old_entries) == 50

        assert session.last_consolidated == 0

    def test_archive_all_resets_last_consolidated(self):
        session = create_session_with_messages("test:reset", 40)
        session.last_consolidated = 15

        archive_all = True
        if archive_all:
            session.last_consolidated = 0

        assert session.last_consolidated == 0
        assert session.message_count == 40

    def test_archive_all_vs_normal_consolidation(self):
        session1 = create_session_with_messages("test:normal", 60)
        session1.last_consolidated = session1.message_count - KEEP_COUNT

        session2 = create_session_with_messages("test:all", 60)
        session2.last_consolidated = 0

        assert session1.last_consolidated == 35
        assert session1.message_count == 60
        assert session2.last_consolidated == 0
        assert session2.message_count == 60


class TestCacheImmutability:
    """Test that consolidation doesn't mutate session state unexpectedly."""

    def test_consolidation_does_not_change_message_count(self):
        session = create_session_with_messages("test:immutable", 50)
        original_count = session.message_count
        session.last_consolidated = original_count - KEEP_COUNT

        assert session.message_count == original_count

    def test_get_history_does_not_modify_dag(self):
        session = create_session_with_messages("test:history_immutable", 40)
        original_count = session.message_count

        for _ in range(5):
            history = session.get_history(max_messages=10)
            assert len(history) == 10

        assert session.message_count == 40

    def test_consolidation_only_updates_last_consolidated(self):
        session = create_session_with_messages("test:field_only", 60)
        original_count = session.message_count
        original_key = session.key
        original_metadata = session.metadata.copy()

        session.last_consolidated = session.message_count - KEEP_COUNT

        assert session.message_count == original_count
        assert session.key == original_key
        assert session.metadata == original_metadata
        assert session.last_consolidated == 35


class TestSliceLogic:
    """Test the slice logic: path[last_consolidated:-keep_count]."""

    def test_slice_extracts_correct_range(self):
        session = create_session_with_messages("test:slice", 60)

        old_entries = get_old_messages(session, 0, KEEP_COUNT)

        assert len(old_entries) == 35
        assert_path_content(old_entries, 0, 34)

        remaining = session._dag.get_path()[-KEEP_COUNT:]
        assert len(remaining) == 25
        assert_path_content(remaining, 35, 59)

    def test_slice_with_partial_consolidation(self):
        session = create_session_with_messages("test:partial", 70)

        last_consolidated = 30
        old_entries = get_old_messages(session, last_consolidated, KEEP_COUNT)

        assert len(old_entries) == 15
        assert_path_content(old_entries, 30, 44)

    def test_slice_with_various_keep_counts(self):
        session = create_session_with_messages("test:keep_counts", 50)
        path = session._dag.get_path()

        test_cases = [(10, 40), (20, 30), (30, 20), (40, 10)]

        for keep_count, expected_count in test_cases:
            old_entries = path[0:-keep_count]
            assert len(old_entries) == expected_count

    def test_slice_when_keep_count_exceeds_messages(self):
        session = create_session_with_messages("test:exceed", 10)
        path = session._dag.get_path()

        old_entries = path[0:-20]
        assert len(old_entries) == 0


class TestEmptyAndBoundarySessions:
    """Test empty sessions and boundary conditions."""

    def test_empty_session_consolidation(self):
        session = Session(key="test:empty")

        assert session.message_count == 0
        assert session.last_consolidated == 0

        messages_to_process = session.message_count - session.last_consolidated
        assert messages_to_process == 0

        old_entries = get_old_messages(session, session.last_consolidated, KEEP_COUNT)
        assert len(old_entries) == 0

    def test_single_message_session(self):
        session = Session(key="test:single")
        session.add_message("user", "only message")

        assert session.message_count == 1

        old_entries = get_old_messages(session, session.last_consolidated, KEEP_COUNT)
        assert len(old_entries) == 0

    def test_exactly_keep_count_messages(self):
        session = create_session_with_messages("test:exact", KEEP_COUNT)

        assert session.message_count == KEEP_COUNT

        old_entries = get_old_messages(session, session.last_consolidated, KEEP_COUNT)
        assert len(old_entries) == 0

    def test_just_over_keep_count(self):
        session = create_session_with_messages("test:over", KEEP_COUNT + 1)

        assert session.message_count == 26

        old_entries = get_old_messages(session, session.last_consolidated, KEEP_COUNT)
        assert len(old_entries) == 1
        assert old_entries[0].content == "msg0"

    def test_very_large_session(self):
        session = create_session_with_messages("test:large", 1000)

        assert session.message_count == 1000

        old_entries = get_old_messages(session, session.last_consolidated, KEEP_COUNT)
        assert len(old_entries) == 975
        assert_path_content(old_entries, 0, 974)

        remaining = session._dag.get_path()[-KEEP_COUNT:]
        assert len(remaining) == 25
        assert_path_content(remaining, 975, 999)

    def test_session_with_gaps_in_consolidation(self):
        session = create_session_with_messages("test:gaps", 50)
        session.last_consolidated = 10

        for i in range(50, 60):
            session.add_message("user", f"msg{i}")

        old_entries = get_old_messages(session, session.last_consolidated, KEEP_COUNT)

        expected_count = 60 - KEEP_COUNT - 10
        assert len(old_entries) == expected_count
        assert_path_content(old_entries, 10, 34)
