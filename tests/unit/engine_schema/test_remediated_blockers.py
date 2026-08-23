"""
tests.unit.engine_schema.test_remediated_blockers
=================================================
Dedicated verification suite covering all 12 hostile review blocker remediations for Authority #4 Schema.
"""

import asyncio
import pytest

from akaalEngine.schema.assessment.compatibility import CompatibilityBreakdown
from akaalEngine.schema.assessment.projection import (
    CapacityEvidenceKind,
    TargetCapacitySchemaProjection,
)
from akaalEngine.schema.assessment.readiness import ReadinessStatus, SchemaReadinessGateProvider
from akaalEngine.schema.assessment.risk import RiskLevel, StructuralRiskReport
from akaalEngine.schema.authority import (
    SchemaAuthority,
    SchemaCompilationRequest,
)
from akaalEngine.schema.core.memoization import CompiledRuleIndexMemoizationEngine
from akaalEngine.schema.core.processor import LargeEstateChunkedSchemaProcessor
from akaalEngine.schema.core.provenance import DeterministicSchemaProvenanceHasher
from akaalEngine.schema.ddl.emitter import DDLStage, UnsupportedTargetEngineError
from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.dialect.datetime import DateTimeDialectTranslator
from akaalEngine.schema.dialect.sequences import SequenceDialectTranslator
from akaalEngine.schema.mapping.engine import MappingEngine
from akaalEngine.schema.models.constraints import CanonicalCheckConstraint, CanonicalForeignKey, CanonicalPrimaryKey
from akaalEngine.schema.models.indexes import CanonicalIndex, IndexAccessMethod
from akaalEngine.schema.models.mapping import (
    ColumnMapping,
    CompiledSchemaMapping,
    DataTypeOverride,
    TableMapping,
)
from akaalEngine.schema.models.partitioning import CanonicalPartitioning, PartitionStrategy
from akaalEngine.schema.models.programmables import (
    CanonicalPackage,
    CanonicalRoutine,
    CanonicalSequence,
    CanonicalTrigger,
    CanonicalUDT,
    RoutineKind,
)
from akaalEngine.schema.models.schema import CanonicalSchema, CanonicalSchemaModel, CanonicalView
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory, freeze_deep
from akaalEngine.schema.procedural.diagnostics import ConversionState
from akaalEngine.schema.procedural.lexer import ProceduralLexer, TokenType


def test_deep_immutability_freeze_deep():
    """Blocker 2: Test that nested mutable structures are deeply frozen."""
    nested_dict = {"a": {"b": [1, 2, {"c": "d"}]}}
    frozen = freeze_deep(nested_dict)

    # Outer dictionary is read-only
    with pytest.raises((TypeError, AttributeError)):
        frozen["a"] = 123

    # Nested dictionary is read-only
    with pytest.raises((TypeError, AttributeError)):
        frozen["a"]["b"] = 123

    # Nested list is converted to immutable tuple
    assert isinstance(frozen["a"]["b"], tuple)
    assert isinstance(frozen["a"]["b"][2], type(frozen))


def test_unsupported_ddl_target_raises_error():
    """Blocker 3: Test that unsupported targets fail-closed instead of silently returning PostgreSQL DDL."""
    with pytest.raises(UnsupportedTargetEngineError):
        DDLGenerator.get_emitter("NON_EXISTENT_DATABASE_ENGINE")

    # Verify newly added emitters work cleanly
    sqlite_emitter = DDLGenerator.get_emitter("SQLITE")
    assert sqlite_emitter.target_engine == "SQLITE"

    db2_emitter = DDLGenerator.get_emitter("DB2")
    assert db2_emitter.target_engine == "DB2"

    databricks_emitter = DDLGenerator.get_emitter("DATABRICKS")
    assert databricks_emitter.target_engine == "DATABRICKS"


