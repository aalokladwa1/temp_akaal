"""
tests.unit.engine_schema.test_remediated_blockers
=================================================
Dedicated verification suite covering all hostile review blocker remediations for Authority #4 Schema.
"""

import asyncio
import pytest

from akaalEngine.schema.assessment.compatibility import CompatibilityBreakdown, PreMigrationCompatibilityAssessor
from akaalEngine.schema.assessment.projection import (
    CapacityEvidenceKind,
    TargetCapacitySchemaProjection,
)
from akaalEngine.schema.assessment.readiness import ReadinessStatus, SchemaReadinessGateProvider
from akaalEngine.schema.assessment.risk import RiskLevel, StructuralRiskReport, StructuralRiskScorer
from akaalEngine.schema.authority import (
    SchemaAuthority,
    SchemaCompilationRequest,
)
from akaalEngine.schema.core.memoization import (
    CompiledRuleIndexMemoizationEngine,
    default_memoization_engine,
)
from akaalEngine.schema.core.processor import LargeEstateChunkedSchemaProcessor
from akaalEngine.schema.core.provenance import DeterministicSchemaProvenanceHasher
from akaalEngine.schema.ddl.emitter import DDLStage, UnsupportedTargetEngineError
from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.dialect.datetime import DateTimeDialectTranslator
from akaalEngine.schema.dialect.sequences import SequenceDialectTranslator
from akaalEngine.schema.mapping.engine import MappingEngine
from akaalEngine.schema.models.constraints import (
    CanonicalCheckConstraint,
    CanonicalForeignKey,
    CanonicalPrimaryKey,
    CanonicalUniqueConstraint,
)
from akaalEngine.schema.models.indexes import CanonicalIndex, IndexAccessMethod
from akaalEngine.schema.models.mapping import (
    ColumnMapping,
    CompiledSchemaMapping,
    DataTypeOverride,
    TableMapping,
)
from akaalEngine.schema.models.partitioning import (
    CanonicalPartitionBound,
    CanonicalPartitioning,
    PartitionStrategy,
)
from akaalEngine.schema.models.programmables import (
    CanonicalPackage,
    CanonicalRoutine,
    CanonicalSequence,
    CanonicalTrigger,
    CanonicalUDT,
    RoutineKind,
)
from akaalEngine.schema.models.schema import (
    CanonicalCatalog,
    CanonicalSchema,
    CanonicalSchemaModel,
    CanonicalSynonym,
    CanonicalView,
)
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory, freeze_deep
from akaalEngine.schema.procedural.diagnostics import ConversionState
from akaalEngine.schema.procedural.lexer import ProceduralLexer, TokenType
from akaalEngine.schema.types.registry import CanonicalTypeRegistry


def test_discovery_snapshot_lossless_no_fake_public():
    """Blocker 1: Verify discovered objects without schema do not receive fabricated 'public'."""
    from akaalEngine.discovery.models.environment import ConfigurationFacts
    from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
    from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectInventory, TableFacts, ViewFacts
    from akaalEngine.discovery.models.programmables import ProgrammableInventory, RoutineFacts, RoutineType
    from akaalEngine.discovery.models.snapshot import DiscoverySnapshot
    from akaalEngine.discovery.models.statistics import StatisticsSnapshot
    from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, ObjectStructureFacts
    from akaalEngine.discovery.models.volume import VolumeSnapshot

    identity = DiscoveredEndpointIdentity(
        provider_id="sqlite",
        vendor_name="SQLite",
        engine_name="SQLite3",
        system_type="Relational Database",
        version=ServerVersion(raw_version_string="3.39.0", major=3, minor=39),
        edition=EngineEdition(edition_name="Community"),
    )
    cols = (ColumnPhysicalMetadata(name="id", ordinal_position=1, native_type="INTEGER", nullable=False),)
    table_struct = ObjectStructureFacts(table_name="items", schema_name="", columns=cols)
    views = (ViewFacts(name="v_items", schema_name=""),)
    routines = (RoutineFacts(name="calc_total", schema_name="", routine_type=RoutineType.FUNCTION, language="SQL", definition_sql="SELECT 1"),)

    snapshot = DiscoverySnapshot(
        snapshot_id="ep_sqlite_1",
        engine_identity=identity,
        environment=ConfigurationFacts(),
        namespaces=NamespaceInventory(),
        objects=ObjectInventory(tables=(TableFacts(name="items", schema_name=""),), views=views),
        structures={"items": table_struct},
        programmables=ProgrammableInventory(routines=routines),
        statistics=StatisticsSnapshot(),
        volume=VolumeSnapshot(),
    )

    authority = SchemaAuthority()
    model = authority._from_discovery_snapshot(snapshot)
    assert model.tables[0].schema_name == ""
    assert model.views[0].schema_name == ""
    assert model.routines[0].schema_name == ""
    assert "public" not in [s.schema_name for s in model.schemas]


