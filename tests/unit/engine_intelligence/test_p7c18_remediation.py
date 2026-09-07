"""tests/unit/engine_intelligence/test_p7c18_remediation.py
================================================================
P7C.18: recipe selection never fabricates an action for causes it has no
canonical action for (governance-critical, unmatched); a matched recipe
produces a real typed ActionProposal referencing an ALREADY-registered
action_type; the producer never mediates/executes anything itself.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.mediation.autonomy import ACTION_AUTONOMY_REGISTRY, AutonomyLevel
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.remediation import RemediationInputs, make_remediation_producer
from akaalEngine.intelligence.remediation.recipes import select_recipe


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


def _kernel(resolver) -> IntelligenceKernel:
    kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
    kernel.register_producer(IntelligenceTask.RECOMMEND, make_remediation_producer(resolver), capability="governed_remediation")
    return kernel


def _request() -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.RECOMMEND, tenant_id="tenant-a", subject_type="migration",
        subject_id="mig-1", subject_version="v1", requested_by="user-1", capability="governed_remediation",
    )


def _context() -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")


class TestRecipeSelection:
    def test_governance_critical_never_gets_automated_recipe(self):
        assert select_recipe(primary_hypothesis_label="Target-side CDC apply is falling behind", fabric_status="CRITICAL", validation_status="UNKNOWN") is None

    def test_unmatched_cause_returns_none(self):
        assert select_recipe(primary_hypothesis_label="Some unrelated cause", fabric_status="UNKNOWN", validation_status="UNKNOWN") is None

    def test_apply_bound_backlog_matches_pause_recipe(self):
        recipe = select_recipe(primary_hypothesis_label="Target-side CDC apply is falling behind source-side capture (apply-bound saturation).", fabric_status="UNKNOWN", validation_status="UNKNOWN")
        assert recipe is not None
        assert recipe.action_type in ACTION_AUTONOMY_REGISTRY
        assert ACTION_AUTONOMY_REGISTRY[recipe.action_type] == AutonomyLevel.L3_GOVERNED_ACTION_AFTER_APPROVAL


class TestProducerNoFabrication:
    def test_no_recipe_yields_recommendation_not_proposal(self, conn):
        inputs = RemediationInputs(
            tenant_id="tenant-a", migration_id="mig-1", requested_by="user-1", context_fingerprint="fp-1",
            rca_data={"primary_hypothesis": "No anomaly currently requires root-cause analysis."},
        )
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["epistemic_type"] == "RECOMMENDATION"
        assert artifact.result["data"]["action_proposal"] is None

    def test_matched_recipe_produces_real_typed_proposal(self, conn):
        inputs = RemediationInputs(
            tenant_id="tenant-a", migration_id="mig-1", requested_by="user-1", context_fingerprint="fp-1",
            rca_data={"primary_hypothesis": "Target-side CDC apply is falling behind source-side capture (apply-bound saturation)."},
        )
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["epistemic_type"] == "PROPOSAL"
        proposal = artifact.result["data"]["action_proposal"]
        assert proposal["action_type"] == "propose_remediation_pause_migration"
        assert proposal["tenant_id"] == "tenant-a"
        assert proposal["target_resource_id"] == "mig-1"

    def test_null_resolver_raises(self, conn):
        from akaalEngine.intelligence.models.errors import IntelligenceValidationError

        kernel = _kernel(lambda req, ctx: None)
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_request(), _context(), conn)
