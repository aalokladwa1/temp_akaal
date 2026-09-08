"""tests/unit/engine_intelligence/test_p7c13_runtime_health_intelligence_state.py
====================================================================================
P7C.13 Runtime Health & Intelligence State: the dimensional health projection
producer, exercised end-to-end through the real IntelligenceKernel. Proves:
  - a fully healthy snapshot reports HEALTHY with full evidence coverage;
  - missing telemetry for a dimension reports UNKNOWN for that dimension, never
    a false HEALTHY (no missing-data-becomes-healthy defect);
  - a genuinely degraded/bottlenecked dimension is surfaced with a finding and
    folds into a non-HEALTHY overall status;
  - a CDC backlog with generation_rate <= 0 does not divide-by-zero into a
    fabricated status;
  - a stale snapshot (observed_at older than stale_after_seconds) is flagged as
    a contradiction rather than presented as current truth;
  - Fabric ownership/fencing violations are CRITICAL, not silently downgraded.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.runtime_health import (
    RuntimeHealthInputs,
    make_runtime_health_producer,
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


def _kernel_with_producer(resolver) -> IntelligenceKernel:
    kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
    kernel.register_producer(IntelligenceTask.QUERY, make_runtime_health_producer(resolver), capability="runtime_health")
    return kernel


def _request(subject_id="mig-1") -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.QUERY, tenant_id="tenant-a", subject_type="migration",
        subject_id=subject_id, subject_version="v1", requested_by="user-1",
        capability="runtime_health",
    )


def _context(subject_id="mig-1") -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id=subject_id, subject_version="v1")


class TestFullyHealthySnapshot:
    def test_all_dimensions_healthy_yields_healthy_overall_and_full_coverage(self, conn):
        inputs = RuntimeHealthInputs(
            migration_id="mig-1",
            transport={"throughput_rows_per_sec": 950, "baseline_rows_per_sec": 1000},
            cdc={"generation_rate": 100, "apply_rate": 98, "backlog_size": 10, "backlog_trend": "stable"},
            validation={"status": "HEALTHY", "mismatch_count": 0},
            workers={"total": 8, "healthy": 8},
            fabric={"ownership_valid": True, "lease_valid": True, "fencing_conflicts": 0},
            resources={"cpu_pct": 40, "memory_pct": 50, "storage_pct": 30, "staging_pct": 20},
            governance={"cutover_ready": True, "approvals_pending": 0, "security_blocking": False},
        )
        kernel = _kernel_with_producer(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["overall_status"] == "HEALTHY"
        assert artifact.result["confidence_evidence"]["evidence_coverage"] == 1.0
        assert artifact.result["findings"] == []
        assert artifact.result["epistemic_type"] == "DERIVED_FACT"


class TestMissingTelemetryNeverBecomesHealthy:
    def test_no_data_at_all_reports_unknown_not_healthy(self, conn):
        inputs = RuntimeHealthInputs(migration_id="mig-1")
        kernel = _kernel_with_producer(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["overall_status"] == "UNKNOWN"
        for dim in artifact.result["data"]["dimensions"].values():
            assert dim["status"] == "UNKNOWN"
        assert artifact.result["confidence_evidence"]["evidence_coverage"] == 0.0
        assert len(artifact.result["confidence_evidence"]["missing_information"]) == 7

    def test_partial_data_reports_mixed_coverage(self, conn):
        inputs = RuntimeHealthInputs(
            migration_id="mig-1",
            transport={"throughput_rows_per_sec": 900, "baseline_rows_per_sec": 1000},
        )
        kernel = _kernel_with_producer(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["dimensions"]["TRANSPORT"]["status"] == "HEALTHY"
        assert artifact.result["data"]["dimensions"]["CDC"]["status"] == "UNKNOWN"
        assert 0.0 < artifact.result["confidence_evidence"]["evidence_coverage"] < 1.0


class TestBottleneckDetection:
    def test_cdc_apply_far_below_generation_is_bottlenecked_and_findings_populated(self, conn):
        inputs = RuntimeHealthInputs(
            migration_id="mig-1",
            cdc={"generation_rate": 85000, "apply_rate": 52000, "backlog_size": 900000, "backlog_trend": "increasing"},
        )
        kernel = _kernel_with_producer(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["dimensions"]["CDC"]["status"] == "BOTTLENECKED"
        assert artifact.result["data"]["overall_status"] == "BOTTLENECKED"
        findings = artifact.result["findings"]
        assert any(f["code"].startswith("RUNTIME_HEALTH:CDC:") for f in findings)


class TestNonPositiveRateNoDivideByZero:
    def test_zero_generation_rate_reports_unknown_not_crash(self, conn):
        inputs = RuntimeHealthInputs(
            migration_id="mig-1",
            cdc={"generation_rate": 0, "apply_rate": 0, "backlog_size": 0, "backlog_trend": "stable"},
        )
        kernel = _kernel_with_producer(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["dimensions"]["CDC"]["status"] == "UNKNOWN"

    def test_negative_apply_rate_reports_unknown_not_crash(self, conn):
        inputs = RuntimeHealthInputs(
            migration_id="mig-1",
            cdc={"generation_rate": 100, "apply_rate": -5, "backlog_size": 0, "backlog_trend": "stable"},
        )
        kernel = _kernel_with_producer(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["dimensions"]["CDC"]["status"] == "UNKNOWN"


class TestStalenessSurfaced:
    def test_stale_snapshot_flagged_as_contradiction(self, conn):
        old = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
        inputs = RuntimeHealthInputs(
            migration_id="mig-1",
            transport={"throughput_rows_per_sec": 900, "baseline_rows_per_sec": 1000},
            observed_at=old,
            stale_after_seconds=60.0,
        )
        kernel = _kernel_with_producer(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        contradictions = artifact.result["explanation"]["contradictions"]
        assert any("STALE" in c for c in contradictions)


class TestFabricOwnershipViolationIsCritical:
    def test_invalid_ownership_is_critical_not_downgraded(self, conn):
        inputs = RuntimeHealthInputs(
            migration_id="mig-1",
            fabric={"ownership_valid": False, "lease_valid": True, "fencing_conflicts": 0},
        )
        kernel = _kernel_with_producer(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["dimensions"]["FABRIC"]["status"] == "CRITICAL"
        assert artifact.result["data"]["overall_status"] == "CRITICAL"


class TestNullResolverRefusesToFabricate:
    def test_resolver_returning_none_raises(self, conn):
        from akaalEngine.intelligence.models.errors import IntelligenceValidationError

        kernel = _kernel_with_producer(lambda req, ctx: None)
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_request(), _context(), conn)
