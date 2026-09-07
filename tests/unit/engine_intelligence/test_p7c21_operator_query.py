"""tests/unit/engine_intelligence/test_p7c21_operator_query.py
====================================================================
P7C.21: intent routing is a closed allow-list (no free-form fallback);
answers are assembled only from already-computed, cited summaries; missing
facts are reported honestly, never guessed.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.operator_query import OperatorQueryInputs, make_operator_query_producer


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
    kernel.register_producer(IntelligenceTask.QUERY, make_operator_query_producer(resolver), capability="operator_query")
    return kernel


def _request(intent) -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.QUERY, tenant_id="tenant-a", subject_type="migration",
        subject_id="mig-1", subject_version="v1", requested_by="user-1", capability="operator_query",
        parameters={"intent": intent},
    )


def _context() -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")


class TestClosedIntentAllowList:
    def test_unsupported_intent_refuses(self, conn):
        kernel = _kernel(lambda req, ctx: OperatorQueryInputs(migration_id="mig-1"))
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_request("do_something_unsupported"), _context(), conn)


class TestGroundedAnswers:
    def test_what_is_happening_cites_health_and_anomaly(self, conn):
        inputs = OperatorQueryInputs(migration_id="mig-1", health_summary="Runtime health: HEALTHY.", anomaly_summary="No anomaly detected.")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request("what_is_happening"), _context(), conn)
        assert "HEALTHY" in artifact.result["summary"]
        assert set(artifact.result["data"]["citations"]) == {"runtime_health", "anomaly_detection"}

    def test_no_facts_available_is_honest_not_guessed(self, conn):
        inputs = OperatorQueryInputs(migration_id="mig-1")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request("why"), _context(), conn)
        assert "No grounded facts" in artifact.result["summary"]
        assert artifact.result["epistemic_type"] == "ASSUMPTION"


class TestExpandedIntentScope:
    """Owner-review Blocker 12 closure: broader authorized operator-question
    scope, still a closed deterministic allow-list, still grounded-only."""

    def test_estimated_cost_intent(self, conn):
        inputs = OperatorQueryInputs(migration_id="mig-1", finops_summary="FinOps SCENARIO projection: COST_PROJECTION_AVAILABLE.")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request("estimated_cost"), _context(), conn)
        assert "COST_PROJECTION_AVAILABLE" in artifact.result["summary"]
        assert artifact.result["data"]["citations"] == ["finops_projection"]

    def test_supporting_evidence_intent(self, conn):
        inputs = OperatorQueryInputs(migration_id="mig-1", rca_supporting_facts="FABRIC dimension status = CRITICAL")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request("supporting_evidence"), _context(), conn)
        assert "CRITICAL" in artifact.result["summary"]

    def test_invalidation_conditions_intent(self, conn):
        inputs = OperatorQueryInputs(migration_id="mig-1", rca_invalidation_condition="FABRIC dimension returns to a non-CRITICAL canonical status.")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request("invalidation_conditions"), _context(), conn)
        assert "non-CRITICAL" in artifact.result["summary"]

    def test_at_risk_migrations_intent(self, conn):
        inputs = OperatorQueryInputs(migration_id="mig-1", portfolio_summary="Portfolio for tenant 'tenant-a': 3 migration(s) evaluated, 1 at risk.")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request("at_risk_migrations"), _context(), conn)
        assert "1 at risk" in artifact.result["summary"]

    def test_what_changed_intent_uses_anomaly_summary(self, conn):
        inputs = OperatorQueryInputs(migration_id="mig-1", anomaly_summary="Anomaly detection: overall=ANOMALOUS, bottleneck=UNKNOWN.")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request("what_changed"), _context(), conn)
        assert "ANOMALOUS" in artifact.result["summary"]


class TestNullResolverRefuses:
    def test_none_resolver_raises(self, conn):
        kernel = _kernel(lambda req, ctx: None)
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_request("what_is_happening"), _context(), conn)