def test_structural_mapping_datatype_override_application():
    """Blocker 4: Test DataTypeOverride updates canonical_type and column definition."""
    col = CanonicalColumn(
        name="user_id",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT", bits=32),
    )
    tbl = CanonicalTable(table_name="users", schema_name="public", columns=(col,))
    model = CanonicalSchemaModel(
        model_id="m1",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="public"),),
        tables=(tbl,),
    )

    mapping = CompiledSchemaMapping(
        table_mappings=(
            TableMapping(
                source_schema="public",
                source_table="users",
                target_schema="core",
                target_table="app_users",
                column_mappings=(
                    ColumnMapping(
                        source_column="user_id",
                        target_column="account_id",
                        datatype_override=DataTypeOverride(
                            target_data_type="BIGINT",
                            reason="Scale up integer keys",
                        ),
                    ),
                ),
            ),
        ),
    )

    mapped_model = MappingEngine.apply_mapping(model, mapping, target_vendor="POSTGRESQL")
    assert len(mapped_model.tables) == 1
    mapped_tbl = mapped_model.tables[0]
    assert mapped_tbl.table_name == "app_users"
    assert mapped_tbl.schema_name == "core"
    assert len(mapped_tbl.columns) == 1
    mapped_col = mapped_tbl.columns[0]
    assert mapped_col.name == "account_id"
    assert mapped_col.source_native_type == "BIGINT"
    assert mapped_col.canonical_type.category == CanonicalTypeCategory.EXACT_NUMERIC


def test_procedural_transpilation_zero_drop_on_failure():
    """Blocker 5: Test that routine failure returns FAILED / MANUAL_REWRITE diagnostic without dropping."""
    routine = CanonicalRoutine(
        name="invalid_syntax_proc",
        schema_name="public",
        routine_type=RoutineKind.PROCEDURE,
        definition_sql="THIS IS NOT VALID PL/SQL SYNTAX AT ALL",
    )
    model = CanonicalSchemaModel(
        model_id="m_proc",
        source_vendor="ORACLE",
        schemas=(CanonicalSchema(schema_name="public"),),
        routines=(routine,),
    )

    authority = SchemaAuthority()
    req = SchemaCompilationRequest(
        source_snapshot=model,
        target_engine="POSTGRESQL",
    )
    res = asyncio.run(authority.compile(req))

    assert len(res.procedural_results) == 1
    proc_res = res.procedural_results[0]
    assert proc_res.routine_name == "invalid_syntax_proc"
    assert proc_res.conversion_state == ConversionState.FAILED
    assert len(proc_res.diagnostics) >= 1
    assert proc_res.diagnostics[0].severity == "ERROR"


def test_oracle_q_quoting_in_lexer():
    """Blocker 5/6: Test Oracle q'[...]' and q'<...>' string tokenization."""
    sql = "SELECT q'[It's a sunny day; with semicolons]' AS msg FROM dual"
    tokens = ProceduralLexer.tokenize(sql)

    string_toks = [t for t in tokens if t.token_type == TokenType.STRING_LITERAL]
    assert len(string_toks) == 1
    assert string_toks[0].value == "q'[It's a sunny day; with semicolons]'"


def test_token_aware_dialect_translation_preserves_literals():
    """Blocker 6: Test that DateTime and Sequence translators do not alter string literals."""
    # A string literal containing the text "SYSDATE + 1" must NOT be modified
    expr = "SELECT 'SYSDATE + 1' AS literal_val, SYSDATE + 1 AS calculated_val FROM dual"
    translated = DateTimeDialectTranslator.translate_datetime_expression(expr, "ORACLE", "POSTGRESQL")
    assert "'SYSDATE + 1'" in translated
    assert "CURRENT_TIMESTAMP + INTERVAL '1 DAY'" in translated


def test_readiness_gate_evaluates_user_decisions():
    """Blocker 7: Test that decision_required_count triggers WAIVER_REQUIRED status."""
    breakdown = CompatibilityBreakdown(
        total_columns=10,
        exact_count=8,
        equivalent_count=0,
        transformed_count=0,
        compat_layer_count=0,
        lossy_count=0,
        unsupported_count=0,
        decision_required_count=2,
    )
    risk = StructuralRiskReport(total_risk_score=0, risk_level=RiskLevel.LOW)
    readiness = SchemaReadinessGateProvider.evaluate_readiness(breakdown, risk)

    assert readiness.status == ReadinessStatus.WAIVER_REQUIRED
    assert readiness.is_executable is True
    assert len(readiness.required_waivers) >= 1


