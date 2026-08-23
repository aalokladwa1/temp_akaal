"""
tests.unit.engine_schema.test_assessment_readiness_risk
=======================================================
Unit tests for compatibility breakdown, risk scoring, readiness gates, and capacity projections (SCH-065 to SCH-068).
"""

import pytest

from akaalEngine.schema.assessment.compatibility import CompatibilityBreakdown, PreMigrationCompatibilityAssessor
from akaalEngine.schema.assessment.lossiness import LossinessAssessment, LossinessReasonCode
from akaalEngine.schema.assessment.projection import TargetCapacityReport, TargetCapacitySchemaProjection
from akaalEngine.schema.assessment.readiness import ReadinessGateReport, ReadinessStatus, SchemaReadinessGateProvider
from akaalEngine.schema.assessment.risk import RiskLevel, StructuralRiskReport, StructuralRiskScorer
from akaalEngine.schema.models.schema import CanonicalSchema, CanonicalSchemaModel
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory, ConversionSafety


def _create_test_schema_model():
    col1 = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="BIGINT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="BIGINT", bits=64),
        nullable=False,
    )
    col2 = CanonicalColumn(
        name="doc",
        ordinal_position=2,
        source_native_type="JSONB",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type="JSONB"),
    )
    col3 = CanonicalColumn(
        name="content_blob",
        ordinal_position=3,
        source_native_type="BLOB",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.LOB, raw_vendor_type="BLOB"),
        is_lob=True,
    )

    tbl = CanonicalTable(
        table_name="documents",
        schema_name="public",
        columns=(col1, col2, col3),
        raw_source_properties={"estimated_rows": 5000},
    )

    return CanonicalSchemaModel(
        model_id="assess_test_model",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="public"),),
        tables=(tbl,),
    )


def test_compatibility_assessment():
    model = _create_test_schema_model()
    breakdown = PreMigrationCompatibilityAssessor.assess_model(model, "POSTGRESQL")

    assert breakdown.total_columns == 3
    assert breakdown.unsupported_count == 0
    assert isinstance(breakdown.to_dict(), dict)


def test_structural_risk_scoring():
    model = _create_test_schema_model()
    breakdown = PreMigrationCompatibilityAssessor.assess_model(model, "POSTGRESQL")
    risk_report = StructuralRiskScorer.score_risk(model, breakdown)

    # 1 LOB column (+10 points) -> Total 10 points -> LOW risk
    assert risk_report.total_risk_score == 10
    assert risk_report.risk_level == RiskLevel.LOW
    assert len(risk_report.risk_factors) == 1
    assert risk_report.risk_factors[0].category == "LOB_COMPLEXITY"


def test_readiness_gate_evaluation():
    model = _create_test_schema_model()
    breakdown = PreMigrationCompatibilityAssessor.assess_model(model, "POSTGRESQL")
    risk_report = StructuralRiskScorer.score_risk(model, breakdown)
    readiness = SchemaReadinessGateProvider.evaluate_readiness(breakdown, risk_report)

    assert readiness.status == ReadinessStatus.READY
    assert readiness.is_executable is True
    assert len(readiness.blocking_reasons) == 0


def test_target_capacity_projection():
    model = _create_test_schema_model()
    report = TargetCapacitySchemaProjection.calculate_projection(model, "SNOWFLAKE")

    assert report.total_tables == 1
    assert report.total_estimated_rows == 5000
    assert report.total_projected_target_bytes > 0
    assert report.table_projections[0].estimated_compression_ratio == 0.35