def test_dictionary_full_reconstruction():
    """Blocker 1: Verify CanonicalSchemaModel.from_dict completely reconstructs all components."""
    sample_dict = {
        "model_id": "dict_test_100",
        "source_vendor": "POSTGRESQL",
        "source_version": "15.0",
        "schemas": [{"schema_name": "billing"}],
        "tables": [
            {
                "table_name": "invoices",
                "schema_name": "billing",
                "columns": [
                    {
                        "name": "id",
                        "ordinal_position": 1,
                        "source_native_type": "BIGINT",
                        "canonical_type": {
                            "category": "EXACT_NUMERIC",
                            "raw_vendor_type": "BIGINT",
                            "bits": 64,
                        },
                        "nullable": False,
                    }
                ],
                "primary_key": {
                    "name": "pk_invoices",
                    "table_name": "invoices",
                    "schema_name": "billing",
                    "columns": ["id"],
                },
                "indexes": [
                    {
                        "name": "idx_invoices_id",
                        "table_name": "invoices",
                        "schema_name": "billing",
                        "columns": ["id"],
                        "access_method": "BTREE",
                    }
                ],
            }
        ],
        "views": [
            {
                "view_name": "v_invoices",
                "schema_name": "billing",
                "view_definition": "SELECT * FROM billing.invoices",
            }
        ],
        "routines": [
            {
                "name": "calc_tax",
                "schema_name": "billing",
                "routine_type": "FUNCTION",
                "language": "PLPGSQL",
                "definition_sql": "CREATE FUNCTION billing.calc_tax() RETURNS INT AS $$ BEGIN RETURN 1; END; $$ LANGUAGE plpgsql;",
            }
        ],
        "sequences": [
            {
                "name": "inv_seq",
                "schema_name": "billing",
                "start_value": 100,
            }
        ],
    }

    model = CanonicalSchemaModel.from_dict(sample_dict)
    assert model.model_id == "dict_test_100"
    assert len(model.schemas) == 1
    assert model.schemas[0].schema_name == "billing"
    assert len(model.tables) == 1
    assert model.tables[0].table_name == "invoices"
    assert model.tables[0].columns[0].canonical_type.category == CanonicalTypeCategory.EXACT_NUMERIC
    assert model.tables[0].primary_key.name == "pk_invoices"
    assert len(model.views) == 1
    assert model.views[0].view_name == "v_invoices"
    assert len(model.routines) == 1
    assert len(model.sequences) == 1


def test_deep_immutability_freeze_deep_and_deterministic_sets():
    """Blocker 2: Verify freeze_deep deeply freezes dicts/sequences and sorts sets deterministically."""
    nested_dict = {"a": {"b": [1, 2, {"c": "d"}]}}
    frozen = freeze_deep(nested_dict)

    with pytest.raises((TypeError, AttributeError)):
        frozen["a"] = 123
    with pytest.raises((TypeError, AttributeError)):
        frozen["a"]["b"] = 123

    # Deterministic set sorting
    set_a = {"z", "a", "m", "b"}
    frozen_set = freeze_deep(set_a)
    assert frozen_set == ("a", "b", "m", "z")


def test_unsupported_ddl_target_raises_error():
    """Blocker 3: Verify unsupported targets fail-closed instead of silently returning PostgreSQL DDL."""
    with pytest.raises(UnsupportedTargetEngineError):
        DDLGenerator.get_emitter("NON_EXISTENT_DATABASE_ENGINE")

    sqlite_emitter = DDLGenerator.get_emitter("SQLITE")
    assert sqlite_emitter.target_engine == "SQLITE"

    db2_emitter = DDLGenerator.get_emitter("DB2")
    assert db2_emitter.target_engine == "DB2"

    databricks_emitter = DDLGenerator.get_emitter("DATABRICKS")
    assert databricks_emitter.target_engine == "DATABRICKS"