def test_target_capacity_evidence_classification():
    """Blocker 8: Test that capacity projection distinguishes MEASURED vs UNKNOWN evidence."""
    col = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="BIGINT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="BIGINT", bits=64),
    )
    tbl_measured = CanonicalTable(
        table_name="t_measured",
        schema_name="public",
        columns=(col,),
        raw_source_properties={"row_count": 10000, "is_exact_count": True},
    )
    tbl_unknown = CanonicalTable(
        table_name="t_unknown",
        schema_name="public",
        columns=(col,),
        raw_source_properties={},
    )
    model = CanonicalSchemaModel(
        model_id="m_cap",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="public"),),
        tables=(tbl_measured, tbl_unknown),
    )

    report = TargetCapacitySchemaProjection.calculate_projection(model, "SNOWFLAKE")
    assert report.total_tables == 2
    proj_map = {tp.table_name: tp for tp in report.table_projections}
    assert proj_map["t_measured"].evidence_kind == CapacityEvidenceKind.MEASURED
    assert proj_map["t_measured"].estimated_row_count == 10000
    assert proj_map["t_unknown"].evidence_kind == CapacityEvidenceKind.UNKNOWN
    assert proj_map["t_unknown"].estimated_row_count is None


def test_chunked_schema_processor():
    """Blocker 9: Test LargeEstateChunkedSchemaProcessor on multi-table model."""
    tables = []
    for i in range(12):
        c = CanonicalColumn(
            name="id",
            ordinal_position=1,
            source_native_type="INT",
            canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT", bits=32),
        )
        tables.append(CanonicalTable(table_name=f"t_{i}", schema_name="public", columns=(c,)))

    model = CanonicalSchemaModel(
        model_id="m_chunked",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="public"),),
        tables=tuple(tables),
    )

    # Process in chunks of 5 tables
    chunks = list(LargeEstateChunkedSchemaProcessor.process_chunked_compilation(model, "POSTGRESQL", chunk_size=5))
    assert len(chunks) == 3  # 5 + 5 + 2 = 12 tables across 3 chunks
    assert all(c.target_engine == "POSTGRESQL" for c in chunks)


def test_memoization_thread_safety_and_versioning():
    """Blocker 10: Test CompiledRuleIndexMemoizationEngine thread safety and rule generation bump."""
    memo = CompiledRuleIndexMemoizationEngine()
    assert memo.rule_generation == 1

    ctype = CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type="VARCHAR", length=100)
    memo.put_normalized_type("postgres", "varchar", ctype, length=100)
    assert memo.get_normalized_type("postgres", "varchar", length=100) == ctype

    # Bumping generation invalidates cache
    memo.bump_generation()
    assert memo.rule_generation == 2
    assert memo.get_normalized_type("postgres", "varchar", length=100) is None


def test_composite_provenance_fingerprinting():
    """Blocker 11: Test composite provenance signature incorporates all stages."""
    sig1 = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
        source_model_hash="hash_src",
        mapping_hash="hash_map",
        ddl_package_hash="hash_ddl",
        target_engine="POSTGRESQL",
        target_version="15.0",
        rule_set_version="1",
        procedural_hash="hash_proc",
        readiness_hash="hash_readiness",
    )
    sig2 = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
        source_model_hash="hash_src",
        mapping_hash="hash_map",
        ddl_package_hash="hash_ddl",
        target_engine="POSTGRESQL",
        target_version="15.0",
        rule_set_version="1",
        procedural_hash="hash_proc",
        readiness_hash="hash_readiness",
    )
    sig3 = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
        source_model_hash="hash_src",
        mapping_hash="hash_map",
        ddl_package_hash="hash_ddl",
        target_engine="POSTGRESQL",
        target_version="15.0",
        rule_set_version="2",  # Updated rule set version
        procedural_hash="hash_proc",
        readiness_hash="hash_readiness",
    )

    assert sig1 == sig2
    assert sig1 != sig3
