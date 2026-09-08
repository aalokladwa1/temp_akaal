"""tests/unit/engine_intelligence/test_p7c22_portfolio.py
==============================================================
P7C.22: aggregation counts real per-migration statuses; at-risk detection;
truncation is disclosed, never silently hidden.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.portfolio import (
    PortfolioInputs,
    PortfolioMigrationSummary,
    make_portfolio_producer,
)


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
    kernel.register_producer(IntelligenceTask.QUERY, make_portfolio_producer(resolver), capability="portfolio_intelligence")
    return kernel


def _request() -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.QUERY, tenant_id="tenant-a", subject_type="tenant",
        subject_id="tenant-a", subject_version="v1", requested_by="user-1", capability="portfolio_intelligence",
    )


def _context() -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="tenant", subject_id="tenant-a", subject_version="v1")


class TestAggregation:
    def test_counts_and_at_risk_detection(self, conn):
        inputs = PortfolioInputs(
            tenant_id="tenant-a",
            migrations=[
                PortfolioMigrationSummary(migration_id="mig-1", overall_status="HEALTHY"),
                PortfolioMigrationSummary(migration_id="mig-2", overall_status="CRITICAL"),
                PortfolioMigrationSummary(migration_id="mig-3", overall_status="UNKNOWN"),
            ],
        )
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["status_counts"] == {"HEALTHY": 1, "CRITICAL": 1, "UNKNOWN": 1}
        assert artifact.result["data"]["at_risk_migration_ids"] == ["mig-2"]

    def test_more_available_discloses_next_cursor_not_silent_truncation(self, conn):
        inputs = PortfolioInputs(tenant_id="tenant-a", migrations=[PortfolioMigrationSummary(migration_id="mig-1", overall_status="HEALTHY")], next_cursor="50")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["truncated"] is True
        assert artifact.result["data"]["next_cursor"] == "50"
        assert any("cursor" in m.lower() for m in artifact.result["confidence_evidence"]["missing_information"])

    def test_no_more_available_yields_null_cursor(self, conn):
        inputs = PortfolioInputs(tenant_id="tenant-a", migrations=[PortfolioMigrationSummary(migration_id="mig-1", overall_status="HEALTHY")])
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["truncated"] is False
        assert artifact.result["data"]["next_cursor"] is None


class TestNullResolverRefuses:
    def test_none_resolver_raises(self, conn):
        from akaalEngine.intelligence.models.errors import IntelligenceValidationError

        kernel = _kernel(lambda req, ctx: None)
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_request(), _context(), conn)