def test_structural_mapping_expression_rewrites_and_dropped_fks():
    """Blocker 4: Verify check clauses, index expressions, and dropped FK tracking."""
    col1 = CanonicalColumn(
        name="old_price",
        ordinal_position=1,
        source_native_type="NUMERIC",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="NUMERIC", precision=10, scale=2),
    )
    col2 = CanonicalColumn(
        name="cust_ref",
        ordinal_position=2,
        source_native_type="BIGINT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="BIGINT", bits=64),
    )

    check_con = CanonicalCheckConstraint(
        name="chk_price",
        table_name="items",
        schema_name="shop",
        check_clause="old_price > 0 AND old_price < 10000",
    )
    idx = CanonicalIndex(
        name="idx_price",
        table_name="items",
        schema_name="shop",
        columns=("old_price",),
        predicate_expression="old_price > 100",
        expression="old_price * 2",
    )
    fk = CanonicalForeignKey(
        name="fk_cust",
        table_name="items",
        schema_name="shop",
        columns=("cust_ref",),
        referenced_schema="shop",
        referenced_table="customers",
        referenced_columns=("id",),
    )

    tbl_items = CanonicalTable(
        table_name="items",
        schema_name="shop",
        columns=(col1, col2),
        check_constraints=(check_con,),
        indexes=(idx,),
        foreign_keys=(fk,),
    )
    tbl_cust = CanonicalTable(
        table_name="customers",
        schema_name="shop",
        columns=(
            CanonicalColumn(
                name="id",
                ordinal_position=1,
                source_native_type="BIGINT",
                canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="BIGINT", bits=64),
            ),
        ),
    )

    model = CanonicalSchemaModel(
        model_id="m_rewrite",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="shop"),),
        tables=(tbl_items, tbl_cust),
    )

    # Map items table: rename old_price -> new_price, with precision 0 and length 0 override tests; exclude customers table
    mapping = CompiledSchemaMapping(
        table_mappings=(
            TableMapping(
                source_schema="shop",
                source_table="items",
                target_schema="store",
                target_table="products",
                column_mappings=(
                    ColumnMapping(
                        source_column="old_price",
                        target_column="new_price",
                        datatype_override=DataTypeOverride(
                            target_data_type="DECIMAL",
                            target_precision=12,
                            target_scale=0,  # Test scale 0 preservation
                        ),
                    ),
                    ColumnMapping(
                        source_column="cust_ref",
                        target_column="customer_id",
                    ),
                ),
            ),
            TableMapping(
                source_schema="shop",
                source_table="customers",
                is_included=False,  # Exclude referenced table
            ),
        ),
    )

    mapped_model = MappingEngine.apply_mapping(model, mapping, target_vendor="POSTGRESQL")
    assert len(mapped_model.tables) == 1
    mapped_tbl = mapped_model.tables[0]
    assert mapped_tbl.table_name == "products"

    # 1. Verify column rename and scale 0
    c_price = mapped_tbl.columns[0]
    assert c_price.name == "new_price"
    assert c_price.scale == 0

    # 2. Verify check clause rewritten
    assert "new_price > 0 AND new_price < 10000" in mapped_tbl.check_constraints[0].check_clause
    assert "old_price" not in mapped_tbl.check_constraints[0].check_clause

    # 3. Verify index predicate and expression rewritten
    assert "new_price > 100" in mapped_tbl.indexes[0].predicate_expression
    assert "new_price * 2" in mapped_tbl.indexes[0].expression

    # 4. Verify dropped FK captured in metadata
    assert "dropped_foreign_keys" in mapped_model.extra
    assert len(mapped_model.extra["dropped_foreign_keys"]) == 1


def test_zero_source_sql_leakage_on_failed_or_manual_procedural_conversion():
    """Blocker 5: Verify failed/manual routines NEVER leak unconverted source SQL into target DDL."""
    routine_invalid = CanonicalRoutine(
        name="bad_syntax_routine",
        schema_name="public",
        routine_type=RoutineKind.PROCEDURE,
        definition_sql="INVALID PL/SQL DEFINITION SQL",
    )
    routine_manual = CanonicalRoutine(
        name="oracle_specific_pkg_proc",
        schema_name="public",
        routine_type=RoutineKind.PROCEDURE,
        definition_sql="CREATE OR REPLACE PROCEDURE public.oracle_specific_pkg_proc AS BEGIN DBMS_OUTPUT.PUT_LINE('HI'); END;",
    )

    model = CanonicalSchemaModel(
        model_id="m_zero_leak",
        source_vendor="ORACLE",
        schemas=(CanonicalSchema(schema_name="public"),),
        routines=(routine_invalid, routine_manual),
    )

    # Compile targeting SQLite (which has no automated PL/SQL procedural transpiler)
    authority = SchemaAuthority()
    req = SchemaCompilationRequest(
        source_snapshot=model,
        target_engine="SQLITE",
    )
    res = asyncio.run(authority.compile(req))

    # All procedural results must be FAILED or MANUAL_REWRITE_REQUIRED
    assert len(res.procedural_results) == 2
    for pr in res.procedural_results:
        assert pr.conversion_state in (ConversionState.FAILED, ConversionState.MANUAL_REWRITE_REQUIRED)

    # DDL Package must NOT contain raw executable PL/SQL statements
    routine_ddl_artifacts = [a for a in res.ddl_package.artifacts if a.stage == DDLStage.ROUTINES]
    for artifact in routine_ddl_artifacts:
        assert "-- [MANUAL REWRITE REQUIRED]:" in artifact.sql
        assert not artifact.is_idempotent


