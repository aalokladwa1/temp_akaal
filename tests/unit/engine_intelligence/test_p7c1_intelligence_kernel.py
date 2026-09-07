"""tests/unit/engine_intelligence/test_p7c1_intelligence_kernel.py
====================================================================
P7C.1 Intelligence Kernel: fingerprint determinism/hostile bit-flip, lifecycle
transition matrix, staleness detection, cancellation/timeout, serialization
round-trip, and end-to-end submit/get/list against a real SQLite connection.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.budget import (
    CancellationToken,
    RequestBudget,
    check_budget_and_cancellation,
)
from akaalEngine.intelligence.identity.fingerprint import (
    compute_artifact_fingerprint,
    compute_context_fingerprint,
)
from akaalEngine.intelligence.lifecycle.staleness import is_context_stale, is_expired
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.artifact import IntelligenceArtifact
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import (
    IntelligenceBudgetExceededError,
    IntelligenceCancelledError,
    IntelligenceInvalidTransitionError,
    IntelligenceNotFoundError,
    IntelligenceTaskUnsupportedError,
    IntelligenceTenantBoundaryError,
)
from akaalEngine.intelligence.models.lifecycle import ArtifactLifecycleState, validate_transition
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask


def _ctx(**overrides) -> IntelligenceContext:
    base = dict(
        tenant_id="tenant-a",
        subject_type="migration_plan",
        subject_id="plan-1",
        subject_version="v1",
    )
    base.update(overrides)
    return IntelligenceContext(**base)


def _req(**overrides) -> IntelligenceRequest:
    base = dict(
        task=IntelligenceTask.QUERY,
        tenant_id="tenant-a",
        subject_type="migration_plan",
        subject_id="plan-1",
        subject_version="v1",
        requested_by="user-1",
    )
    base.update(overrides)
    return IntelligenceRequest(**base)


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE intelligence_artifacts (
            artifact_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            workspace_id TEXT,
            project_id TEXT,
            subject_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            subject_version TEXT NOT NULL,
            task TEXT NOT NULL,
            algorithm_version TEXT NOT NULL,
            policy_version TEXT NOT NULL,
            canonical_state_fingerprint TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            result TEXT NOT NULL,
            lifecycle_state TEXT NOT NULL,
            created_at TEXT NOT NULL,
            requested_by TEXT NOT NULL,
            model_provider TEXT,
            model_id TEXT,
            model_version TEXT,
            expires_at TEXT,
            superseded_by TEXT,
            updated_at TEXT
        )
        """
    )
    yield connection
    connection.close()


@pytest.fixture
def kernel() -> IntelligenceKernel:
    return IntelligenceKernel(store=IntelligenceArtifactStore())


# --- Fingerprint determinism -------------------------------------------------

