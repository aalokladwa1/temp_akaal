"""tests/pipeline/test_hostile_corrections_findings_1_to_6.py
==========================================================
Hostile regression test suite proving corrections for Findings 01 through 06.
"""

from __future__ import annotations

import types
import pytest

from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.ids import AttemptId, CheckpointId, ExecutionPlanId, InitializationId, MigrationId, OperationId
from akaalPipeline.contracts.serialization import canonical_fingerprint, canonical_serialize, deep_freeze
from akaalPipeline.contracts.errors import CheckpointRejectedError, StaleResultError
from akaalPipeline.events.schemas import DomainEvent, EngineEventProposal, IntegrationEvent
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.ports.engine import EngineInvocationResult
from akaalPipeline.recovery.checkpoints import CheckpointCandidate, CheckpointManager
from akaalPipeline.state.artifacts import ImmutableArtifact
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


# -- Finding 01: Candidate Initialization Fingerprint Validation -----------------

def test_01_candidate_init_fingerprint_mismatch(temp_db_path):
    """1. Candidate fingerprint differs from canonical lease fingerprint => rejected, zero checkpoint write."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-CANONICAL", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand = CheckpointCandidate(
        checkpoint_id="chk-1",
        attempt_id="att-1",
        engine_invocation_id="inv-1",
        lease_id="l-1",
        fence_epoch=1,
        graph_node_id="node-1",
        initialization_fingerprint="fp-CANDIDATE-MISMATCH",  # Mismatch
        engine_binding="b1",
        checkpoint_payload_reference="payload-ref",
    )

    with uow:
        with pytest.raises(CheckpointRejectedError, match="Candidate initialization fingerprint"):
            chk_mgr.record_checkpoint(cand, "fp-CANONICAL", uow.connection)

        # Verify zero DB rows written
        cur = uow.connection.execute("SELECT COUNT(*) FROM checkpoints")
        assert cur.fetchone()[0] == 0


def test_02_candidate_init_fingerprint_differs_from_stored(temp_db_path):
    """2. Candidate fingerprint matches expected argument but differs from canonical stored fingerprint => rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-STORED-CANONICAL", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand = CheckpointCandidate(
        checkpoint_id="chk-2",
        attempt_id="att-1",
        engine_invocation_id="inv-1",
        lease_id="l-1",
        fence_epoch=1,
        graph_node_id="node-1",
        initialization_fingerprint="fp-ARG",  # matches expected arg, but differs from stored
        engine_binding="b1",
        checkpoint_payload_reference="payload-ref",
    )

    with uow:
        with pytest.raises(CheckpointRejectedError):
            chk_mgr.record_checkpoint(cand, "fp-ARG", uow.connection)


# -- Finding 02: Duplicate Checkpoint Content & Provenance Verification ---------