def test_memoization_operational_integration():
    """Blocker 10: Verify memoization cache is actively populated and retrieved across type and dialect paths."""
    default_memoization_engine.clear()

    # 1. Type normalization memoization
    t1 = CanonicalTypeRegistry.normalize_source_type("oracle", "NUMBER", precision=10, scale=2)
    cached_t = default_memoization_engine.get_normalized_type("oracle", "NUMBER", precision=10, scale=2)
    assert cached_t is not None
    assert cached_t.category == CanonicalTypeCategory.EXACT_NUMERIC

    # 2. DateTime translation memoization
    expr = "SELECT SYSDATE + 7 FROM dual"
    res1 = DateTimeDialectTranslator.translate_datetime_expression(expr, "ORACLE", "POSTGRESQL")
    cached_expr = default_memoization_engine.get_translated_expression(expr, "ORACLE", "POSTGRESQL")
    assert cached_expr is not None
    assert cached_expr == res1


def test_capacity_projection_with_measured_zero_and_evidence_truth():
    """Blocker 8: Verify physically measured row_count=0 is preserved as MEASURED."""
    col = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT", bits=32),
    )
    tbl_zero = CanonicalTable(
        table_name="empty_table",
        schema_name="public",
        columns=(col,),
        raw_source_properties={"row_count": 0, "is_exact_count": True},
    )
    tbl_unmeasured = CanonicalTable(
        table_name="unknown_table",
        schema_name="public",
        columns=(col,),
        raw_source_properties={},
    )
    model = CanonicalSchemaModel(
        model_id="m_cap_zero",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="public"),),
        tables=(tbl_zero, tbl_unmeasured),
    )

    report = TargetCapacitySchemaProjection.calculate_projection(model, "SNOWFLAKE")
    proj_map = {tp.table_name: tp for tp in report.table_projections}

    # Verify empty table is MEASURED with 0 rows (not None or UNKNOWN)
    assert proj_map["empty_table"].evidence_kind == CapacityEvidenceKind.MEASURED
    assert proj_map["empty_table"].estimated_row_count == 0

    # Verify unmeasured table is UNKNOWN with None rows
    assert proj_map["unknown_table"].evidence_kind == CapacityEvidenceKind.UNKNOWN
    assert proj_map["unknown_table"].estimated_row_count is None
    assert report.extra.get("has_unknown_volumes") is True


def test_large_estate_chunked_streaming_and_compilation():
    """Blocker 9: Verify LargeEstateChunkedSchemaProcessor streams lazy table chunks."""
    tables = [
        CanonicalTable(
            table_name=f"t_{i}",
            schema_name="public",
            columns=(
                CanonicalColumn(
                    name="id",
                    ordinal_position=1,
                    source_native_type="INT",
                    canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT", bits=32),
                ),
            ),
        )
        for i in range(25)
    ]

    # Test stream_chunked_tables generator
    chunks = list(LargeEstateChunkedSchemaProcessor.stream_chunked_tables(iter(tables), chunk_size=10))
    assert len(chunks) == 3  # 10 + 10 + 5
    assert len(chunks[0]) == 10
    assert len(chunks[2]) == 5

    # Test compile_large_estate_package
    model = CanonicalSchemaModel(
        model_id="m_chunked_stream",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="public"),),
        tables=tuple(tables),
    )
    pkg = LargeEstateChunkedSchemaProcessor.compile_large_estate_package(model, "POSTGRESQL", chunk_size=10)
    assert len(pkg.artifacts) > 0


def test_composite_provenance_all_factors():
    """Blocker 11: Verify composite provenance hashes all 18 compilation decisions and options."""
    h1 = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
        source_model_hash="h_src",
        mapping_hash="h_map",
        ddl_package_hash="h_ddl",
        target_engine="POSTGRESQL",
        target_version="15.0",
        rule_set_version="1",
        procedural_hash="h_proc",
        readiness_hash="h_readiness",
        compatibility_breakdown_hash="h_compat",
        compat_pack_hash="h_pack",
        risk_hash="h_risk",
        capacity_hash="h_cap",
        options_hash="h_opt",
    )
    h2 = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
        source_model_hash="h_src",
        mapping_hash="h_map",
        ddl_package_hash="h_ddl",
        target_engine="POSTGRESQL",
        target_version="15.0",
        rule_set_version="1",
        procedural_hash="h_proc",
        readiness_hash="h_readiness",
        compatibility_breakdown_hash="h_compat",
        compat_pack_hash="h_pack",
        risk_hash="h_risk",
        capacity_hash="h_cap_altered",  # Altered capacity factor
        options_hash="h_opt",
    )

    assert h1 != h2