class TestFingerprintDeterminism:
    def test_identical_context_yields_identical_fingerprint(self):
        c1 = _ctx()
        c2 = _ctx()
        assert compute_context_fingerprint(c1) == compute_context_fingerprint(c2)

    def test_context_fingerprint_independent_of_dict_key_order(self):
        # dataclasses always serialize in field order via to_dict(), but the
        # underlying canonical_json sorts keys regardless -- prove both paths agree.
        from akaalEngine.intelligence.identity.fingerprint import canonical_json

        a = {"b": 1, "a": 2}
        b = {"a": 2, "b": 1}
        assert canonical_json(a) == canonical_json(b)

    @pytest.mark.parametrize(
        "field_name,new_value",
        [
            ("tenant_id", "tenant-b"),
            ("subject_type", "table"),
            ("subject_id", "plan-2"),
            ("subject_version", "v2"),
            ("policy_version", "p7c1-policy-v2"),
            ("algorithm_version", "p7c1-kernel-v2"),
        ],
    )
    def test_hostile_bit_flip_changes_fingerprint(self, field_name, new_value):
        """Hostile test: flipping any single identity dimension must change the
        fingerprint. A collision here would let a stale/forged context masquerade
        as a fresh one."""
        baseline = _ctx()
        mutated = _ctx(**{field_name: new_value})
        assert compute_context_fingerprint(baseline) != compute_context_fingerprint(mutated)

    def test_artifact_fingerprint_changes_with_result_fingerprint(self):
        fp1 = compute_artifact_fingerprint(
            context_fingerprint="ctxfp",
            task="QUERY",
            algorithm_version="v1",
            policy_version="v1",
            result_fingerprint="resultfp-1",
        )
        fp2 = compute_artifact_fingerprint(
            context_fingerprint="ctxfp",
            task="QUERY",
            algorithm_version="v1",
            policy_version="v1",
            result_fingerprint="resultfp-2",
        )
        assert fp1 != fp2

    def test_artifact_fingerprint_changes_with_model_identity(self):
        base = dict(
            context_fingerprint="ctxfp",
            task="RECOMMEND",
            algorithm_version="v1",
            policy_version="v1",
            result_fingerprint="resultfp",
        )
        fp_no_model = compute_artifact_fingerprint(**base)
        fp_with_model = compute_artifact_fingerprint(**base, model_provider="acme", model_id="m1", model_version="1.0")
        assert fp_no_model != fp_with_model


# --- Lifecycle transition matrix ----------------------------------------------

class TestLifecycleTransitions:
    def test_generated_to_grounded_allowed(self):
        validate_transition(ArtifactLifecycleState.GENERATED, ArtifactLifecycleState.GROUNDED)

    def test_generated_to_accepted_disallowed(self):
        with pytest.raises(IntelligenceInvalidTransitionError):
            validate_transition(ArtifactLifecycleState.GENERATED, ArtifactLifecycleState.ACCEPTED)

    def test_presented_to_accepted_allowed(self):
        validate_transition(ArtifactLifecycleState.PRESENTED, ArtifactLifecycleState.ACCEPTED)

    @pytest.mark.parametrize(
        "terminal_state",
        [ArtifactLifecycleState.REJECTED, ArtifactLifecycleState.EXPIRED, ArtifactLifecycleState.SUPERSEDED],
    )
    def test_no_transition_out_of_terminal_states(self, terminal_state):
        for target in ArtifactLifecycleState:
            if target == terminal_state:
                continue
            with pytest.raises(IntelligenceInvalidTransitionError):
                validate_transition(terminal_state, target)

    def test_self_transition_always_disallowed(self):
        for state in ArtifactLifecycleState:
            with pytest.raises(IntelligenceInvalidTransitionError):
                validate_transition(state, state)

    def test_stale_cannot_go_back_to_generated(self):
        """Hostile: a stale recommendation must never silently become actionable
        again -- it can only be superseded or expire."""
        with pytest.raises(IntelligenceInvalidTransitionError):
            validate_transition(ArtifactLifecycleState.STALE, ArtifactLifecycleState.GENERATED)
        with pytest.raises(IntelligenceInvalidTransitionError):
            validate_transition(ArtifactLifecycleState.STALE, ArtifactLifecycleState.ACCEPTED)


# --- Kernel end-to-end (real SQLite) -----------------------------------------

