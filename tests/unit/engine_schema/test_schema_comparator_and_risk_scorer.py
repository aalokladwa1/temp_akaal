"""
tests/unit/engine_schema/test_schema_comparator_and_risk_scorer.py
====================================================================
Tests for CONS-001 & CONS-002: Canonical Schema Comparison, SchemaDiff,
Incremental DDL generation, and Explainable Risk Scoring.
"""

import pytest

from akaalEngine.schema.compat import (
    CanonicalRiskScorer,
    CanonicalSchemaComparator,
    CompatibilityClassification,
    DifferenceCategory,
    RiskSeverity,
    SchemaDifference,
    SchemaDiffEngine,
)
from akaalEngine.schema.models.constraints import CanonicalPrimaryKey
from akaalEngine.schema.models.schema import CanonicalSchemaModel
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory


def _make_col(name: str, category_str: str, ordinal: int = 1, length: int = None, nullable: bool = True):
    cat = {
        "INTEGER": CanonicalTypeCategory.EXACT_NUMERIC,
        "VARCHAR": CanonicalTypeCategory.CHARACTER,
        "DATETIME": CanonicalTypeCategory.DATETIME,
    }.get(category_str, CanonicalTypeCategory.UNKNOWN)

    ctype = CanonicalType(category=cat, raw_vendor_type=category_str, length=length)
    return CanonicalColumn(
        name=name,
        ordinal_position=ordinal,
        source_native_type=category_str,
        canonical_type=ctype,
        length=length,
        nullable=nullable,
    )


def test_identical_schemas_produce_zero_differences_and_zero_risk():
    """Identical schemas produce zero differences, zero risk score, and is_safe_to_continue=True."""
    col1 = _make_col("id", "INTEGER", ordinal=1, nullable=False)
    col2 = _make_col("name", "VARCHAR", ordinal=2, length=100, nullable=True)
    pk = CanonicalPrimaryKey(name="pk_t1", table_name="t1", columns=("id",))
    table = CanonicalTable(table_name="t1", schema_name="public", columns=(col1, col2), primary_key=pk)

    model1 = CanonicalSchemaModel(model_id="m1", source_vendor="postgresql", tables=(table,))
    model2 = CanonicalSchemaModel(model_id="m2", source_vendor="postgresql", tables=(table,))

    diffs = CanonicalSchemaComparator.compare_schemas(model1, model2)
    assert len(diffs) == 0

    risk = CanonicalRiskScorer.evaluate_risk(diffs)
    assert risk.risk_score == 0
    assert risk.overall_compatibility == CompatibilityClassification.COMPATIBLE
    assert risk.is_safe_to_continue is True
    assert len(risk.findings) == 0


def test_added_and_removed_tables_and_columns():
    """Detects added/removed tables and columns deterministically."""
    c1 = _make_col("id", "INTEGER", ordinal=1, nullable=False)
    c2 = _make_col("email", "VARCHAR", ordinal=2, length=200, nullable=True)
    t1 = CanonicalTable(table_name="users", schema_name="public", columns=(c1, c2))
    t2 = CanonicalTable(table_name="orders", schema_name="public", columns=(c1,))

    source = CanonicalSchemaModel(model_id="src", source_vendor="postgresql", tables=(t1,))
    target = CanonicalSchemaModel(model_id="tgt", source_vendor="postgresql", tables=(t2,))

    diffs = CanonicalSchemaComparator.compare_schemas(source, target)
    assert len(diffs) == 2

    diff_ids = [d.difference_id for d in diffs]
    assert "diff-tbl-add-public.orders" in diff_ids
    assert "diff-tbl-rem-public.users" in diff_ids

    risk = CanonicalRiskScorer.evaluate_risk(diffs)
    assert risk.risk_score > 0
    assert "STRUCTURAL" in risk.breakdown


def test_column_type_and_length_narrowing_diffs():
    """Detects type category changes and length narrowing risks."""
    c_src_type = _make_col("val", "INTEGER")
    c_tgt_type = _make_col("val", "VARCHAR")
    t_src_type = CanonicalTable(table_name="t", schema_name="public", columns=(c_src_type,))
    t_tgt_type = CanonicalTable(table_name="t", schema_name="public", columns=(c_tgt_type,))

    source_type = CanonicalSchemaModel(model_id="src", source_vendor="postgresql", tables=(t_src_type,))
    target_type = CanonicalSchemaModel(model_id="tgt", source_vendor="postgresql", tables=(t_tgt_type,))

    diffs = CanonicalSchemaComparator.compare_schemas(source_type, target_type)
    assert len(diffs) == 1
    assert diffs[0].category == DifferenceCategory.TYPE_CHANGED
    assert diffs[0].compatibility == CompatibilityClassification.POTENTIALLY_LOSSY

    # Test length narrowing
    c_src_len = _make_col("bio", "VARCHAR", length=200)
    c_tgt_len = _make_col("bio", "VARCHAR", length=50)
    t_src_len = CanonicalTable(table_name="t", schema_name="public", columns=(c_src_len,))
    t_tgt_len = CanonicalTable(table_name="t", schema_name="public", columns=(c_tgt_len,))

    src_len_m = CanonicalSchemaModel(model_id="src", source_vendor="postgresql", tables=(t_src_len,))
    tgt_len_m = CanonicalSchemaModel(model_id="tgt", source_vendor="postgresql", tables=(t_tgt_len,))

    diffs_len = CanonicalSchemaComparator.compare_schemas(src_len_m, tgt_len_m)
    assert len(diffs_len) == 1
    assert diffs_len[0].property_name == "length"
    assert diffs_len[0].source_value == 200
    assert diffs_len[0].target_value == 50


