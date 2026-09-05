"""
tests/pipeline/test_unit_of_work_connection_modes.py
========================================================
Hostile-review blocker #11: proves SQLiteUnitOfWork.commit()/rollback() work correctly
in BOTH connection modes -- db_path-owned (self._conn) and shared_connection (self._shared_conn)
-- after the fix to the guard that previously only checked self._conn, silently no-op'ing
commit/rollback for shared connections and leaving _in_transaction permanently True.

Why Campaign A touched this file: the P7A.6 REST API test suite needed a SQLite connection
usable safely from FastAPI TestClient's background anyio thread (check_same_thread=False),
which requires shared_connection mode -- the first real exercise of that mode anywhere in
the repo (confirmed by a repo-wide grep before the fix: zero non-test production or test
callers used shared_connection with a real connection). The bug was pre-existing and
dormant, not introduced by Campaign A.
"""

from __future__ import annotations

import sqlite3
import tempfile

import pytest

from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


def test_db_path_owned_mode_commits_and_allows_sequential_transactions(db_path):
    """Path-owned mode (self._conn): repeated `with uow:` blocks must each succeed."""
    uow = SQLiteUnitOfWork(db_path=db_path)
    with uow:
        uow.connection.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        uow.connection.execute("INSERT INTO t (v) VALUES ('a')")
    with uow:
        uow.connection.execute("INSERT INTO t (v) VALUES ('b')")
    with uow:
        rows = uow.connection.execute("SELECT v FROM t ORDER BY id").fetchall()
    assert [r["v"] for r in rows] == ["a", "b"]
    uow.close()


def test_db_path_owned_mode_rollback_on_exception_discards_changes(db_path):
    uow = SQLiteUnitOfWork(db_path=db_path)
    with uow:
        uow.connection.execute("CREATE TABLE t2 (id INTEGER PRIMARY KEY, v TEXT)")
    try:
        with uow:
            uow.connection.execute("INSERT INTO t2 (v) VALUES ('should-be-rolled-back')")
            raise RuntimeError("simulated failure")
    except RuntimeError:
        pass
    with uow:
        rows = uow.connection.execute("SELECT v FROM t2").fetchall()
    assert rows == []
    uow.close()


def test_shared_connection_mode_commits_and_allows_sequential_transactions(db_path):
    """
    Shared-connection mode (self._shared_conn): this is the exact scenario the bug broke --
    a second `with uow:` block used to raise 'cannot start a transaction within a transaction'
    because commit() silently no-op'd (guarded on self._conn, which stays None in this mode)
    and _in_transaction was never cleared.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    uow = SQLiteUnitOfWork(db_path=db_path, shared_connection=conn)

    with uow:
        uow.connection.execute("CREATE TABLE t3 (id INTEGER PRIMARY KEY, v TEXT)")
        uow.connection.execute("INSERT INTO t3 (v) VALUES ('x')")
    with uow:
        uow.connection.execute("INSERT INTO t3 (v) VALUES ('y')")
    with uow:
        uow.connection.execute("INSERT INTO t3 (v) VALUES ('z')")
    with uow:
        rows = uow.connection.execute("SELECT v FROM t3 ORDER BY id").fetchall()

    assert [r["v"] for r in rows] == ["x", "y", "z"]
    conn.close()


def test_shared_connection_mode_rollback_on_exception_discards_changes_and_clears_flag(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    uow = SQLiteUnitOfWork(db_path=db_path, shared_connection=conn)

    with uow:
        uow.connection.execute("CREATE TABLE t4 (id INTEGER PRIMARY KEY, v TEXT)")
    try:
        with uow:
            uow.connection.execute("INSERT INTO t4 (v) VALUES ('should-be-rolled-back')")
            raise RuntimeError("simulated failure")
    except RuntimeError:
        pass

    # The bug's exact failure mode: _in_transaction stuck True after rollback would make
    # this next `with uow:` raise "cannot start a transaction within a transaction".
    with uow:
        rows = uow.connection.execute("SELECT v FROM t4").fetchall()
    assert rows == []
    conn.close()


def test_shared_connection_is_not_closed_by_uow_close(db_path):
    """UnitOfWork.close() must never close a connection it doesn't own."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    uow = SQLiteUnitOfWork(db_path=db_path, shared_connection=conn)
    with uow:
        uow.connection.execute("CREATE TABLE t5 (id INTEGER PRIMARY KEY)")
    uow.close()
    # Connection must still be usable -- proves close() didn't close a shared connection.
    conn.execute("SELECT 1")
    conn.close()


def test_db_path_owned_connection_is_closed_by_uow_close(db_path):
    """The inverse: a UoW-owned connection SHOULD be closed by close()."""
    uow = SQLiteUnitOfWork(db_path=db_path)
    with uow:
        uow.connection.execute("CREATE TABLE t6 (id INTEGER PRIMARY KEY)")
    owned_conn = uow.connection
    uow.close()
    with pytest.raises(sqlite3.ProgrammingError):
        owned_conn.execute("SELECT 1")


def test_commit_no_ops_safely_when_not_in_a_transaction(db_path):
    """Calling commit()/rollback() outside any `with uow:` block must not raise."""
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.commit()  # no-op, not in a transaction
    uow.rollback()  # no-op, not in a transaction
    uow.close()