class TestKernelSubmitAndRetrieve:
    def test_submit_request_persists_and_returns_generated_artifact(self, kernel, conn):
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        assert artifact.lifecycle_state == ArtifactLifecycleState.GENERATED
        assert artifact.tenant_id == "tenant-a"
        assert artifact.canonical_state_fingerprint == compute_context_fingerprint(_ctx())

        fetched = kernel.get_artifact(artifact.artifact_id, conn)
        assert fetched.artifact_id == artifact.artifact_id
        assert fetched.fingerprint == artifact.fingerprint

    def test_get_missing_artifact_raises_not_found(self, kernel, conn):
        with pytest.raises(IntelligenceNotFoundError):
            kernel.get_artifact("intel-art-does-not-exist", conn)

    def test_list_artifacts_scoped_to_tenant(self, kernel, conn):
        kernel.submit_request(_req(tenant_id="tenant-a"), _ctx(tenant_id="tenant-a"), conn)
        kernel.submit_request(_req(tenant_id="tenant-b"), _ctx(tenant_id="tenant-b"), conn)
        results_a = kernel.list_artifacts("tenant-a", conn)
        results_b = kernel.list_artifacts("tenant-b", conn)
        assert len(results_a) == 1
        assert len(results_b) == 1
        assert results_a[0].tenant_id == "tenant-a"
        assert results_b[0].tenant_id == "tenant-b"

    def test_submit_rejects_tenant_mismatch_between_request_and_context(self, kernel, conn):
        with pytest.raises(IntelligenceTenantBoundaryError):
            kernel.submit_request(_req(tenant_id="tenant-a"), _ctx(tenant_id="tenant-b"), conn)

    def test_submit_unsupported_task_raises_typed_error_not_fake_success(self, kernel, conn):
        """P7C.1 ships exactly one deterministic producer (QUERY). Every other task
        must fail loudly rather than fabricate a result -- proves the zero-fake
        policy at the kernel boundary."""
        with pytest.raises(IntelligenceTaskUnsupportedError):
            kernel.submit_request(_req(task=IntelligenceTask.ASSESS), _ctx(), conn)

    def test_result_is_genuinely_computed_from_inputs(self, kernel, conn):
        """The built-in producer's output must actually depend on its inputs -- not
        be a canned string -- proving it is a real (if minimal) computation."""
        art1 = kernel.submit_request(_req(subject_id="plan-1"), _ctx(subject_id="plan-1"), conn)
        art2 = kernel.submit_request(_req(subject_id="plan-2"), _ctx(subject_id="plan-2"), conn)
        assert art1.result["data"]["context_fingerprint"] != art2.result["data"]["context_fingerprint"]
        assert "plan-1" in art1.result["summary"]
        assert "plan-2" in art2.result["summary"]


# --- Staleness -----------------------------------------------------------------

class TestStaleness:
    def test_same_context_not_stale(self, kernel, conn):
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        assert kernel.evaluate_staleness(artifact, _ctx()) is False

    def test_changed_subject_version_marks_stale(self, kernel, conn):
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        newer_ctx = _ctx(subject_version="v2")
        assert kernel.evaluate_staleness(artifact, newer_ctx) is True

    def test_refresh_staleness_persists_stale_transition(self, kernel, conn):
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        newer_ctx = _ctx(subject_version="v2")
        updated = kernel.refresh_staleness(artifact, newer_ctx, conn)
        assert updated.lifecycle_state == ArtifactLifecycleState.STALE

        refetched = kernel.get_artifact(artifact.artifact_id, conn)
        assert refetched.lifecycle_state == ArtifactLifecycleState.STALE

    def test_stale_artifact_transition_to_generated_rejected(self, kernel, conn):
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        kernel.refresh_staleness(artifact, _ctx(subject_version="v2"), conn)
        with pytest.raises(IntelligenceInvalidTransitionError):
            kernel.transition(artifact.artifact_id, ArtifactLifecycleState.GENERATED, conn)

    def test_is_expired_true_after_expiry_timestamp(self):
        from datetime import datetime, timedelta, timezone

        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        artifact = IntelligenceArtifact(
            artifact_id="intel-art-x",
            tenant_id="tenant-a",
            subject_type="migration_plan",
            subject_id="plan-1",
            subject_version="v1",
            task=IntelligenceTask.QUERY,
            algorithm_version="v1",
            policy_version="v1",
            canonical_state_fingerprint="fp",
            fingerprint="afp",
            result={},
            lifecycle_state=ArtifactLifecycleState.GENERATED,
            created_at=past,
            requested_by="user-1",
            expires_at=past,
        )
        assert is_expired(artifact) is True


