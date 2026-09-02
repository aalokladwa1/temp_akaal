"""tests/pipeline/test_concurrency_multitenancy.py
=============================================
Mandatory concurrency and multitenancy isolation tests.
"""

from __future__ import annotations

import threading
import pytest

from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
from akaalPipeline.contracts.errors import RevisionConflictError, UnableToAcquireLeaseError
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from tests.pipeline.conftest import authorized_caller, make_command, make_query


def test_multi_migration_tenant_isolation(temp_db_path, ipc_actor, ipc_correlation):
    """Prove two independent migrations for different tenants operate concurrently without state leak."""
    caller = authorized_caller(db_path=temp_db_path)

    cmd_tenant1 = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-t1", "name": "Tenant 1 Mig", "mode": "M1"},
        actor=ipc_actor,  # org-acme
        correlation=ipc_correlation,
    )
    res1 = caller.handle_command(cmd_tenant1)
    assert res1.status.value == "OK"

    cmd_tenant2 = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-t2", "name": "Tenant 2 Mig", "mode": "M2"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res2 = caller.handle_command(cmd_tenant2)
    assert res2.status.value == "OK"

    # Both migrations exist independently in store
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow:
        m1 = caller.repository.get_by_id("mig-t1", uow.connection)
        m2 = caller.repository.get_by_id("mig-t2", uow.connection)

        assert m1.migration_id == "mig-t1"
        assert m1.mode == MigrationMode.M1_BULK

        assert m2.migration_id == "mig-t2"
        assert m2.mode == MigrationMode.M2_BULK_CDC


def test_concurrent_revision_cas_race(temp_db_path):
    """Prove concurrent attempts to update the same aggregate revision result in exactly one winner and one RevisionConflictError."""
    repo = SQLiteMigrationRepository(db_path=temp_db_path)
    agg = MigrationAggregate(
        migration_id="mig-cas-1",
        revision=1,
        name="CAS Test",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
    )
    repo.save(agg)

    barrier = threading.Barrier(2)
    results = []

    def worker_update(worker_id: int):
        barrier.wait()
        uow = SQLiteUnitOfWork(db_path=temp_db_path)
        try:
            with uow:
                item = repo.get_by_id("mig-cas-1", uow.connection)
                item.update_configuration({"worker": worker_id}, expected_revision=1)
                repo.save(item, uow.connection)
                results.append((worker_id, "SUCCESS"))
        except RevisionConflictError as rce:
            results.append((worker_id, "REVISION_CONFLICT"))
        except Exception as ex:
            results.append((worker_id, f"ERROR: {ex}"))
        finally:
            uow.close()

    t1 = threading.Thread(target=worker_update, args=(1,))
    t2 = threading.Thread(target=worker_update, args=(2,))

    t1.start()
    t2.start()

    t1.join(timeout=5)
    t2.join(timeout=5)

    successes = [r for r in results if r[1] == "SUCCESS"]
    conflicts = [r for r in results if r[1] == "REVISION_CONFLICT"]

    assert len(successes) == 1, f"Expected exactly 1 CAS winner, got {results}"
    assert len(conflicts) == 1, f"Expected exactly 1 CAS conflict, got {results}"


def test_concurrent_attempt_lease_race(temp_db_path):
    """Prove two contenders racing for the same execution attempt lease result in exactly one owner winning."""
    lease_mgr = LeaseManager()
    uow_init = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow_init:
        # Pre-seed active unexpired lease for owner-A
        lease_mgr.acquire_lease(
            lease_id="l-owner-A",
            attempt_id="att-race-1",
            owner_id="owner-A",
            expires_at="2099-01-01T00:00:00+00:00",
            initialization_fingerprint="fp-init",
            conn=uow_init.connection,
        )
    uow_init.close()

    # Contender B attempts to acquire active lease
    uow_b = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow_b:
        with pytest.raises(UnableToAcquireLeaseError):
            lease_mgr.acquire_lease(
                lease_id="l-owner-B",
                attempt_id="att-race-1",
                owner_id="owner-B",
                expires_at="2099-01-01T00:00:00+00:00",
                initialization_fingerprint="fp-init",
                conn=uow_b.connection,
            )
    uow_b.close()
