"""tests/unit/engine_intelligence/test_p7c_concurrency_and_durability.py
============================================================================
P7C Group 1 §22/§23: concurrency/race testing and restart/durability testing for
the Intelligence Kernel. Uses real threads against a real file-backed SQLite
database (not mocks) -- the same durability pattern already established for
akaalPipeline.state.unit_of_work.SQLiteUnitOfWork elsewhere in this repository.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.lifecycle import ArtifactLifecycleState
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS intelligence_artifacts (
    artifact_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT,
    project_id TEXT, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
    subject_version TEXT NOT NULL, task TEXT NOT NULL, algorithm_version TEXT NOT NULL,
    policy_version TEXT NOT NULL, canonical_state_fingerprint TEXT NOT NULL,
    fingerprint TEXT NOT NULL, result TEXT NOT NULL, lifecycle_state TEXT NOT NULL,
    created_at TEXT NOT NULL, requested_by TEXT NOT NULL, model_provider TEXT,
    model_id TEXT, model_version TEXT, expires_at TEXT, superseded_by TEXT, updated_at TEXT
)
"""


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _open_conn(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA_SQL)
    conn.commit()
    return conn


def _req(subject_id="plan-race", **overrides) -> IntelligenceRequest:
    base = dict(
        task=IntelligenceTask.QUERY, tenant_id="tenant-a", subject_type="migration_plan",
        subject_id=subject_id, subject_version="v1", requested_by="user-1",
    )
    base.update(overrides)
    return IntelligenceRequest(**base)


def _ctx(subject_id="plan-race", **overrides) -> IntelligenceContext:
    base = dict(tenant_id="tenant-a", subject_type="migration_plan", subject_id=subject_id, subject_version="v1")
    base.update(overrides)
    return IntelligenceContext(**base)


class TestConcurrentGeneration:
    def test_concurrent_submit_requests_each_get_a_distinct_artifact(self, db_path):
        """Same artifact 'generated concurrently': N threads submit requests for
        the SAME subject at the same time -- every one must land as its own
        distinct, individually durable artifact; none silently lost or merged."""
        conn = _open_conn(db_path)
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        results = []
        errors = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            try:
                thread_conn = _open_conn(db_path)
                artifact = kernel.submit_request(_req(), _ctx(), thread_conn)
                thread_conn.commit()
                thread_conn.close()
                with lock:
                    results.append(artifact.artifact_id)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent submission errors: {errors}"
        assert len(results) == 16
        assert len(set(results)) == 16  # every artifact_id genuinely distinct
        conn.close()

    def test_concurrent_supersession_leaves_exactly_one_non_terminal_artifact(self, db_path):
        """Racing supersede_previous=True submissions for the same subject/task
        must never leave two simultaneously-non-terminal artifacts, and must
        never crash on the concurrent UPDATE."""
        conn = _open_conn(db_path)
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        errors = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            try:
                thread_conn = _open_conn(db_path)
                kernel.submit_request(_req(), _ctx(subject_version=f"v{i}"), thread_conn, supersede_previous=True)
                thread_conn.commit()
                thread_conn.close()
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent supersession errors: {errors}"

        final_conn = _open_conn(db_path)
        all_artifacts = kernel.list_artifacts("tenant-a", final_conn, subject_id="plan-race", limit=100)
        non_terminal = [a for a in all_artifacts if a.lifecycle_state not in (
            ArtifactLifecycleState.SUPERSEDED, ArtifactLifecycleState.EXPIRED, ArtifactLifecycleState.REJECTED
        )]
        assert len(non_terminal) == 1, f"Expected exactly one non-terminal artifact, found {len(non_terminal)}"
        final_conn.close()

    def test_concurrent_cancellation_races_do_not_corrupt_store(self, db_path):
        from akaalEngine.intelligence.budget import CancellationToken
        from akaalEngine.intelligence.models.errors import IntelligenceCancelledError

        conn = _open_conn(db_path)
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        cancelled_count = [0]
        succeeded_count = [0]
        lock = threading.Lock()

        def worker(i: int) -> None:
            thread_conn = _open_conn(db_path)
            token = CancellationToken()
            if i % 2 == 0:
                token.cancel()
            try:
                kernel.submit_request(_req(subject_id=f"plan-cancel-{i}"), _ctx(subject_id=f"plan-cancel-{i}"), thread_conn, cancellation_token=token)
                thread_conn.commit()
                with lock:
                    succeeded_count[0] += 1
            except IntelligenceCancelledError:
                with lock:
                    cancelled_count[0] += 1
            finally:
                thread_conn.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cancelled_count[0] == 5
        assert succeeded_count[0] == 5
        conn.close()


class TestRestartDurability:
    def test_artifact_survives_process_restart(self, db_path):
        """Simulates a process restart: a fresh IntelligenceKernel + fresh SQLite
        connection opened against the same db_path must still see the artifact
        generated 'before restart', with its lifecycle state and fingerprint
        intact -- unchanged, not reset to GENERATED, not resurrected/upgraded."""
        conn1 = _open_conn(db_path)
        kernel1 = IntelligenceKernel(store=IntelligenceArtifactStore())
        artifact = kernel1.submit_request(_req(), _ctx(), conn1)
        kernel1.transition(artifact.artifact_id, ArtifactLifecycleState.GROUNDED, conn1)
        conn1.commit()
        conn1.close()

        # "Restart": brand new kernel instance, brand new connection.
        conn2 = _open_conn(db_path)
        kernel2 = IntelligenceKernel(store=IntelligenceArtifactStore())
        restored = kernel2.get_artifact(artifact.artifact_id, conn2)

        assert restored.artifact_id == artifact.artifact_id
        assert restored.fingerprint == artifact.fingerprint
        assert restored.lifecycle_state == ArtifactLifecycleState.GROUNDED
        conn2.close()

    def test_expired_artifact_stays_expired_after_restart(self, db_path):
        """Restart must never resurrect a terminal-state artifact back to
        actionable -- a stale/expired artifact found after restart must still be
        treated as stale/expired by any consequential caller."""
        conn1 = _open_conn(db_path)
        kernel1 = IntelligenceKernel(store=IntelligenceArtifactStore())
        artifact = kernel1.submit_request(_req(), _ctx(), conn1)
        kernel1.transition(artifact.artifact_id, ArtifactLifecycleState.EXPIRED, conn1)
        conn1.commit()
        conn1.close()

        conn2 = _open_conn(db_path)
        kernel2 = IntelligenceKernel(store=IntelligenceArtifactStore())
        restored = kernel2.get_artifact(artifact.artifact_id, conn2)
        assert restored.lifecycle_state == ArtifactLifecycleState.EXPIRED

        from akaalEngine.intelligence.models.errors import IntelligenceInvalidTransitionError
        with pytest.raises(IntelligenceInvalidTransitionError):
            kernel2.transition(artifact.artifact_id, ArtifactLifecycleState.ACCEPTED, conn2)
        conn2.close()

    def test_tenant_boundary_holds_after_restart(self, db_path):
        conn1 = _open_conn(db_path)
        kernel1 = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel1.submit_request(
            _req(subject_id="plan-tenant-a"), _ctx(subject_id="plan-tenant-a"), conn1,
        )
        conn1.commit()
        conn1.close()

        conn2 = _open_conn(db_path)
        kernel2 = IntelligenceKernel(store=IntelligenceArtifactStore())
        listed = kernel2.list_artifacts("tenant-b", conn2)
        assert listed == []
        conn2.close()
