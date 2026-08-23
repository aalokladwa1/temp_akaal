"""
tests.unit.engine_schema.test_lossiness_17_reason_codes
=======================================================
Unit tests proving all 17 standardized machine-readable lossiness reason codes (SCH-064).
"""

import pytest

from akaalEngine.schema.assessment.lossiness import LossinessAssessment, LossinessEngine, LossinessReasonCode
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory, ConversionSafety, TargetTypeEmission


def test_17_standardized_reason_codes_defined():
    expected_codes = {
        "TARGET_PRECISION_INSUFFICIENT",
        "SCALE_REDUCTION_LOSSY",
        "STRING_TRUNCATION_RISK",
        "TIMEZONE_SEMANTICS_LOSSY",
        "BINARY_LENGTH_LIMITATION",
        "UNSUPPORTED_TYPE_CONVERSION",
        "FLOATING_POINT_IMPRECISION",
        "UNSIGNED_TO_SIGNED_OVERFLOW",
        "BIT_WIDTH_NARROWING",
        "JSON_DOCUMENT_FALLBACK",
        "ARRAY_ELEMENT_LOSS",
        "SPATIAL_SRID_UNSUPPORTED",
        "VECTOR_DIMENSION_MISMATCH",
        "UDT_STRUCTURE_FLATTENED",
        "LOB_STORAGE_DEGRADED",
        "COLLATION_NORMALIZED",
        "NULLABILITY_RELAXED",
    }
    actual_codes = {e.value for e in LossinessReasonCode}
    assert actual_codes == expected_codes
    assert len(actual_codes) == 17


def test_lossiness_engine_evaluation():
    ctype = CanonicalType(
        category=CanonicalTypeCategory.EXACT_NUMERIC,
        raw_vendor_type="NUMBER(38,10)",
        precision=38,
        scale=10,
    )
    emission = TargetTypeEmission(
        target_engine="MYSQL",
        target_native_type="DECIMAL(10,2)",
        safety=ConversionSafety.LOSSY,
        lossiness_reasons=(
            "TARGET_PRECISION_INSUFFICIENT",
            "SCALE_REDUCTION_LOSSY",
        ),
        warning_message="Precision reduced from 38 to 10; Scale reduced from 10 to 2",
    )

    assessment = LossinessEngine.assess_column("orders.total", ctype, emission)
    assert assessment.column_name == "orders.total"
    assert assessment.safety == ConversionSafety.LOSSY
    assert LossinessReasonCode.TARGET_PRECISION_INSUFFICIENT in assessment.reasons
    assert LossinessReasonCode.SCALE_REDUCTION_LOSSY in assessment.reasons
    assert len(assessment.reasons) == 2