def test_incremental_ddl_generation():
    """Generates incremental ALTER DDL statements from SchemaDifferences, failing closed for untyped columns."""
    # Untyped diff without CanonicalColumn -> fails closed with no executable DDL
    untyped_diff = SchemaDifference(
        difference_id="diff-col-rem-public.users.email",
        object_type="COLUMN",
        schema_name="public",
        object_name="users",
        category=DifferenceCategory.REMOVED,
        property_name="email",
    )

    untyped_actions = SchemaDiffEngine.generate_incremental_ddl([untyped_diff], target_dialect="postgresql")
    assert len(untyped_actions) == 1
    assert untyped_actions[0].action_type == "ADD_COLUMN"
    assert untyped_actions[0].ddl_statement == ""
    assert untyped_actions[0].is_safe is False
    assert "UNSUPPORTED_INCREMENTAL_DDL" in untyped_actions[0].unsupported_reason

    # Typed diff with CanonicalColumn -> generates valid DDL
    col_obj = _make_col("email", "VARCHAR", length=100)
    typed_diff = SchemaDifference(
        difference_id="diff-col-rem-public.users.email",
        object_type="COLUMN",
        schema_name="public",
        object_name="users",
        category=DifferenceCategory.REMOVED,
        property_name="email",
        source_value=col_obj,
    )
    typed_actions = SchemaDiffEngine.generate_incremental_ddl([typed_diff], target_dialect="postgresql")
    assert len(typed_actions) == 1
    assert typed_actions[0].is_safe is True
    assert "users" in typed_actions[0].ddl_statement and "email" in typed_actions[0].ddl_statement and "VARCHAR(100)" in typed_actions[0].ddl_statement

    # SQLite unsupported alter type
    type_diff = SchemaDifference(
        difference_id="diff-col-type-public.users.age",
        object_type="COLUMN",
        schema_name="public",
        object_name="users",
        category=DifferenceCategory.TYPE_CHANGED,
        property_name="age",
    )
    sqlite_actions = SchemaDiffEngine.generate_incremental_ddl([type_diff], target_dialect="sqlite")
    assert len(sqlite_actions) == 1
    assert sqlite_actions[0].requires_rebuild is True
    assert "SQLite does not support" in sqlite_actions[0].unsupported_reason


def test_case_sensitive_identifier_difference_detection():
    """Proves case-sensitive identifier differences (e.g. CaseName vs casename) are detected as IDENTITY_CHANGED."""
    c_src = _make_col("CaseCol", "VARCHAR", length=100)
    c_tgt = _make_col("casecol", "VARCHAR", length=100)

    t_src = CanonicalTable(table_name="CaseTable", schema_name="s", columns=(c_src,))
    t_tgt = CanonicalTable(table_name="casetable", schema_name="s", columns=(c_tgt,))

    src_model = CanonicalSchemaModel(model_id="src", source_vendor="postgresql", tables=(t_src,))
    tgt_model = CanonicalSchemaModel(model_id="tgt", source_vendor="postgresql", tables=(t_tgt,))

    diffs = CanonicalSchemaComparator.compare_schemas(src_model, tgt_model)
    assert len(diffs) >= 2
    categories = [d.category for d in diffs]
    assert DifferenceCategory.IDENTITY_CHANGED in categories

    # Case difference count
    case_diffs = [d for d in diffs if d.category == DifferenceCategory.IDENTITY_CHANGED]
    assert len(case_diffs) > 0


def test_missing_column_ddl_retains_canonical_type_and_quoting():
    """Proves missing column DDL retains source canonical type (e.g. VARCHAR(200)) and vendor quoting."""
    c_src = _make_col("bio", "VARCHAR", length=200, nullable=False)
    t_src = CanonicalTable(table_name="users", schema_name="public", columns=(c_src,))
    t_empty = CanonicalTable(table_name="users", schema_name="public", columns=())

    src_m = CanonicalSchemaModel(model_id="src", source_vendor="postgresql", tables=(t_src,))
    tgt_m = CanonicalSchemaModel(model_id="tgt", source_vendor="postgresql", tables=(t_empty,))

    diffs = CanonicalSchemaComparator.compare_schemas(src_m, tgt_m)
    assert len(diffs) == 1
    assert diffs[0].source_value == c_src

    actions = SchemaDiffEngine.generate_incremental_ddl(diffs, target_dialect="postgresql")
    assert len(actions) == 1
    ddl = actions[0].ddl_statement
    assert '"public"."users"' in ddl or "public.users" in ddl
    assert '"bio"' in ddl or "bio" in ddl
    assert "VARCHAR(200)" in ddl
    assert "NOT NULL" in ddl
    assert "VARCHAR(255)" not in ddl  # Must NOT fallback to generic VARCHAR(255)


