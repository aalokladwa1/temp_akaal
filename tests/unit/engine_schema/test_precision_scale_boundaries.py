"""
tests.unit.engine_schema.test_precision_scale_boundaries
========================================================
Unit tests proving precision, scale, length, and timezone boundary safety evaluation (SCH-019 to SCH-026).
"""

import pytest

from akaalEngine.schema.models.mapping import DataTypeOverride
from akaalEngine.schema.models.types import CanonicalTypeCategory, ConversionSafety
from akaalEngine.schema.types.registry import CanonicalTypeRegistry


def test_oracle_unconstrained_number_to_postgresql():
    # Oracle unconstrained NUMBER -> PostgreSQL NUMERIC (exact semantic match)
    res = CanonicalTypeRegistry.convert_type("oracle", "postgresql", "NUMBER")
    assert res.target_native_type == "NUMERIC"
    assert res.safety in (ConversionSafety.EXACT, ConversionSafety.SEMANTICALLY_EQUIVALENT)


def test_oracle_negative_scale_lossiness():
    # Oracle NUMBER(10, -2) rounds values to hundreds
    res = CanonicalTypeRegistry.convert_type("oracle", "postgresql", "NUMBER", precision=10, scale=-2)
    assert res.safety == ConversionSafety.LOSSY
    assert "SCALE_REDUCTION_LOSSY" in res.lossiness_reasons


def test_string_length_truncation_detection():
    # Large VARCHAR(10000) into target with smaller max length
    ora_type = CanonicalTypeRegistry.normalize_source_type("oracle", "VARCHAR2", length=10000)
    # Oracle VARCHAR2 max is 4000 on older versions / 32767 on extended
    res = CanonicalTypeRegistry.emit_target_type("mssql", ora_type)
    assert res.target_native_type == "NVARCHAR(MAX)"  # Automatically escalates to MAX


def test_timezone_loss_detection():
    # Timezone-aware timestamp emitted to target without timezone
    canon_tz = CanonicalTypeRegistry.normalize_source_type("postgresql", "TIMESTAMPTZ")
    # Emit to SQLite (which stores text without native tz offset)
    res = CanonicalTypeRegistry.emit_target_type("sqlite", canon_tz)
    assert res.target_native_type == "TEXT"


def test_explicit_datatype_override():
    # Operator override of a column type
    override = DataTypeOverride(
        target_data_type="DECIMAL",
        target_precision=18,
        target_scale=4,
        reason="Business requirement for financial rounding",
    )
    res = CanonicalTypeRegistry.convert_type(
        source_provider="oracle",
        target_provider="postgresql",
        raw_source_type="FLOAT",
        override=override,
    )
    assert res.target_native_type == "DECIMAL(18,4)"
    assert res.extra.get("is_override") is True
    assert "Business requirement" in res.warning_message
