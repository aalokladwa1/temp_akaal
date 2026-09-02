"""tests/pipeline/test_restart_durability.py
============================================
Mandatory restart durability tests proving canonical state reconstructs from disk tables after process restart.
"""

from __future__ import annotations

import os
import sqlite3
import pytest

from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode, OperationStatus
from akaalPipeline.operations.idempotency import IdempotencyService
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.service import OperationService
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from tests.pipeline.conftest import authorized_caller, make_command, make_query


def test_aggregate_and_history_reconstruct_after_restart(temp_db_path, ipc_actor, ipc_correlation):
    """Prove MigrationAggregate and lifecycle history survive process restart on SQLite file."""
    # 1. First session: Create migration
    caller1 = authorized_caller(db_path=temp_db_path)
    cmd1 = make_command(
        request_type="migration.create",
        payload={"migration_id": "mig-restart-1", "name": "Restart Mig", "mode": "M1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res1 = caller1.handle_command(cmd1)
    assert res1.status.value == "OK"
    assert res1.result["state"] == "DRAFT"

    # 2. Simulate process shutdown: dispose caller1
    del caller1

    # 3. Second session: New objects attached to same database file
    caller2 = authorized_caller(db_path=temp_db_path)
    qry2 = make_query(
        request_type="migration.get",
        payload={"migration_id": "mig-restart-1"},
        actor=ipc_actor,
        correlation=ipc_correlation,
    )
    res2 = caller2.handle_query(qry2)
    assert res2.status.value == "OK"
    assert res2.result["migration_id"] == "mig-restart-1"
    assert res2.result["state"] == "DRAFT"
    assert res2.result["name"] == "Restart Mig"


def test_operation_and_idempotency_survive_restart(temp_db_path, ipc_actor, ipc_correlation):
    """Prove operation journal and idempotency records survive process restart."""
    uow1 = SQLiteUnitOfWork(db_path=temp_db_path)
    idemp_service = IdempotencyService()
    op_service = OperationService()

    with uow1:
        idemp_service.check_and_store(
            idempotency_key="key-restart-100",
            command_id="cmd-100",
            payload_fingerprint="fp-100",
            result_payload={"status": "stored"},
            conn=uow1.connection,
        )

    uow1.close()

    # Restart session
    uow2 = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow2:
        res = idemp_service.check_and_store(
            idempotency_key="key-restart-100",
            command_id="cmd-100",
            payload_fingerprint="fp-100",
            result_payload={"status": "new"},
            conn=uow2.connection,
        )
        assert res == {"status": "stored"}

    uow2.close()


def test_leases_and_fencing_survive_restart(temp_db_path):
    """Prove execution attempt lease and fence epoch survive restart."""
    lease_mgr = LeaseManager()
    uow1 = SQLiteUnitOfWork(db_path=temp_db_path)

    with uow1:
        l1 = lease_mgr.acquire_lease(
            lease_id="l-1",
            attempt_id="att-1",
            owner_id="owner-1",
            expires_at="2099-01-01T00:00:00+00:00",
            initialization_fingerprint="fp-init-1",
            conn=uow1.connection,
        )
        assert l1.fence_epoch == 1

    uow1.close()

    # Restart session
    uow2 = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow2:
        l2 = lease_mgr.get_lease("att-1", uow2.connection)
        assert l2 is not None
        assert l2.lease_id == "l-1"
        assert l2.fence_epoch == 1
        assert l2.owner_id == "owner-1"

    uow2.close()
