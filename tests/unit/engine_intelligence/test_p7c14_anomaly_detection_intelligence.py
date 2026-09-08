"""tests/unit/engine_intelligence/test_p7c14_anomaly_detection_intelligence.py
=================================================================================
P7C.14 producer exercised end-to-end through the real IntelligenceKernel.
Proves: FABRIC/VALIDATION CRITICAL precedence overrides healthy throughput;
insufficient data is never presented as "no anomaly"; a real detected
collapse produces findings and ANOMALOUS overall status.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.anomaly_detection import (
    AnomalyDetectionInputs,
    make_anomaly_detection_producer,
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
    kernel.register_producer(IntelligenceTask.ASSESS, make_anomaly_detection_producer(resolver), capability="anomaly_detection")
    return kernel


def _request(subject_id="mig-1") -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.ASSESS, tenant_id="tenant-a", subject_type="migration",
        subject_id=subject_id, subject_version="v1", requested_by="user-1", capability="anomaly_detection",
    )


def _context(subject_id="mig-1") -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id=subject_id, subject_version="v1")


class TestGovernancePrecedence:
    def test_fabric_critical_overrides_healthy_throughput(self, conn):
        inputs = AnomalyDetectionInputs(
            tenant_id="tenant-a", migration_id="mig-1",
            current_dimensions={"throughput_rows_per_sec": 1000.0},
            historical_dimensions=[{"throughput_rows_per_sec": v} for v in [990, 1010, 995, 1005]],
            runtime_health_overall_status="CRITICAL",
            runtime_health_dimensions={"FABRIC": {"status": "CRITICAL"}, "VALIDATION": {"status": "UNKNOWN"}},
        )
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["overall_status"] == "ANOMALOUS"
        assert any(f["code"] == "ANOMALY:GOVERNANCE_CRITICAL_PRECEDENCE" for f in artifact.result["findings"])


class TestInsufficientDataNeverBecomesNoAnomaly:
    def test_no_history_reports_insufficient_data_not_none(self, conn):
        inputs = AnomalyDetectionInputs(tenant_id="tenant-a", migration_id="mig-1", current_dimensions={})
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["overall_status"] == "INSUFFICIENT_DATA"


class TestRealCollapseDetected:
    def test_throughput_collapse_produces_anomalous_with_findings(self, conn):
        inputs = AnomalyDetectionInputs(
            tenant_id="tenant-a", migration_id="mig-1",
            current_dimensions={"throughput_rows_per_sec": 50.0},
            historical_dimensions=[{"throughput_rows_per_sec": v} for v in [1000, 980, 1020, 990, 1010]],
            runtime_health_dimensions={"FABRIC": {"status": "UNKNOWN"}, "VALIDATION": {"status": "UNKNOWN"}},
        )
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["overall_status"] == "ANOMALOUS"
        assert any(f["code"] == "ANOMALY:THROUGHPUT_ROWS_PER_SEC" for f in artifact.result["findings"])
        assert artifact.result["epistemic_type"] == "DIAGNOSIS"


class TestCallerCannotForceHealthyViaEmptyResolver:
    def test_null_resolver_result_raises(self, conn):
        from akaalEngine.intelligence.models.errors import IntelligenceValidationError

        kernel = _kernel(lambda req, ctx: None)
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_request(), _context(), conn)