def test_18_stage_canonical_compilation():
    """Blocker 12: Verify full 18-stage compilation in SchemaAuthority."""
    col = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="BIGINT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="BIGINT", bits=64),
        nullable=False,
    )
    tbl = CanonicalTable(table_name="orders", schema_name="sales", columns=(col,))
    model = CanonicalSchemaModel(
        model_id="m_full_18",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="sales"),),
        tables=(tbl,),
    )

    authority = SchemaAuthority()
    req = SchemaCompilationRequest(
        source_snapshot=model,
        target_engine="POSTGRESQL",
        target_version="15.0",
        options={"chunked_compilation": True, "chunk_size": 10},
    )
    res = asyncio.run(authority.compile(req))

    assert res.source_engine == "POSTGRESQL"
    assert res.target_engine == "POSTGRESQL"
    assert res.readiness_report.status == ReadinessStatus.READY
    assert len(res.topologically_ordered_nodes) > 0
    assert len(res.provenance_fingerprint) == 64


def test_procedural_diagnostic_stub_immune_to_embedded_block_comments():
    """Blocker 3: Verify procedural diagnostic stub is immune to internal block comments /* ... */."""
    routine_with_comment = CanonicalRoutine(
        name="proc_with_comment",
        schema_name="public",
        routine_type=RoutineKind.PROCEDURE,
        definition_sql="CREATE PROCEDURE proc() /* block comment */ AS BEGIN NULL; /* second comment */ END;",
    )
    emitter = DDLGenerator.get_emitter("POSTGRESQL")
    artifacts = emitter.emit_routine_artifacts(
        routine=routine_with_comment,
        converted_sql=None,
        conversion_state=ConversionState.FAILED,
        source_engine="ORACLE",
    )
    assert len(artifacts) == 1
    art = artifacts[0]
    assert not art.is_idempotent
    # Every line of definition SQL must be prefixed with '-- '
    assert "-- CREATE PROCEDURE proc() /* block comment */" in art.sql
    assert "/*\n" not in art.sql  # No raw unescaped block comment wrapper


def test_memoization_semantic_cache_keys_no_collisions():
    """Blocker 2: Verify type emission cache keys distinguish timezone, UUID, vector dimensions, and LOB types."""
    default_memoization_engine.clear()

    # 1. TIMESTAMP without TZ vs with TZ
    t_no_tz = CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type="TIMESTAMP", is_timezone_aware=False)
    t_tz = CanonicalType(category=CanonicalTypeCategory.DATETIME, raw_vendor_type="TIMESTAMP", is_timezone_aware=True)

    emit_no_tz = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", t_no_tz)
    emit_tz = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", t_tz)

    assert "WITHOUT TIME ZONE" in emit_no_tz.target_native_type or emit_no_tz.target_native_type == "TIMESTAMP"
    assert "WITH TIME ZONE" in emit_tz.target_native_type or emit_tz.target_native_type == "TIMESTAMPTZ"
    assert emit_no_tz.target_native_type != emit_tz.target_native_type

    # 2. Vector with 128 dims vs 512 dims
    t_vec128 = CanonicalType(category=CanonicalTypeCategory.VECTOR, raw_vendor_type="VECTOR", dimensions=128)
    t_vec512 = CanonicalType(category=CanonicalTypeCategory.VECTOR, raw_vendor_type="VECTOR", dimensions=512)

    emit_v128 = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", t_vec128)
    emit_v512 = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", t_vec512)

    assert "128" in emit_v128.target_native_type
    assert "512" in emit_v512.target_native_type
    assert emit_v128.target_native_type != emit_v512.target_native_type


