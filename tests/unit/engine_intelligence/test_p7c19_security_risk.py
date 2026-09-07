"""tests/unit/engine_intelligence/test_p7c19_security_risk.py
===================================================================
P7C.19: risk classification is derived only from real upstream
canonical-derived facts (FABRIC/VALIDATION/pending remediation) -- no
invented compliance rule, no risk reported without a supporting fact.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.security_risk import SecurityRiskInputs, make_security_risk_producer


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
    kernel.register_producer(IntelligenceTask.ASSESS, make_security_risk_producer(resolver), capability="security_risk_intelligence")
    return kernel


def _request() -> IntelligenceRequest:
    return IntelligenceRequest(
        task=IntelligenceTask.ASSESS, tenant_id="tenant-a", subject_type="migration",
        subject_id="mig-1", subject_version="v1", requested_by="user-1", capability="security_risk_intelligence",
    )


def _context() -> IntelligenceContext:
    return IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")


class TestNoFabricationWhenClean:
    def test_all_healthy_yields_zero_findings(self, conn):
        inputs = SecurityRiskInputs(tenant_id="tenant-a", migration_id="mig-1", fabric_status="HEALTHY", validation_status="HEALTHY")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert artifact.result["data"]["finding_count"] == 0
        assert artifact.result["data"]["risk_dimensions"] == []


class TestRealSignalsClassified:
    def test_fabric_critical_yields_security_residency_risk(self, conn):
        inputs = SecurityRiskInputs(tenant_id="tenant-a", migration_id="mig-1", fabric_status="CRITICAL")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert "SECURITY" in artifact.result["data"]["risk_dimensions"]
        assert "RESIDENCY" in artifact.result["data"]["risk_dimensions"]

    def test_validation_critical_yields_data_compliance_risk(self, conn):
        inputs = SecurityRiskInputs(tenant_id="tenant-a", migration_id="mig-1", validation_status="CRITICAL")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert "DATA" in artifact.result["data"]["risk_dimensions"]
        assert "COMPLIANCE" in artifact.result["data"]["risk_dimensions"]

    def test_pending_remediation_yields_operational_risk(self, conn):
        inputs = SecurityRiskInputs(tenant_id="tenant-a", migration_id="mig-1", pending_remediation_action_type="propose_remediation_pause_migration")
        kernel = _kernel(lambda req, ctx: inputs)
        artifact = kernel.submit_request(_request(), _context(), conn)
        assert "OPERATIONAL" in artifact.result["data"]["risk_dimensions"]


class TestNullResolverRefuses:
    def test_none_resolver_raises(self, conn):
        from akaalEngine.intelligence.models.errors import IntelligenceValidationError

        kernel = _kernel(lambda req, ctx: None)
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(_request(), _context(), conn)
