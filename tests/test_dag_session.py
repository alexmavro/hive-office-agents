"""Tests for hive.session.dag — DagSession JSONL tree session."""

import os
import tempfile
import pytest

from hive.session.dag import DagSession, MessageEntry, CompactionEntry


# ---------------------------------------------------------------------------
# Basic append and path traversal
# ---------------------------------------------------------------------------


def test_in_memory_append_and_get_path():
    dag = DagSession.in_memory()
    assert dag.get_path() == []
    assert dag.message_count == 0

    id1 = dag.append("user", "Hello")
    id2 = dag.append("assistant", "Hi there")
    id3 = dag.append("user", "How are you?")

    path = dag.get_path()
    assert len(path) == 3
    assert path[0].id == id1
    assert path[1].id == id2
    assert path[2].id == id3
    assert dag.get_leaf_id() == id3


def test_parent_chain():
    dag = DagSession.in_memory()
    id1 = dag.append("user", "A")
    id2 = dag.append("assistant", "B")
    id3 = dag.append("user", "C")

    assert dag.get_entry(id1).parent_id is None
    assert dag.get_entry(id2).parent_id == id1
    assert dag.get_entry(id3).parent_id == id2


def test_message_count():
    dag = DagSession.in_memory()
    assert dag.message_count == 0
    dag.append("user", "one")
    assert dag.message_count == 1
    dag.append("assistant", "two")
    assert dag.message_count == 2


def test_empty_session():
    dag = DagSession.in_memory()
    assert dag.get_path() == []
    assert dag.build_context() == []
    assert dag.get_leaf_id() is None
    assert dag.get_leaf_entry() is None


# ---------------------------------------------------------------------------
# build_context — no compaction
# ---------------------------------------------------------------------------


def test_build_context_no_compaction():
    dag = DagSession.in_memory()
    dag.append("user", "Hello")
    dag.append("assistant", "Hi")
    dag.append("user", "Tell me something")

    ctx = dag.build_context()
    assert ctx == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "Tell me something"},
    ]


# ---------------------------------------------------------------------------
# Compaction
# ---------------------------------------------------------------------------


def test_build_context_with_compaction():
    dag = DagSession.in_memory()
    dag.append("user", "msg1")
    dag.append("assistant", "msg2")
    id3 = dag.append("user", "msg3")   # first_kept_entry_id
    dag.append("assistant", "msg4")

    # Compact: summarize msg1 + msg2, keep from msg3 onward
    dag.compact(
        summary="User asked about msg1, assistant replied with msg2.",
        first_kept_entry_id=id3,
    )

    dag.append("user", "msg5")

    ctx = dag.build_context()

    # Should start with compaction summary, then msg3 onward
    assert ctx[0]["role"] == "system"
    assert "msg1" in ctx[0]["content"]
    assert ctx[1] == {"role": "user", "content": "msg3"}
    assert ctx[2] == {"role": "assistant", "content": "msg4"}
    assert ctx[3] == {"role": "user", "content": "msg5"}
    assert len(ctx) == 4


def test_compaction_entry_on_path():
    dag = DagSession.in_memory()
    dag.append("user", "a")
    dag.append("assistant", "b")
    id_kept = dag.append("user", "c")
    compact_id = dag.compact(summary="summary of a,b", first_kept_entry_id=id_kept)

    path = dag.get_path()
    # path should include compaction entry
    types = [type(e).__name__ for e in path]
    assert "CompactionEntry" in types
    assert dag.get_entry(compact_id) is not None


# ---------------------------------------------------------------------------
# Branching
# ---------------------------------------------------------------------------


def test_branch():
    dag = DagSession.in_memory()
    id1 = dag.append("user", "start")
    id2 = dag.append("assistant", "response A")
    id3 = dag.append("user", "follow-up A")  # branch A tip

    # Branch back to id1, then grow a different path
    dag.branch(id1)
    id4 = dag.append("assistant", "response B")
    id5 = dag.append("user", "follow-up B")  # branch B tip

    # Branch B path should only contain branch B nodes
    path_b = dag.get_path()
    ids_b = {e.id for e in path_b}
    assert id1 in ids_b
    assert id4 in ids_b
    assert id5 in ids_b
    assert id2 not in ids_b
    assert id3 not in ids_b

    # Branch A path reachable via explicit leaf_id
    path_a = dag.get_path(leaf_id=id3)
    ids_a = {e.id for e in path_a}
    assert id1 in ids_a
    assert id2 in ids_a
    assert id3 in ids_a
    assert id4 not in ids_a

    # All 5 entries exist in the session
    assert len(dag.get_entries()) == 5


def test_branch_raises_on_unknown_id():
    dag = DagSession.in_memory()
    with pytest.raises(KeyError):
        dag.branch("nonexistent_id")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_persist_and_reload():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "session.jsonl")

        # Write session
        dag = DagSession.create(cwd=tmpdir, path=path)
        id1 = dag.append("user", "persisted message")
        id2 = dag.append("assistant", "persisted reply")

        # Reload
        dag2 = DagSession.open(path)
        assert dag2.message_count == 2
        assert dag2.get_leaf_id() == id2

        path2 = dag2.get_path()
        assert path2[0].id == id1
        assert path2[1].id == id2
        assert isinstance(path2[0], MessageEntry)
        assert path2[0].content == "persisted message"
        assert path2[1].content == "persisted reply"


def test_persist_compaction_and_reload():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "session_compact.jsonl")

        dag = DagSession.create(cwd=tmpdir, path=path)
        dag.append("user", "old1")
        dag.append("assistant", "old2")
        id_kept = dag.append("user", "kept1")
        dag.compact(summary="old1 and old2 summarized", first_kept_entry_id=id_kept)
        dag.append("assistant", "kept2")

        dag2 = DagSession.open(path)
        ctx = dag2.build_context()
        assert ctx[0]["role"] == "system"
        assert "old1" in ctx[0]["content"]
        assert ctx[1]["content"] == "kept1"
        assert ctx[2]["content"] == "kept2"


def test_get_children():
    dag = DagSession.in_memory()
    id1 = dag.append("user", "root")
    id2 = dag.append("assistant", "child A")
    dag.branch(id1)
    id3 = dag.append("assistant", "child B")

    children = {e.id for e in dag.get_children(id1)}
    assert id2 in children
    assert id3 in children


def test_tools_used_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "tools.jsonl")
        dag = DagSession.create(cwd=tmpdir, path=path)
        dag.append("user", "do something")
        dag.append("assistant", "done", tools_used=["exec", "read_file"])

        dag2 = DagSession.open(path)
        path2 = dag2.get_path()
        assert path2[1].tools_used == ["exec", "read_file"]