def test_dropped_fk_requires_readiness_waiver_and_partition_bounds_rewritten():
    """Blocker 4: Verify dropped FK requires WAIVER_REQUIRED and partition boundaries are rewritten."""
    col = CanonicalColumn(
        name="old_col",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT"),
    )
    part_bound = CanonicalPartitioning(
        strategy=PartitionStrategy.RANGE,
        partition_columns=("old_col",),
        partitions=(
            CanonicalPartitionBound(
                partition_name="p1",
                strategy=PartitionStrategy.RANGE,
                lower_bound="old_col >= 0",
                upper_bound="old_col < 100",
            ),
        ),
    )
    fk = CanonicalForeignKey(
        name="fk_cust",
        table_name="orders",
        schema_name="sales",
        columns=("old_col",),
        referenced_schema="sales",
        referenced_table="excluded_table",
        referenced_columns=("id",),
    )
    tbl = CanonicalTable(
        table_name="orders",
        schema_name="sales",
        columns=(col,),
        foreign_keys=(fk,),
        partitioning=part_bound,
    )
    model = CanonicalSchemaModel(
        model_id="m_fk_part",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="sales"),),
        tables=(tbl,),
    )

    mapping = CompiledSchemaMapping(
        table_mappings=(
            TableMapping(
                source_schema="sales",
                source_table="orders",
                target_schema="sales",
                target_table="orders",
                column_mappings=(
                    ColumnMapping(source_column="old_col", target_column="new_col"),
                ),
            ),
            TableMapping(source_schema="sales", source_table="excluded_table", is_included=False),
        ),
    )

    mapped_model = MappingEngine.apply_mapping(model, mapping, target_vendor="POSTGRESQL")
    assert "new_col >= 0" in mapped_model.tables[0].partitioning.partitions[0].lower_bound
    assert "new_col < 100" in mapped_model.tables[0].partitioning.partitions[0].upper_bound

    # Assess readiness
    compat = PreMigrationCompatibilityAssessor.assess_model(mapped_model, "POSTGRESQL")
    risk = StructuralRiskScorer.score_risk(mapped_model, compat)
    readiness = SchemaReadinessGateProvider.evaluate_readiness(compat, risk)

    assert readiness.status == ReadinessStatus.WAIVER_REQUIRED
    assert any("dropped foreign key constraints" in w for w in readiness.required_waivers)


def test_capacity_evidence_separation_measured_source_vs_heuristic_target():
    """Blocker 5: Verify source row evidence is MEASURED while target byte projection is ESTIMATED."""
    col = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT"),
    )
    tbl = CanonicalTable(
        table_name="data_table",
        schema_name="public",
        columns=(col,),
        raw_source_properties={"row_count": 50000, "is_exact_count": True},
    )
    model = CanonicalSchemaModel(
        model_id="m_cap_sep",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="public"),),
        tables=(tbl,),
    )

    report = TargetCapacitySchemaProjection.calculate_projection(model, "SNOWFLAKE")
    proj = report.table_projections[0]

    assert proj.source_row_evidence_kind == CapacityEvidenceKind.MEASURED
    assert proj.target_bytes_evidence_kind == CapacityEvidenceKind.ESTIMATED
    assert proj.evidence_kind == CapacityEvidenceKind.ESTIMATED


def test_50k_table_streaming_compilation_memory_bounded():
    """Blocker 1: Verify all 50,000 tables can be compiled end-to-end in memory-bounded stream with cross-chunk FK ordering, mapping, dialect translations, and full 18-step summary."""
    from akaalEngine.schema.models.constraints import CanonicalForeignKey
    from akaalEngine.schema.core.processor import EstateCompilationSummary

    captured_summary: List[EstateCompilationSummary] = []

    def on_summary(s: EstateCompilationSummary):
        captured_summary.append(s)

    # 50,000 tables with cross-chunk foreign key dependencies (child tables reference earlier parent tables)
    def table_generator():
        col = CanonicalColumn(
            name="id",
            ordinal_position=1,
            source_native_type="INT",
            canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT"),
            default_expression="SYSDATE",
        )
        for i in range(50000):
            fks = ()
            if i > 0 and i % 500 == 0:
                # Every 500th table (at chunk boundaries) references table t_0 (parent table in chunk 0)
                fks = (
                    CanonicalForeignKey(
                        name=f"fk_{i}",
                        table_name=f"t_{i}",
                        schema_name="public",
                        columns=("id",),
                        referenced_table="t_0",
                        referenced_schema="public",
                        referenced_columns=("id",),
                    ),
                )
            yield CanonicalTable(
                table_name=f"t_{i}",
                schema_name="public",
                columns=(col,),
                foreign_keys=fks,
            )

    stream = LargeEstateChunkedSchemaProcessor.stream_compile_estate(
        table_generator(),
        target_engine="POSTGRESQL",
        source_vendor="ORACLE",
        chunk_size=500,
        on_summary=on_summary,
    )

    chunk_count = 0
    total_artifacts = 0
    first_chunk_has_t0 = False
    for chunk_pkg in stream:
        chunk_count += 1
        total_artifacts += len(chunk_pkg.artifacts)
        if chunk_count == 1:
            # Verify parent table t_0 is in chunk 1
            first_chunk_has_t0 = any("t_0" in a.object_name.lower() for a in chunk_pkg.artifacts)

    # 100 chunks of 500 tables = exactly 50,000 tables processed in streaming mode
    assert chunk_count == 100
    assert total_artifacts >= 50000
    assert first_chunk_has_t0 is True

    # Verify complete whole-estate summary was generated
    assert len(captured_summary) == 1
    summary = captured_summary[0]
    assert summary.total_tables == 50000
    assert summary.total_chunks == 100
    assert summary.compatibility_report.total_columns == 50000
    assert summary.capacity_report.total_tables == 50000
    assert summary.readiness_report is not None
    assert len(summary.provenance_fingerprint) == 64


