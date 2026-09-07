"""tests/unit/engine_intelligence/test_p7c7_estate_assessment.py
====================================================================
P7C.7 Estate Assessment & Risk Intelligence: producer genuinely wraps the real
PreMigrationCompatibilityAssessor/StructuralRiskScorer engines end-to-end through
the IntelligenceKernel, against real heterogeneous provider metadata.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.estate_assessment import make_estate_assessment_producer
from akaalEngine.schema.models.schema import CanonicalSchemaModel
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory


def _clean_model() -> CanonicalSchemaModel:
    table = CanonicalTable(
        table_name="customers",
        schema_name="public",
        columns=(
            CanonicalColumn(
                name="id", ordinal_position=1, source_native_type="INTEGER",
                canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INTEGER"),
            ),
        ),
    )
    return CanonicalSchemaModel(model_id="model-clean", source_vendor="postgresql", tables=(table,))


def _risky_model() -> CanonicalSchemaModel:
    table = CanonicalTable(
        table_name="documents",
        schema_name="public",
        columns=(
            CanonicalColumn(
                name="geo", ordinal_position=1, source_native_type="GEOMETRY",
                canonical_type=CanonicalType(category=CanonicalTypeCategory.SPATIAL, raw_vendor_type="GEOMETRY"),
            ),
            CanonicalColumn(
                name="payload", ordinal_position=2, source_native_type="XMLTYPE",
                canonical_type=CanonicalType(category=CanonicalTypeCategory.XML, raw_vendor_type="XMLTYPE"),
            ),
        ),
    )
    return CanonicalSchemaModel(model_id="model-risky", source_vendor="oracle", tables=(table,))


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
    kernel.register_producer(IntelligenceTask.ASSESS, make_estate_assessment_producer(resolver))
    return kernel


class TestCleanSchemaAssessment:
    def test_fully_compatible_schema_reports_zero_blockers(self, conn):
        kernel = _kernel_with_producer(lambda req, ctx: _clean_model())
        req = IntelligenceRequest(
            task=IntelligenceTask.ASSESS, tenant_id="tenant-a", subject_type="migration_plan",
            subject_id="plan-1", subject_version="v1", requested_by="user-1",
            parameters={"target_engine": "postgresql"},
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert artifact.result["data"]["is_compatible"] is True
        assert artifact.result["data"]["blocker_count"] == 0
        assert artifact.result["epistemic_type"] == "DIAGNOSIS"


class TestRiskySchemaAssessment:
    def test_unsupported_types_produce_high_severity_findings(self, conn):
        kernel = _kernel_with_producer(lambda req, ctx: _risky_model())
        req = IntelligenceRequest(
            task=IntelligenceTask.ASSESS, tenant_id="tenant-a", subject_type="migration_plan",
            subject_id="plan-2", subject_version="v1", requested_by="user-1",
            parameters={"target_engine": "mysql"},
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-2", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert artifact.result["data"]["is_compatible"] is False
        assert artifact.result["data"]["compatibility_breakdown"]["unsupported_count"] == 2
        findings = artifact.result["findings"]
        assert any(f["severity"] == "HIGH" for f in findings)

    def test_findings_carry_evidence_not_bare_opinion(self, conn):
        """Every finding must be traceable to the deterministic risk engine's own
        output -- proving these are DERIVED_FACT/DIAGNOSIS, not model opinion."""
        kernel = _kernel_with_producer(lambda req, ctx: _risky_model())
        req = IntelligenceRequest(
            task=IntelligenceTask.ASSESS, tenant_id="tenant-a", subject_type="migration_plan",
            subject_id="plan-2", subject_version="v1", requested_by="user-1",
            parameters={"target_engine": "mysql"},
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-2", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert len(artifact.result["explanation"]["supporting_facts"]) >= 3
        assert artifact.result["confidence_evidence"]["evidence_coverage"] == 1.0


class TestMissingTargetEngine:
    def test_missing_target_engine_raises_not_silently_assessed(self, conn):
        kernel = _kernel_with_producer(lambda req, ctx: _clean_model())
        req = IntelligenceRequest(
            task=IntelligenceTask.ASSESS, tenant_id="tenant-a", subject_type="migration_plan",
            subject_id="plan-1", subject_version="v1", requested_by="user-1",
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(req, ctx, conn)


class TestHeterogeneousProviderCoverage:
    @pytest.mark.parametrize("target_engine", ["postgresql", "mysql", "sqlite"])
    def test_multiple_target_providers_all_produce_valid_reports(self, conn, target_engine):
        """Not hardcoded to a single Oracle->Postgres pair -- covers multiple
        provider types already supported by AKAAL."""
        kernel = _kernel_with_producer(lambda req, ctx: _clean_model())
        req = IntelligenceRequest(
            task=IntelligenceTask.ASSESS, tenant_id="tenant-a", subject_type="migration_plan",
            subject_id=f"plan-{target_engine}", subject_version="v1", requested_by="user-1",
            parameters={"target_engine": target_engine},
        )
        ctx = IntelligenceContext(
            tenant_id="tenant-a", subject_type="migration_plan", subject_id=f"plan-{target_engine}", subject_version="v1"
        )
        artifact = kernel.submit_request(req, ctx, conn)
        assert "compatibility_breakdown" in artifact.result["data"]
