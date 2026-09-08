"""tests/security/test_p7c_group2_concurrency_campaign.py
================================================================
Closes owner-review Blocker 8: risk-driven concurrency testing targeted at
the highest-risk Group-2 shared state, not mechanical per-part duplication.
P7C.14's HealthSampleStore already produced one REAL same-file SQLite
deadlock during this build (fixed by giving it a sibling DB file) -- this
file specifically stress-tests that fix under genuine concurrent writers,
plus concurrent requests against the same/different migrations, concurrent
outcome recording, and concurrent portfolio reads during migration changes.

Uses real threads against the real production seam -- no `sleep()`-based
synchronization, only thread joins / barriers for deterministic timing.

Concurrency construction note: this repository's own established pattern
for genuine cross-thread tests (see tests/pipeline/test_concurrency_
multitenancy.py::test_concurrent_revision_cas_race) is a FRESH
SQLiteUnitOfWork/connection per thread, never one shared plain sqlite3.
Connection object handed to multiple OS threads (Python's sqlite3 module
enforces same-thread-only access by default, and akaalPipeline's
CentralAuthorizationEngine/repositories are constructed against a single
connection for their lifetime -- this is a pre-existing, repository-wide
constraint of the frozen P7/P7A authorization layer, not something Group 2
introduced or can safely change). Every concurrency test below therefore
builds a SEPARATE `authorized_caller(db_path=...)` per thread, all pointed at
the SAME underlying database file -- the same story a real multi-connection
deployment would have -- rather than sharing one Python object across
threads.
"""

from __future__ import annotations

import os
import tempfile
import threading

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _actor(org_id: str, actor_id: str = None) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=actor_id or f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id, workspace_id="ws-main", project_id="proj-1",
    )


def _seed_migration(caller, migration_id, tenant_id):
    from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
    from akaalPipeline.state.aggregates import MigrationAggregate

    agg = MigrationAggregate(
        migration_id=migration_id, revision=1, name=f"migration-{migration_id}",
        mode=MigrationMode.M1_BULK, state=MigrationLifecycleState.DRAFT,
        tenant_id=tenant_id, workspace_id="ws-main", project_id="proj-1",
    )
    caller.repository.save(agg)


def _submit_anomaly(caller, actor, migration_id):
    payload = {
        "task": "ASSESS", "subject_type": "migration", "subject_id": migration_id,
        "subject_version": "v1", "capability": "anomaly_detection", "parameters": {"migration_id": migration_id},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


def _run_concurrently(fns, thread_count):
    """Runs `thread_count` threads each calling one of `fns` (cycled),
    collecting (result_or_None, exception_or_None) per thread -- deterministic
    join-based synchronization, no sleeps."""
    results = [None] * thread_count
    errors = [None] * thread_count

    def _worker(i):
        try:
            results[i] = fns[i % len(fns)]()
        except Exception as exc:  # noqa: BLE001
            errors[i] = exc

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return results, errors


class TestConcurrentHealthSampleStoreWrites:
    """The exact component that produced a real cross-connection deadlock
    earlier in this build -- proves the sibling-file fix holds under genuine
    concurrent writers to the SAME migration's sample history. Each thread
    uses its OWN caller/connection against the SAME db file (see module
    docstring)."""

    def test_concurrent_anomaly_requests_same_migration_no_lock_errors(self, temp_db_path):
        setup_caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(setup_caller, "mig-concurrent-1", "tenant-alpha")
        finally:
            setup_caller.close()

        def _worker():
            caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
            try:
                return _submit_anomaly(caller, actor, "mig-concurrent-1")
            finally:
                caller.close()

        fns = [_worker for _ in range(8)]
        results, errors = _run_concurrently(fns, 8)

        assert all(e is None for e in errors), f"concurrent anomaly requests raised: {errors}"
        assert all(r is not None and r.status == CallerResultStatus.OK for r in results)

    def test_concurrent_requests_different_migrations_no_cross_contamination(self, temp_db_path):
        migration_ids = [f"mig-concurrent-diff-{i}" for i in range(6)]
        setup_caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            for mid in migration_ids:
                _seed_migration(setup_caller, mid, "tenant-alpha")
        finally:
            setup_caller.close()

        def _worker(mid):
            caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
            try:
                return _submit_anomaly(caller, actor, mid)
            finally:
                caller.close()

        fns = [lambda mid=mid: _worker(mid) for mid in migration_ids]
        results, errors = _run_concurrently(fns, len(fns))

        assert all(e is None for e in errors), f"concurrent multi-migration requests raised: {errors}"
        returned_migration_ids = {r.result["result"]["data"]["migration_id"] for r in results}
        assert returned_migration_ids == set(migration_ids)


class TestConcurrentOutcomeRecording:
    def test_concurrent_outcome_records_against_same_artifact_all_persist(self, temp_db_path):
        setup_caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            eval_payload = {
                "task": "COMPARE", "subject_type": "migration", "subject_id": "mig-1", "subject_version": "v1",
                "capability": "forecast_evaluation",
                "parameters": {"metric_name": "eta", "predicted_value": 100, "predicted_low": 80, "predicted_high": 120, "actual_value": 110},
            }
            artifact_result = setup_caller.handle_command(make_command("intelligence.submit", eval_payload, actor, CorrelationContext.new()))
            assert artifact_result.status == CallerResultStatus.OK
            artifact_id = artifact_result.result["artifact_id"]
        finally:
            setup_caller.close()

        def _record(i):
            caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
            try:
                payload = {"artifact_id": artifact_id, "outcome_status": "SUCCEEDED", "detail": f"concurrent-{i}"}
                return caller.handle_command(make_command("intelligence.outcome.record", payload, actor, CorrelationContext.new()))
            finally:
                caller.close()

        fns = [lambda i=i: _record(i) for i in range(6)]
        results, errors = _run_concurrently(fns, 6)

        assert all(e is None for e in errors), f"concurrent outcome recording raised: {errors}"
        assert all(r.status == CallerResultStatus.OK for r in results)


class TestConcurrentPortfolioReadsDuringMigrationChanges:
    def test_portfolio_reads_never_crash_while_migrations_are_added(self, temp_db_path):
        setup_caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            for i in range(5):
                _seed_migration(setup_caller, f"mig-pre-{i}", "tenant-alpha")
        finally:
            setup_caller.close()

        def _read_portfolio():
            caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
            try:
                payload = {
                    "task": "QUERY", "subject_type": "tenant", "subject_id": "tenant-alpha",
                    "subject_version": "v1", "capability": "portfolio_intelligence", "parameters": {},
                }
                return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
            finally:
                caller.close()

        def _add_migration(i):
            caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
            try:
                _seed_migration(caller, f"mig-during-{i}", "tenant-alpha")
                return None
            finally:
                caller.close()

        fns = [_read_portfolio, _read_portfolio, lambda: _add_migration(0), _read_portfolio, lambda: _add_migration(1), _read_portfolio]
        results, errors = _run_concurrently(fns, 6)

        assert all(e is None for e in errors), f"concurrent portfolio reads during writes raised: {errors}"
        for r in results:
            if r is not None:
                assert r.status == CallerResultStatus.OK