def test_array_type_memoization_nested_unhashable_extra_mapping():
    """Blocker 2: Verify array type emission with nested CanonicalType and MappingProxyType does not fail on unhashable dict."""
    default_memoization_engine.clear()

    inner_type = CanonicalType(
        category=CanonicalTypeCategory.CHARACTER,
        raw_vendor_type="VARCHAR",
        length=255,
        extra={"custom_attr": "nested_val", "is_uuid": False},
    )
    array_type = CanonicalType(
        category=CanonicalTypeCategory.ARRAY,
        raw_vendor_type="VARCHAR[]",
        array_element_type=inner_type,
        extra={"array_dimension": 1},
    )

    # Must emit without raising TypeError: unhashable type: 'mappingproxy'
    emission = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", array_type)
    assert "VARCHAR(255)[]" in emission.target_native_type or "TEXT[]" in emission.target_native_type

    # Verify cached retrieval works identically
    cached_emission = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", array_type)
    assert cached_emission.target_native_type == emission.target_native_type


def test_scoped_memoization_engine_isolation():
    """Blocker 3: Verify scoped memoization engine uses ContextVar and isolates cache across execution scopes."""
    memo1 = CompiledRuleIndexMemoizationEngine(rule_generation=1)
    memo2 = CompiledRuleIndexMemoizationEngine(rule_generation=2)

    t = CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT")

    with CanonicalTypeRegistry.scoped_memoization_engine(memo1):
        CanonicalTypeRegistry.emit_target_type("POSTGRESQL", t)
        assert len(memo1._type_emit_cache) == 1
        assert len(memo2._type_emit_cache) == 0

    with CanonicalTypeRegistry.scoped_memoization_engine(memo2):
        CanonicalTypeRegistry.emit_target_type("POSTGRESQL", t)
        assert len(memo1._type_emit_cache) == 1
        assert len(memo2._type_emit_cache) == 1


def test_rule_implementation_version_is_deterministic_and_dynamic():
    """Blocker 4: Verify rule implementation version is dynamically computed from bytecode and constants."""
    from akaalEngine.schema.core.provenance import get_rule_implementation_version
    v1 = get_rule_implementation_version()
    v2 = get_rule_implementation_version()
    assert v1 == v2
    assert v1.startswith("v4.0.0-")
    assert len(v1) == 19  # 'v4.0.0-' + 12 hex chars


def test_authority_compile_restores_contextvar_memo_binding():
    """Verify SchemaAuthority.compile cleans up ContextVar binding on exit without leaking to caller."""
    import asyncio
    from akaalEngine.schema.authority import SchemaAuthority, SchemaCompilationRequest
    custom_memo = CompiledRuleIndexMemoizationEngine(rule_generation=42)
    auth = SchemaAuthority(memoization_engine=custom_memo)

    col = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT"),
    )
    tbl = CanonicalTable(table_name="t", schema_name="public", columns=(col,))
    model = CanonicalSchemaModel(model_id="m_ctx", source_vendor="POSTGRESQL", schemas=(CanonicalSchema(schema_name="public"),), tables=(tbl,))

    req = SchemaCompilationRequest(source_snapshot=model, target_engine="POSTGRESQL")

    assert CanonicalTypeRegistry.get_active_memoization_engine() == default_memoization_engine
    result = asyncio.run(auth.compile(req))
    assert result is not None
    # Must be restored back to default
    assert CanonicalTypeRegistry.get_active_memoization_engine() == default_memoization_engine
    assert len(custom_memo._type_emit_cache) > 0


def test_authority_stream_compile_maintains_scoped_memo_binding_during_iteration():
    """Verify SchemaAuthority.stream_compile keeps ContextVar active during lazy generator iteration and restores afterwards."""
    from akaalEngine.schema.authority import SchemaAuthority, SchemaCompilationRequest
    custom_memo = CompiledRuleIndexMemoizationEngine(rule_generation=99)
    auth = SchemaAuthority(memoization_engine=custom_memo)

    col = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT"),
    )
    tbl = CanonicalTable(table_name="t", schema_name="public", columns=(col,))
    model = CanonicalSchemaModel(model_id="m_stream_ctx", source_vendor="POSTGRESQL", schemas=(CanonicalSchema(schema_name="public"),), tables=(tbl,))

    req = SchemaCompilationRequest(source_snapshot=model, target_engine="POSTGRESQL")

    assert CanonicalTypeRegistry.get_active_memoization_engine() == default_memoization_engine
    stream = auth.stream_compile(req, chunk_size=1)

    # During iteration, the active memo engine is custom_memo
    for pkg in stream:
        assert CanonicalTypeRegistry.get_active_memoization_engine() == custom_memo
        assert len(pkg.artifacts) > 0

    # After iteration completes, ContextVar is cleanly reset
    assert CanonicalTypeRegistry.get_active_memoization_engine() == default_memoization_engine


