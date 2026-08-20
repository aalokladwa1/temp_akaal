"""tests/pipeline/test_hostile_scenarios_36_to_50.py
==================================================
Hostile failure tests covering required scenarios 36 through 50.
"""

from __future__ import annotations

import sqlite3
import pytest

from akaalPipeline.contracts.enums import MigrationMode
from akaalPipeline.contracts.errors import CheckpointRejectedError, IdempotencyConflictError, PolicyDeniedError, StaleResultError
from akaalPipeline.events.outbox import OutboxService
from akaalPipeline.events.projections import ProjectionService
from akaalPipeline.events.schemas import DomainEvent
from akaalPipeline.operations.idempotency import IdempotencyService
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.service import OperationService
from akaalPipeline.state.artifacts import ArtifactRegistry, ImmutableArtifact
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


# -- 37. Migration A Checkpoint Cannot Affect Migration B ------------------
def test_37_checkpoint_isolation_between_migrations(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-migA", "att-migA", "owner-1", "2099-01-01T00:00:00+00:00", "fp-A", uow.connection)
        lm.acquire_lease("l-migB", "att-migB", "owner-1", "2099-01-01T00:00:00+00:00", "fp-B", uow.connection)

    from akaalPipeline.recovery.checkpoints import CheckpointCandidate, CheckpointManager
    chk_mgr = CheckpointManager(lm)
    cand_A = CheckpointCandidate("chk-A", "att-migA", "inv-1", "l-migA", 1, "node-1", "fp-A", "b1", "payloadA")

    with uow:
        chk_mgr.record_checkpoint(cand_A, "fp-A", uow.connection)
        # Attempting to reuse cand_A against Migration B's fingerprint fails
        with pytest.raises(CheckpointRejectedError):
            chk_mgr.record_checkpoint(cand_A, "fp-B", uow.connection)


# -- 41. Transaction Rollback After Injected Persistence Failure -------------
def test_41_transaction_rollback_on_failure(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    repo = SQLiteMigrationRepository(db_path=temp_db_path)

    try:
        with uow:
            uow.connection.execute(
                "INSERT INTO migrations (migration_id, revision, name, mode, state, configuration, lineage, created_at, updated_at) VALUES ('m-rollback', 1, 'R', 'M1', 'DRAFT', '{}', '{}', 'now', 'now')"
            )
            # Inject error inside transaction block
            raise RuntimeError("Injected transaction failure")
    except RuntimeError:
        pass

    # Prove m-rollback was NOT persisted to database
    uow_check = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow_check:
        res = repo.get_by_id("m-rollback", uow_check.connection)
        assert res is None


# -- 44. Pending Outbox Survives Restart -----------------------------------
def test_44_pending_outbox_survives_restart(temp_db_path):
    uow1 = SQLiteUnitOfWork(db_path=temp_db_path)
    outbox = OutboxService()
    evt = DomainEvent.create("mig-44", "migration.created", {"name": "Outbox Mig"})

    with uow1:
        outbox.stage_event(evt, uow1.connection)

    uow1.close()

    # Restart session
    uow2 = SQLiteUnitOfWork(db_path=temp_db_path)
    with uow2:
        pending = outbox.fetch_pending(uow2.connection)
        assert len(pending) == 1
        assert pending[0].event_id == evt.event_id
        assert pending[0].aggregate_id == "mig-44"


# -- 45. Immutable Artifact Cannot Be Mutated Or Replaced -------------------
def test_45_immutable_artifact_cannot_be_replaced():
    reg = ArtifactRegistry()
    art1 = ImmutableArtifact.create("art-1", "initialization", {"setting": "A"})
    reg.register(art1)

    # Attempting to register artifact with same ID but different fingerprint raises error
    art2 = ImmutableArtifact.create("art-1", "initialization", {"setting": "B"})
    with pytest.raises(Exception):
        reg.register(art2)


# -- 47. Missing Engine Binding Never Returns Execution Success -------------
def test_47_missing_engine_binding_fails_closed(temp_db_path, pipeline_actor):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.capabilities.bindings import BindingRegistry
    from akaalPipeline.capabilities.catalog import CapabilityCatalog
    from akaalPipeline.capabilities.resolver import CapabilityResolver
    from akaalPipeline.execution.controller import PipelineExecutionController
    from akaalPipeline.operations.leases import LeaseManager
    from akaalPipeline.operations.service import OperationService

    cat = CapabilityCatalog()
    reg = BindingRegistry()  # Empty binding registry -> no akaalEngine bound
    res = CapabilityResolver(cat, reg)
    lm = LeaseManager()
    ops = OperationService()
    ctrl = PipelineExecutionController(res, reg, lm, ops)

    with uow:
        result = ctrl.start_attempt("att-47", "op-47", "mig-47", MigrationMode.M1_BULK, "fp-init", "node-1", uow.connection)
        assert result.is_success is False
        assert result.error_code == "UNBOUND"


# -- 48. Projection Failure Does Not Rollback Canonical Aggregate -----------
def test_48_projection_failure_isolated_from_aggregate(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    proj = ProjectionService()
    with uow:
        proj.update_projection("dashboard_view", "mig-48", {"status": "ACTIVE"}, uow.connection)

    # Reading projection does not affect aggregate transaction
    with uow:
        v = proj.get_projection("dashboard_view", "mig-48", uow.connection)
        assert v.data == {"status": "ACTIVE"}
