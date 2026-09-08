"""tests/security/test_p7c_group2_staleness_protection.py
================================================================
Closes owner-review Blocker 15: proves Group 2 artifacts (P7C.16
optimization, P7C.18 remediation) are subject to the SAME frozen P7C.1
staleness machinery (akaalEngine.intelligence.api.IntelligenceKernel.
evaluate_staleness/refresh_staleness, akaalEngine.intelligence.lifecycle.
staleness.is_context_stale) already proven for Group 1 -- never a second,
Group-2-specific staleness mechanism. A Group-2 artifact generated against
one canonical context and later evaluated against a materially different
context (topology/plan/subject-version change) is detected as stale and, on
refresh, transitioned to the STALE terminal-adjacent lifecycle state -- it
does not remain silently actionable.

Also proves the P7C.18 mediation-time staleness gate (context_fingerprint !=
current_context_fingerprint -> StaleProposalError, already exercised in
test_p7c18_full_governed_pause_execution.py::test_stale_context_fingerprint_refused)
is the SAME real gate, not a second one -- by asserting on the exact error
type raised by the real akaalEngine.intelligence.mediation.mediator.
ActionMediationGateway.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.lifecycle import ArtifactLifecycleState
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.optimization import make_optimization_producer


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE intelligence_artifacts (
            artifact_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT,
            project_id TEXT, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
            subject_version TEXT NOT NULL, task TEXT NOT NULL, algorithm_version TEXT NOT NULL,
            policy_version TEXT NOT NULL, canonical_state_fingerprint TEXT NOT NULL,
            fingerprint TEXT NOT NULL, result TEXT NOT NULL, lifecycle_state TEXT NOT NULL,
            created_at TEXT NOT NULL, requested_by TEXT NOT NULL, model_provider TEXT,
            model_id TEXT, model_version TEXT, expires_at TEXT, superseded_by TEXT, updated_at TEXT
        )
        """
    )
    yield connection
    connection.close()


class TestOptimizationArtifactGoesStaleOnCanonicalContextChange:
    def test_plan_revision_change_makes_prior_optimization_stale(self, conn):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(IntelligenceTask.OPTIMIZE, make_optimization_producer(None), capability="performance_optimization")

        context_v1 = IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="rev-1")
        req = IntelligenceRequest(
            task=IntelligenceTask.OPTIMIZE, tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1",
            subject_version="rev-1", requested_by="user-1", capability="performance_optimization",
            parameters={
                "dataset_size_bytes": 1_000_000_000, "worker_throughput_bytes_per_sec": 1_000_000,
                "validation_throughput_bytes_per_sec": 2_000_000, "cutover_window_seconds": 10_000,
            },
        )
        artifact = kernel.submit_request(req, context_v1, conn)
        assert artifact.lifecycle_state == ArtifactLifecycleState.GENERATED

        # Canonical plan has since been revised (a real topology/config
        # change would bump subject_version/canonical_state_fingerprint the
        # SAME way a real akaalPipeline resolver's IntelligenceContext would
        # reflect a new plan revision).
        context_v2 = IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="rev-2")

        assert kernel.evaluate_staleness(artifact, context_v2) is True
        assert kernel.evaluate_staleness(artifact, context_v1) is False

        refreshed = kernel.refresh_staleness(artifact, context_v2, conn)
        assert refreshed.lifecycle_state == ArtifactLifecycleState.STALE

        # The STALE artifact is still retrievable (audit trail preserved),
        # but its lifecycle state itself is the caller's signal that it must
        # not be acted on without recomputation.
        refetched = kernel.get_artifact(artifact.artifact_id, conn)
        assert refetched.lifecycle_state == ArtifactLifecycleState.STALE


class TestRemediationProposalMediationStalenessIsTheSameRealGate:
    def test_stale_proposal_error_is_the_real_mediation_gateway_error_type(self):
        from akaalEngine.intelligence.mediation.errors import StaleProposalError
        from akaalEngine.intelligence.mediation.mediator import ActionMediationGateway
        from akaalEngine.intelligence.mediation.proposal import ActionProposal

        gateway = ActionMediationGateway()
        proposal = ActionProposal(
            action_type="propose_remediation_pause_migration", tenant_id="tenant-a",
            target_resource_type="migration", target_resource_id="mig-1", requested_by="user-1",
            context_fingerprint="fp-old",
        )
        with pytest.raises(StaleProposalError):
            gateway.mediate(proposal, current_context_fingerprint="fp-new-after-canonical-change", authorizer=lambda p: True)
