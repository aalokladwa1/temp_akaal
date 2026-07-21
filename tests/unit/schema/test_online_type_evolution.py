"""
Unit tests for Feature 4 — Online Type Evolution.
"""

import pytest

from akaal.schema.domain.errors import ValidationError
from akaal.schema.domain.identifiers import SchemaIdentifier
from akaal.schema.type_evolution.engine import TypeEvolutionEngine
from akaal.schema.type_evolution.matrix import ConversionSafety, TypeCompatibilityMatrix
from akaal.schema.type_evolution.planner import ConversionPlanner


def test_type_matrix_widening_vs_narrowing():
    assert TypeCompatibilityMatrix.evaluate_conversion("INT", "BIGINT") == ConversionSafety.SAFE_WIDENING
    assert TypeCompatibilityMatrix.evaluate_conversion("BIGINT", "INT") == ConversionSafety.UNSAFE_NARROWING
    assert TypeCompatibilityMatrix.evaluate_conversion("VARCHAR(10)", "VARCHAR(50)") == ConversionSafety.SAFE_WIDENING
    assert TypeCompatibilityMatrix.evaluate_conversion("INT", "DATE") == ConversionSafety.INCOMPATIBLE


def test_conversion_planner_safe_and_narrowing_steps():
    planner = ConversionPlanner()
    target = SchemaIdentifier("public", "orders")

    plan_wide = planner.plan_conversion(target, "amount", "INT", "BIGINT")
    assert plan_wide.safety == ConversionSafety.SAFE_WIDENING
    assert len(plan_wide.forward_steps) == 1
    assert "TYPE BIGINT" in plan_wide.forward_steps[0].sql

    plan_narrow = planner.plan_conversion(target, "amount", "BIGINT", "INT")
    assert plan_narrow.safety == ConversionSafety.UNSAFE_NARROWING
    assert len(plan_narrow.forward_steps) == 4


def test_type_evolution_engine_incompatible_rejection():
    engine = TypeEvolutionEngine()
    target = SchemaIdentifier("public", "users")

    with pytest.raises(ValidationError):
        engine.plan_and_validate(target, "birth_date", "BOOLEAN", "TIMESTAMP")