def test_03_duplicate_checkpoint_identical_content(temp_db_path):
    """3. Duplicate checkpoint ID + identical canonical content => idempotent replay accepted."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand = CheckpointCandidate("chk-dup-1", "att-1", "inv-1", "l-1", 1, "n-1", "fp-1", "b1", "payload-1")

    with uow:
        chk_mgr.record_checkpoint(cand, "fp-1", uow.connection)
        # Duplicate identical record should return without error
        chk_mgr.record_checkpoint(cand, "fp-1", uow.connection)


def test_04_duplicate_checkpoint_different_attempt(temp_db_path):
    """4. Duplicate checkpoint ID + different attempt => rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)
        lm.acquire_lease("l-2", "att-2", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand1 = CheckpointCandidate("chk-dup-diff", "att-1", "inv-1", "l-1", 1, "n-1", "fp-1", "b1", "payload-1")
    cand2 = CheckpointCandidate("chk-dup-diff", "att-2", "inv-1", "l-2", 1, "n-1", "fp-1", "b1", "payload-1")

    with uow:
        chk_mgr.record_checkpoint(cand1, "fp-1", uow.connection)
        with pytest.raises(CheckpointRejectedError, match="conflicting canonical content"):
            chk_mgr.record_checkpoint(cand2, "fp-1", uow.connection)


def test_05_duplicate_checkpoint_different_invocation(temp_db_path):
    """5. Duplicate checkpoint ID + different invocation => rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand1 = CheckpointCandidate("chk-dup-inv", "att-1", "inv-1", "l-1", 1, "n-1", "fp-1", "b1", "payload-1")
    cand2 = CheckpointCandidate("chk-dup-inv", "att-1", "inv-2", "l-1", 1, "n-1", "fp-1", "b1", "payload-1")

    with uow:
        chk_mgr.record_checkpoint(cand1, "fp-1", uow.connection)
        with pytest.raises(CheckpointRejectedError, match="conflicting canonical content"):
            chk_mgr.record_checkpoint(cand2, "fp-1", uow.connection)


def test_06_duplicate_checkpoint_different_lease(temp_db_path):
    """6. Duplicate checkpoint ID + different lease => rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand1 = CheckpointCandidate("chk-dup-lease", "att-1", "inv-1", "l-1", 1, "n-1", "fp-1", "b1", "payload-1")
    cand2 = CheckpointCandidate("chk-dup-lease", "att-1", "inv-1", "l-OTHER", 1, "n-1", "fp-1", "b1", "payload-1")

    with uow:
        chk_mgr.record_checkpoint(cand1, "fp-1", uow.connection)
        with pytest.raises(CheckpointRejectedError):
            chk_mgr.record_checkpoint(cand2, "fp-1", uow.connection)


def test_07_duplicate_checkpoint_different_epoch(temp_db_path):
    """7. Duplicate checkpoint ID + different fence epoch => rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand1 = CheckpointCandidate("chk-dup-epoch", "att-1", "inv-1", "l-1", 1, "n-1", "fp-1", "b1", "payload-1")
    cand2 = CheckpointCandidate("chk-dup-epoch", "att-1", "inv-1", "l-1", 2, "n-1", "fp-1", "b1", "payload-1")

    with uow:
        chk_mgr.record_checkpoint(cand1, "fp-1", uow.connection)
        with pytest.raises(CheckpointRejectedError):
            chk_mgr.record_checkpoint(cand2, "fp-1", uow.connection)


def test_08_duplicate_checkpoint_different_node(temp_db_path):
    """8. Duplicate checkpoint ID + different graph node => rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand1 = CheckpointCandidate("chk-dup-node", "att-1", "inv-1", "l-1", 1, "n-1", "fp-1", "b1", "payload-1")
    cand2 = CheckpointCandidate("chk-dup-node", "att-1", "inv-1", "l-1", 1, "n-99", "fp-1", "b1", "payload-1")

    with uow:
        chk_mgr.record_checkpoint(cand1, "fp-1", uow.connection)
        with pytest.raises(CheckpointRejectedError, match="conflicting canonical content"):
            chk_mgr.record_checkpoint(cand2, "fp-1", uow.connection)


def test_09_duplicate_checkpoint_different_init_fp(temp_db_path):
    """9. Duplicate checkpoint ID + different initialization fingerprint => rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand1 = CheckpointCandidate("chk-dup-initfp", "att-1", "inv-1", "l-1", 1, "n-1", "fp-1", "b1", "payload-1")
    cand2 = CheckpointCandidate("chk-dup-initfp", "att-1", "inv-1", "l-1", 1, "n-1", "fp-DIFF", "b1", "payload-1")

    with uow:
        chk_mgr.record_checkpoint(cand1, "fp-1", uow.connection)
        with pytest.raises(CheckpointRejectedError):
            chk_mgr.record_checkpoint(cand2, "fp-1", uow.connection)


def test_10_duplicate_checkpoint_different_payload_ref(temp_db_path):
    """10. Duplicate checkpoint ID + different payload reference => rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-1", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand1 = CheckpointCandidate("chk-dup-pref", "att-1", "inv-1", "l-1", 1, "n-1", "fp-1", "b1", "payload-1")
    cand2 = CheckpointCandidate("chk-dup-pref", "att-1", "inv-1", "l-1", 1, "n-1", "fp-1", "b1", "payload-MALICIOUS")

    with uow:
        chk_mgr.record_checkpoint(cand1, "fp-1", uow.connection)
        with pytest.raises(CheckpointRejectedError, match="conflicting canonical content"):
            chk_mgr.record_checkpoint(cand2, "fp-1", uow.connection)


# -- Finding 03: Deep Immutability ---------------------------------------------

def test_11_domain_event_nested_payload_immutable():
    """11. DomainEvent nested payload cannot be mutated after construction."""
    nested = {"details": {"status": "ACTIVE"}}
    evt = DomainEvent.create("mig-11", "test.event", nested)

    assert isinstance(evt.payload, types.MappingProxyType)
    with pytest.raises(TypeError):
        evt.payload["details"] = "MUTATED"

    with pytest.raises(TypeError):
        evt.payload["details"]["status"] = "MUTATED"


def test_12_integration_event_nested_payload_immutable():
    """12. IntegrationEvent nested payload cannot be mutated."""
    nested = {"items": [1, 2, {"key": "val"}]}
    evt = IntegrationEvent("evt-12", "integ.event", nested)

    assert isinstance(evt.payload, types.MappingProxyType)
    with pytest.raises(TypeError):
        evt.payload["items"] = []


def test_13_engine_proposal_nested_payload_immutable():
    """13. EngineEventProposal nested payload cannot be mutated."""
    nested = {"metrics": {"rows": 100}}
    prop = EngineEventProposal("p-13", "b-1", "att-1", "inv-1", "l-1", 1, "fp-1", "n-1", "task.done", nested)

    assert isinstance(prop.payload, types.MappingProxyType)
    with pytest.raises(TypeError):
        prop.payload["metrics"] = {}


def test_14_external_dict_mutation_isolated():
    """14. Caller-owned nested structures mutated after object construction do not mutate canonical event/artifact state."""
    raw_dict = {"nested": {"status": "ORIGINAL"}}
    art = ImmutableArtifact.create("art-14", "initialization", raw_dict)

    # Mutate raw_dict post-creation
    raw_dict["nested"]["status"] = "MUTATED_BY_CALLER"

    # Artifact content must remain unchanged
    assert art.content["nested"]["status"] == "ORIGINAL"


def test_15_canonical_fingerprint_deterministic_with_frozen():
    """15. Canonical serialization/fingerprinting remains deterministic after deep-freeze correction."""
    frozen_payload = deep_freeze({"b": 2, "a": [1, {"x": "y"}]})
    fp1 = canonical_fingerprint(frozen_payload)
    fp2 = canonical_fingerprint({"a": [1, {"x": "y"}], "b": 2})

    assert fp1 == fp2


# -- Finding 04: Default Persistence Safety ------------------------------------

def test_16_unified_caller_no_implicit_memory_default():
    """16. PipelineUnifiedCaller() without persistence configuration cannot silently create an in-memory database."""
    with pytest.raises(ValueError, match="requires an explicit db_path or shared_uow"):
        PipelineUnifiedCaller()


def test_17_no_production_constructor_implicit_memory_fallback():
    """17. No production constructor silently falls back to :memory:."""
    with pytest.raises(ValueError):
        SQLiteMigrationRepository(db_path="")

    with pytest.raises(ValueError):
        SQLiteUnitOfWork(db_path=None, shared_connection=None)


# -- Finding 05: ID Entropy -----------------------------------------------------

def test_18_generated_ids_full_uuid_entropy():
    """18. Generated canonical IDs use full-strength UUID entropy/representation."""
    m_id = str(MigrationId.generate())
    o_id = str(OperationId.generate())
    a_id = str(AttemptId.generate())
    p_id = str(ExecutionPlanId.generate())
    i_id = str(InitializationId.generate())

    # Full UUID hex is 32 chars + prefix
    assert len(m_id) > 20, f"Expected full UUID entropy, got {m_id}"
    assert len(o_id) > 20
    assert len(a_id) > 20
    assert len(p_id) > 20
    assert len(i_id) > 20


# -- Finding 06: Provenance Hardening ------------------------------------------

def test_19_stale_engine_provenance_rejected(temp_db_path):
    """19. Stale engine provenance is rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.execution.result_reconciliation import ResultReconciler
    from akaalPipeline.operations.leases import LeaseManager

    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-new", "att-19", "owner-1", "2099-01-01T00:00:00+00:00", "fp-canonical", uow.connection)

    rec = ResultReconciler(lm)
    stale_res = EngineInvocationResult("inv-1", "att-19", "l-OLD", 1, True, initialization_fingerprint="fp-canonical")

    with uow:
        with pytest.raises(StaleResultError):
            rec.reconcile_result(stale_res, "fp-canonical", uow.connection)


def test_20_wrong_init_provenance_rejected(temp_db_path):
    """20. Wrong initialization provenance is rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.execution.result_reconciliation import ResultReconciler
    from akaalPipeline.operations.leases import LeaseManager

    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-20", "owner-1", "2099-01-01T00:00:00+00:00", "fp-CORRECT", uow.connection)

    rec = ResultReconciler(lm)
    wrong_init_res = EngineInvocationResult("inv-1", "att-20", "l-1", 1, True, initialization_fingerprint="fp-WRONG")

    with uow:
        with pytest.raises(StaleResultError):
            rec.reconcile_result(wrong_init_res, "fp-CORRECT", uow.connection)


def test_21_wrong_node_provenance_rejected(temp_db_path):
    """21. Wrong graph-node provenance is rejected during checkpoint validation."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-21", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand1 = CheckpointCandidate("chk-node-1", "att-21", "inv-1", "l-1", 1, "node-CORRECT", "fp-1", "b1", "payload-1")
    cand2 = CheckpointCandidate("chk-node-1", "att-21", "inv-1", "l-1", 1, "node-WRONG", "fp-1", "b1", "payload-1")

    with uow:
        chk_mgr.record_checkpoint(cand1, "fp-1", uow.connection)
        with pytest.raises(CheckpointRejectedError):
            chk_mgr.record_checkpoint(cand2, "fp-1", uow.connection)


def test_22_wrong_invocation_provenance_rejected(temp_db_path):
    """22. Wrong invocation provenance is rejected during checkpoint replay."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-22", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    chk_mgr = CheckpointManager(lm)
    cand1 = CheckpointCandidate("chk-inv-1", "att-22", "inv-CORRECT", "l-1", 1, "node-1", "fp-1", "b1", "payload-1")
    cand2 = CheckpointCandidate("chk-inv-1", "att-22", "inv-WRONG", "l-1", 1, "node-1", "fp-1", "b1", "payload-1")

    with uow:
        chk_mgr.record_checkpoint(cand1, "fp-1", uow.connection)
        with pytest.raises(CheckpointRejectedError):
            chk_mgr.record_checkpoint(cand2, "fp-1", uow.connection)


def test_23_wrong_fence_epoch_rejected(temp_db_path):
    """23. Wrong fence epoch remains rejected."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.execution.result_reconciliation import ResultReconciler
    from akaalPipeline.operations.leases import LeaseManager

    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-23", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    rec = ResultReconciler(lm)
    wrong_epoch_res = EngineInvocationResult("inv-1", "att-23", "l-1", 99, True, initialization_fingerprint="fp-1")

    with uow:
        with pytest.raises(StaleResultError):
            rec.reconcile_result(wrong_epoch_res, "fp-1", uow.connection)


def test_24_correct_provenance_accepted(temp_db_path):
    """24. Correct current provenance remains accepted."""
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    from akaalPipeline.execution.result_reconciliation import ResultReconciler
    from akaalPipeline.operations.leases import LeaseManager

    lm = LeaseManager()
    with uow:
        lm.acquire_lease("l-1", "att-24", "owner-1", "2099-01-01T00:00:00+00:00", "fp-1", uow.connection)

    rec = ResultReconciler(lm)
    valid_res = EngineInvocationResult("inv-1", "att-24", "l-1", 1, True, initialization_fingerprint="fp-1", result_payload={"done": True})

    with uow:
        reconciled = rec.reconcile_result(valid_res, "fp-1", uow.connection)
        assert reconciled["status"] == "SUCCEEDED"
        assert reconciled["result_payload"] == {"done": True}