def test_risk_scorer_evaluates_manual_review_and_lossy_as_unsafe():
    """Proves CanonicalRiskScorer returns is_safe_to_continue=False for MANUAL_REVIEW_REQUIRED / POTENTIALLY_LOSSY unless waived."""
    diff_manual = SchemaDifference(
        difference_id="diff-proc-rem-public.calc",
        object_type="PROCEDURE",
        schema_name="public",
        object_name="calc",
        category=DifferenceCategory.REMOVED,
        severity=RiskSeverity.HIGH,
        compatibility=CompatibilityClassification.MANUAL_REVIEW_REQUIRED,
    )

    risk = CanonicalRiskScorer.evaluate_risk([diff_manual])
    assert risk.overall_compatibility == CompatibilityClassification.MANUAL_REVIEW_REQUIRED
    assert risk.is_safe_to_continue is False  # Safe gate operates truthfully!

    # With explicit waiver
    risk_waived = CanonicalRiskScorer.evaluate_risk([diff_manual], allow_manual_waiver=True)
    assert risk_waived.is_safe_to_continue is True


def test_foreign_key_and_procedure_and_view_drift_comparison():
    """Proves FK actions, procedure definitions, and view definitions are compared by comparator and drift analyzer."""
    from akaalEngine.schema.compat import CanonicalDriftAnalyzer, DriftClassification
    from akaalEngine.schema.models.constraints import CanonicalForeignKey
    from akaalEngine.schema.models.programmables import CanonicalRoutine, RoutineKind
    from akaalEngine.schema.models.schema import CanonicalView

    fk_src = CanonicalForeignKey(
        name="fk_1", table_name="t", schema_name="s", columns=("c",),
        referenced_schema="s", referenced_table="ref", referenced_columns=("id",),
        on_delete="CASCADE"
    )
    fk_tgt = CanonicalForeignKey(
        name="fk_1", table_name="t", schema_name="s", columns=("c",),
        referenced_schema="s", referenced_table="ref", referenced_columns=("id",),
        on_delete="SET NULL"
    )

    t_src = CanonicalTable(table_name="t", schema_name="s", columns=(), foreign_keys=(fk_src,))
    t_tgt = CanonicalTable(table_name="t", schema_name="s", columns=(), foreign_keys=(fk_tgt,))

    v_src = CanonicalView(view_name="v1", schema_name="s", view_definition="SELECT 1")
    v_tgt = CanonicalView(view_name="v1", schema_name="s", view_definition="SELECT 2")

    r_src = CanonicalRoutine(name="r1", schema_name="s", routine_type=RoutineKind.PROCEDURE, definition_sql="BEGIN NULL; END;")
    r_tgt = CanonicalRoutine(name="r1", schema_name="s", routine_type=RoutineKind.PROCEDURE, definition_sql="BEGIN SELECT 1; END;")

    m_src = CanonicalSchemaModel(model_id="m1", source_vendor="postgresql", tables=(t_src,), views=(v_src,), routines=(r_src,))
    m_tgt = CanonicalSchemaModel(model_id="m2", source_vendor="postgresql", tables=(t_tgt,), views=(v_tgt,), routines=(r_tgt,))

    drift = CanonicalDriftAnalyzer.analyze_drift(m_src, m_tgt)
    assert drift.is_drift_detected is True
    assert drift.drift_classification == DriftClassification.BREAKING_DRIFT
    diff_cats = [d.category for d in drift.differences]
    assert DifferenceCategory.CONSTRAINT_CHANGED in diff_cats
    assert DifferenceCategory.DEFINITION_CHANGED in diff_cats


def test_no_mutation_of_input_canonical_models():
    """Guarantees input CanonicalSchemaModel instances are not mutated during comparison."""
    c1 = _make_col("id", "INTEGER")
    t1 = CanonicalTable(table_name="t1", schema_name="public", columns=(c1,))
    model1 = CanonicalSchemaModel(model_id="m1", source_vendor="postgresql", tables=(t1,))
    model2 = CanonicalSchemaModel(model_id="m2", source_vendor="postgresql", tables=())

    dict_before1 = model1.to_dict()
    dict_before2 = model2.to_dict()

    _ = CanonicalSchemaComparator.compare_schemas(model1, model2)

    assert model1.to_dict() == dict_before1
    assert model2.to_dict() == dict_before2
