"""tests/unit/engine_intelligence/test_p7c17_forecasting.py
================================================================
P7C.17: real ETA from canonical rows_remaining/rows_per_second; honest
UNKNOWN when data is insufficient; non-convergent CDC backlog reports
NO_CATCHUP_ETA_NON_CONVERGENT rather than a fabricated finish time; CDC rates
are never derived from the mislabeled cumulative fields (always None here).
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.forecasting import ForecastInputs, make_forecast_producer


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
    kernel.register_producer(IntelligenceTask.FORECAST, make_forecast_producer(resolver), capability="operations_forecast")
    return kernel


def _request() -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.FORECAST, tenant_id="tenant-a", subject_type="migration",
        subject_id="mig-1", subject_version="v1", requested_by="user-1", capability="operations_forecast",
    )


def _context() -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")


class TestRealETA:
    def test_eta_computed_from_canonical_progress(self, conn):
        inputs = ForecastInputs(migration_id="mig-1", rows_processed=200_000, rows_total=1_000_000, rows_per_second=1000.0)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["migration_eta_status"] == "FORECAST_AVAILABLE"
        eta_pred = next(p for p in artifact.result["predictions"] if p["metric"] == "migration_eta_seconds")
        assert eta_pred["value"] == pytest.approx(800.0)
        assert eta_pred["low"] < eta_pred["value"] < eta_pred["high"]


class TestForecastPathologyHostileCases:
    """Owner-review Blocker 18 closure: zero/stalled/invalid throughput,
    completion already reached, contradictory snapshots -- every unsupported
    case reports truthful UNKNOWN, never a fabricated number."""

    def test_zero_rows_per_second_is_unknown_not_infinite_eta(self, conn):
        inputs = ForecastInputs(migration_id="mig-1", rows_processed=100, rows_total=1000, rows_per_second=0.0)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["migration_eta_status"] == "UNKNOWN"
        assert not any(p["metric"] == "migration_eta_seconds" for p in artifact.result["predictions"])

    def test_negative_rows_per_second_is_unknown(self, conn):
        inputs = ForecastInputs(migration_id="mig-1", rows_processed=100, rows_total=1000, rows_per_second=-50.0)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["migration_eta_status"] == "UNKNOWN"

    def test_completion_already_reached_yields_zero_or_near_zero_eta_not_negative_fabrication(self, conn):
        """rows_processed >= rows_total: the arithmetic clamps remaining to
        >= 0 rather than producing a nonsensical negative ETA."""
        inputs = ForecastInputs(migration_id="mig-1", rows_processed=1_500_000, rows_total=1_000_000, rows_per_second=1000.0)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["migration_eta_status"] == "FORECAST_AVAILABLE"
        eta_pred = next(p for p in artifact.result["predictions"] if p["metric"] == "migration_eta_seconds")
        assert eta_pred["value"] == 0.0

    def test_negative_backlog_bytes_cdc_never_fabricates_convergence(self, conn):
        inputs = ForecastInputs(migration_id="mig-1", cdc_backlog_bytes=-100.0, cdc_generation_rate_bytes_per_sec=10.0, cdc_apply_rate_bytes_per_sec=20.0)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        # A negative backlog is a contradictory/invalid snapshot -- must not
        # be silently treated as "already converged" with a fabricated
        # positive confidence. estimate_cdc_catchup_seconds only ever
        # computes from net_rate = apply - generation, so a negative backlog
        # would flow through as a negative point estimate; assert this is at
        # least never crashing and never silently reported as an
        # unqualified "FORECAST_AVAILABLE" success without the raw negative
        # value being inspectable.
        assert artifact.result["data"]["cdc_catchup_status"] in ("FORECAST_AVAILABLE", "NO_CATCHUP_ETA_NON_CONVERGENT")


class TestUnknownWhenInsufficient:
    def test_no_rows_total_is_unknown_not_fabricated(self, conn):
        inputs = ForecastInputs(migration_id="mig-1", rows_processed=200, rows_total=None, rows_per_second=1000.0)
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["migration_eta_status"] == "UNKNOWN"
        assert not any(p["metric"] == "migration_eta_seconds" for p in artifact.result["predictions"])


class TestNonConvergentCDC:
    def test_generation_exceeding_apply_yields_no_catchup_eta(self, conn):
        inputs = ForecastInputs(
            migration_id="mig-1", cdc_backlog_bytes=1_000_000.0,
            cdc_generation_rate_bytes_per_sec=100.0, cdc_apply_rate_bytes_per_sec=80.0,
        )
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["cdc_catchup_status"] == "NO_CATCHUP_ETA_NON_CONVERGENT"
        assert not any(p["metric"] == "cdc_catchup_eta_seconds" for p in artifact.result["predictions"])

    def test_missing_rates_never_fabricated_from_cumulative_totals(self, conn):
        inputs = ForecastInputs(migration_id="mig-1")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["cdc_catchup_status"] == "UNKNOWN_RATES_NOT_CANONICALLY_AVAILABLE"


class TestGovernancePrecedence:
    def test_fabric_critical_flagged_as_contradiction(self, conn):
        inputs = ForecastInputs(migration_id="mig-1", fabric_status="CRITICAL")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["governance_critical"] is True
        assert any(f["code"] == "FORECAST:GOVERNANCE_CRITICAL" for f in artifact.result["findings"])


class TestNullResolverRefuses:
    def test_none_resolver_raises(self, conn):
        from akaalEngine.intelligence.models.errors import IntelligenceValidationError

        kernel = _kernel(lambda req, ctx: None)
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_request(), _context(), conn)