# --- Cancellation / budget -----------------------------------------------------

class TestCancellationAndBudget:
    def test_cancellation_token_raises_before_producer_runs(self, kernel, conn):
        token = CancellationToken()
        token.cancel()
        with pytest.raises(IntelligenceCancelledError):
            kernel.submit_request(_req(), _ctx(), conn, cancellation_token=token)

    def test_budget_exhaustion_raises_typed_error(self):
        budget = RequestBudget(max_seconds=0.01)
        time.sleep(0.02)
        with pytest.raises(IntelligenceBudgetExceededError):
            check_budget_and_cancellation(budget, None)

    def test_budget_not_exceeded_when_within_window(self):
        budget = RequestBudget(max_seconds=10.0)
        check_budget_and_cancellation(budget, None)  # must not raise

    def test_request_rejects_non_positive_timeout(self):
        with pytest.raises(ValueError):
            _req(timeout_seconds=0)


# --- Serialization round-trip ---------------------------------------------------

class TestArtifactIntegrityVerificationHostile:
    def test_untampered_artifact_passes_integrity_check(self, kernel, conn):
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        assert kernel.verify_artifact_integrity(artifact) is True
        # Also exercised via the enforcing get_artifact(..., verify_integrity=True) path.
        kernel.get_artifact(artifact.artifact_id, conn, verify_integrity=True)

    def test_hostile_tampered_result_content_fails_integrity_check(self, kernel, conn):
        """Simulates a row tampered at rest (e.g. direct DB write bypassing the
        kernel): the stored `result` content no longer matches the fingerprint
        computed at generation time. Must be detected, never silently trusted."""
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        conn.execute(
            "UPDATE intelligence_artifacts SET result = ? WHERE artifact_id = ?",
            ('{"tampered": true}', artifact.artifact_id),
        )
        conn.commit()

        tampered = kernel.get_artifact(artifact.artifact_id, conn)  # raw read still succeeds
        assert kernel.verify_artifact_integrity(tampered) is False

        with pytest.raises(Exception):
            kernel.get_artifact(artifact.artifact_id, conn, verify_integrity=True)

    def test_hostile_tampered_fingerprint_field_itself_fails_integrity_check(self, kernel, conn):
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        conn.execute(
            "UPDATE intelligence_artifacts SET fingerprint = ? WHERE artifact_id = ?",
            ("forged-fingerprint-0000", artifact.artifact_id),
        )
        conn.commit()
        tampered = kernel.get_artifact(artifact.artifact_id, conn)
        assert kernel.verify_artifact_integrity(tampered) is False


class TestSerializationRoundTrip:
    def test_artifact_to_dict_from_dict_round_trip(self, kernel, conn):
        artifact = kernel.submit_request(_req(), _ctx(), conn)
        restored = IntelligenceArtifact.from_dict(artifact.to_dict())
        assert restored.to_dict() == artifact.to_dict()

    def test_store_round_trip_preserves_all_fields(self, conn):
        store = IntelligenceArtifactStore()
        original = IntelligenceArtifact(
            artifact_id="intel-art-rt",
            tenant_id="tenant-a",
            workspace_id="ws-1",
            project_id="proj-1",
            subject_type="migration_plan",
            subject_id="plan-1",
            subject_version="v1",
            task=IntelligenceTask.ASSESS,
            algorithm_version="algo-v1",
            policy_version="policy-v1",
            canonical_state_fingerprint="ctxfp",
            fingerprint="artfp",
            result={"summary": "test", "nested": {"a": 1}},
            lifecycle_state=ArtifactLifecycleState.GENERATED,
            created_at="2026-01-01T00:00:00+00:00",
            requested_by="user-1",
            model_provider="acme",
            model_id="m1",
            model_version="1.0",
        )
        store.save(original, conn)
        fetched = store.get("intel-art-rt", conn)
        assert fetched.to_dict() == original.to_dict()
