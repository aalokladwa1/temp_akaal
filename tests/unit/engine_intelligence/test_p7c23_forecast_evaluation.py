"""tests/unit/engine_intelligence/test_p7c23_forecast_evaluation.py
=========================================================================
P7C.23: real deterministic error/interval-hit computation; interval miss is
flagged as a finding, not silently absorbed; hard requires all inputs.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.forecast_evaluation import (
    ForecastEvaluationInputs,
    evaluate_forecast,
    make_forecast_evaluation_producer,
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


class TestPureMath:
    def test_interval_hit_true_within_bounds(self):
        r = evaluate_forecast(ForecastEvaluationInputs(metric_name="eta", predicted_value=100, predicted_low=80, predicted_high=120, actual_value=110))
        assert r["interval_hit"] is True
        assert r["error"] == 10

    def test_interval_miss_outside_bounds(self):
        r = evaluate_forecast(ForecastEvaluationInputs(metric_name="eta", predicted_value=100, predicted_low=80, predicted_high=120, actual_value=200))
        assert r["interval_hit"] is False


class TestProducer:
    def _kernel(self):
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(IntelligenceTask.COMPARE, make_forecast_evaluation_producer(), capability="forecast_evaluation")
        return kernel

    def test_missing_params_raises(self, conn):
        kernel = self._kernel()
        req = IntelligenceRequest(task=IntelligenceTask.COMPARE, tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1", requested_by="user-1", capability="forecast_evaluation", parameters={})
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(req, ctx, conn)

    def test_miss_produces_finding(self, conn):
        kernel = self._kernel()
        req = IntelligenceRequest(
            task=IntelligenceTask.COMPARE, tenant_id="tenant-a", subject_type="migration", subject_id="mig-1",
            subject_version="v1", requested_by="user-1", capability="forecast_evaluation",
            parameters={"metric_name": "migration_eta_seconds", "predicted_value": 100, "predicted_low": 80, "predicted_high": 120, "actual_value": 500},
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert any(f["code"] == "EVAL:INTERVAL_MISS" for f in artifact.result["findings"])
