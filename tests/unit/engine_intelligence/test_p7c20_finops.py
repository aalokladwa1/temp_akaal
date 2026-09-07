"""tests/unit/engine_intelligence/test_p7c20_finops.py
============================================================
P7C.20: cost only computed from a supplied organization rate + real ETA;
never fabricated when either is missing; no invented price catalog.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.finops import FinOpsInputs, make_finops_producer


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
    kernel.register_producer(IntelligenceTask.FORECAST, make_finops_producer(resolver), capability="finops_projection")
    return kernel


def _request() -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.FORECAST, tenant_id="tenant-a", subject_type="migration",
        subject_id="mig-1", subject_version="v1", requested_by="user-1", capability="finops_projection",
    )


def _context() -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")


class TestNoFabrication:
    def test_missing_cost_rate_yields_unknown(self, conn):
        inputs = FinOpsInputs(tenant_id="tenant-a", migration_id="mig-1", migration_eta_seconds=3600.0, worker_count=4)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["cost_status"] == "UNKNOWN"
        assert artifact.result["data"]["cost_to_completion"] is None

    def test_missing_eta_yields_unknown(self, conn):
        inputs = FinOpsInputs(tenant_id="tenant-a", migration_id="mig-1", cost_per_worker_hour=2.0, worker_count=4)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["cost_status"] == "UNKNOWN"


class TestCostProvenance:
    """Owner-review Blocker 10 closure: every cost number carries an explicit
    provenance tag distinguishing a caller-supplied scenario assumption from
    (a currently nonexistent) canonical organizational spend source -- never
    blurred together."""

    def test_cost_always_tagged_as_caller_supplied_assumption(self, conn):
        inputs = FinOpsInputs(tenant_id="tenant-a", migration_id="mig-1", migration_eta_seconds=3600.0, worker_count=4, cost_per_worker_hour=2.0)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["cost_source"] == "CALLER_SUPPLIED_ASSUMPTION"
        assert any("scenario assumption" in a for a in artifact.result["explanation"]["assumptions"])

    def test_no_cost_input_is_assumption_epistemic_type(self, conn):
        inputs = FinOpsInputs(tenant_id="tenant-a", migration_id="mig-1")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["epistemic_type"] == "ASSUMPTION"


class TestSustainabilityTruthfulLimitation:
    """Owner-review Blocker 11 closure: sustainability is explicitly declared
    unavailable, never silently omitted, never fabricated."""

    def test_sustainability_always_declared_not_currently_provable(self, conn):
        inputs = FinOpsInputs(tenant_id="tenant-a", migration_id="mig-1", migration_eta_seconds=3600.0, worker_count=4, cost_per_worker_hour=2.0)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["sustainability"]["status"] == "NOT_CURRENTLY_PROVABLE"
        assert "no canonical" in artifact.result["data"]["sustainability"]["reason"].lower()


class TestRealCostComputation:
    def test_cost_computed_from_rate_and_real_eta(self, conn):
        inputs = FinOpsInputs(tenant_id="tenant-a", migration_id="mig-1", migration_eta_seconds=3600.0, worker_count=4, cost_per_worker_hour=2.0)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["cost_status"] == "COST_PROJECTION_AVAILABLE"
        assert artifact.result["data"]["cost_to_completion"] == pytest.approx(8.0)

    def test_cost_per_gb_computed_when_dataset_size_supplied(self, conn):
        inputs = FinOpsInputs(
            tenant_id="tenant-a", migration_id="mig-1", migration_eta_seconds=3600.0, worker_count=4,
            cost_per_worker_hour=2.0, dataset_size_bytes=1_000_000_000,
        )
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["cost_per_gb"] == pytest.approx(8.0)


class TestNullResolverRefuses:
    def test_none_resolver_raises(self, conn):
        from akaalEngine.intelligence.models.errors import IntelligenceValidationError

        kernel = _kernel(lambda req, ctx: None)
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_request(), _context(), conn)
