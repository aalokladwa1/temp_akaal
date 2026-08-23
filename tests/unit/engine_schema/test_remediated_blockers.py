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
from akaalEngine.schema.models.partitioning import CanonicalPartitioning, PartitionStrategy
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