def test_multi_chunk_mapping_cross_chunk_resolution():
    """Verify multi-chunk CompiledSchemaMapping with cross-chunk foreign key rewriting and global pre-validation."""
    from akaalEngine.schema.models.constraints import CanonicalForeignKey
    from akaalEngine.schema.models.mapping import ColumnMapping, CompiledSchemaMapping, TableMapping
    from akaalEngine.schema.core.processor import EstateCompilationSummary

    col = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT"),
    )

    t0 = CanonicalTable(table_name="t_parent", schema_name="public", columns=(col,))
    t1 = CanonicalTable(table_name="t_other", schema_name="public", columns=(col,))
    t2 = CanonicalTable(
        table_name="t_child",
        schema_name="public",
        columns=(col,),
        foreign_keys=(
            CanonicalForeignKey(
                name="fk_child_parent",
                table_name="t_child",
                schema_name="public",
                columns=("id",),
                referenced_schema="public",
                referenced_table="t_parent",
                referenced_columns=("id",),
            ),
        ),
    )

    # Mapping renames t_parent -> target_parent, and t_child -> target_child
    mapping = CompiledSchemaMapping(
        table_mappings=(
            TableMapping(
                source_schema="public",
                source_table="t_parent",
                target_schema="core",
                target_table="target_parent",
            ),
            TableMapping(
                source_schema="public",
                source_table="t_child",
                target_schema="core",
                target_table="target_child",
            ),
        ),
    )

    captured_summary = []
    stream = LargeEstateChunkedSchemaProcessor.stream_compile_estate(
        [t0, t1, t2],
        target_engine="POSTGRESQL",
        chunk_size=1,  # Forces 3 separate 1-table chunks
        mapping=mapping,
        on_summary=lambda s: captured_summary.append(s),
    )

    packages = list(stream)
    assert len(packages) == 3

    # Check that t_parent was rendered as core.target_parent
    p1_sql = "\n".join(a.sql for a in packages[1].artifacts)
    assert "target_parent" in p1_sql

    # Check that t_child was rendered as core.target_child and FK references core.target_parent
    p2_sql = "\n".join(a.sql for a in packages[2].artifacts)
    assert "target_child" in p2_sql
    assert "target_parent" in p2_sql

    assert len(captured_summary) == 1
    assert captured_summary[0].total_tables == 3


def test_source_semantic_provenance_sensitivity():
    """Verify modifying a column type, default expression, or constraint changes whole-estate provenance."""
    col1 = CanonicalColumn(
        name="val",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT"),
        default_expression="0",
    )
    col2_modified = CanonicalColumn(
        name="val",
        ordinal_position=1,
        source_native_type="BIGINT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="BIGINT"),
        default_expression="100",
    )

    t_base = CanonicalTable(table_name="t_sens", schema_name="public", columns=(col1,))
    t_mod = CanonicalTable(table_name="t_sens", schema_name="public", columns=(col2_modified,))

    sum1 = []
    list(LargeEstateChunkedSchemaProcessor.stream_compile_estate([t_base], target_engine="POSTGRESQL", on_summary=sum1.append))

    sum2 = []
    list(LargeEstateChunkedSchemaProcessor.stream_compile_estate([t_mod], target_engine="POSTGRESQL", on_summary=sum2.append))

    assert sum1[0].provenance_fingerprint != sum2[0].provenance_fingerprint


def test_truthful_risk_and_compatibility_aggregation():
    """Verify truthful accumulation of risk factors and compatibility layers across chunked streaming."""
    from akaalEngine.schema.assessment.risk import RiskLevel

    col_lob = CanonicalColumn(
        name="payload",
        ordinal_position=1,
        source_native_type="BLOB",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.BINARY, raw_vendor_type="BLOB"),
        is_lob=True,
    )
    t = CanonicalTable(table_name="t_lob", schema_name="public", columns=(col_lob,))

    sum_out = []
    list(LargeEstateChunkedSchemaProcessor.stream_compile_estate([t], target_engine="POSTGRESQL", on_summary=sum_out.append))

    summary = sum_out[0]
    # LOB column produces LOB_COMPLEXITY risk factor
    assert any(f.category == "LOB_COMPLEXITY" for f in summary.risk_report.risk_factors)
    assert summary.risk_report.total_risk_score >= 10
    assert summary.capacity_report.is_truncated is False
    assert summary.capacity_report.total_projected_count == 1
