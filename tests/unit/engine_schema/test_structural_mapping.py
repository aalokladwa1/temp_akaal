"""
tests.unit.engine_schema.test_structural_mapping
================================================
Unit tests for schema routing, table/column renaming, conflict validation, and serialization (SCH-035 to SCH-040).
"""

import pytest

from akaalEngine.schema.mapping.engine import MappingEngine
from akaalEngine.schema.mapping.serializer import MappingSerializer
from akaalEngine.schema.mapping.validator import MappingValidator
from akaalEngine.schema.models.mapping import (
    ColumnMapping,
    CompiledSchemaMapping,
    SchemaMappingRule,
    TableMapping,
)
from akaalEngine.schema.models.schema import CanonicalSchema, CanonicalSchemaModel
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory


def _create_sample_model():
    col1 = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT", bits=32),
    )
    col2 = CanonicalColumn(
        name="cust_name",
        ordinal_position=2,
        source_native_type="VARCHAR(100)",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type="VARCHAR(100)", length=100),
    )
    col3 = CanonicalColumn(
        name="internal_notes",
        ordinal_position=3,
        source_native_type="TEXT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type="TEXT"),
    )

    tbl = CanonicalTable(
        table_name="customers",
        schema_name="legacy_db",
        columns=(col1, col2, col3),
    )

    return CanonicalSchemaModel(
        model_id="mapping_test_model",
        source_vendor="POSTGRESQL",
        schemas=(CanonicalSchema(schema_name="legacy_db"),),
        tables=(tbl,),
    )


def test_schema_and_table_mapping_execution():
    model = _create_sample_model()

    col_map_id = ColumnMapping(source_column="id", target_column="customer_id")
    col_map_name = ColumnMapping(source_column="cust_name", target_column="full_name")
    col_map_notes = ColumnMapping(source_column="internal_notes", target_column="notes", is_included=False)

    tbl_map = TableMapping(
        source_schema="legacy_db",
        source_table="customers",
        target_schema="sales",
        target_table="dim_customers",
        column_mappings=(col_map_id, col_map_name, col_map_notes),
    )

    mapping = CompiledSchemaMapping(
        schema_routes=(SchemaMappingRule(source_schema="legacy_db", target_schema="sales"),),
        table_mappings=(tbl_map,),
    )

    # 1. Validation
    val_res = MappingValidator.validate(model, mapping)
    assert val_res.is_valid is True

    # 2. Transformation
    mapped_model = MappingEngine.apply_mapping(model, mapping)
    assert len(mapped_model.tables) == 1

    m_tbl = mapped_model.tables[0]
    assert m_tbl.schema_name == "sales"
    assert m_tbl.table_name == "dim_customers"
    assert len(m_tbl.columns) == 2  # Excluded column filtered out

    col_names = [c.name for c in m_tbl.columns]
    assert "customer_id" in col_names
    assert "full_name" in col_names
    assert "internal_notes" not in col_names


def test_mapping_conflict_validation():
    model = _create_sample_model()

    # Mapping with duplicate target table collision
    tm1 = TableMapping(source_schema="legacy_db", source_table="customers", target_schema="sales", target_table="customers")
    # Reference non-existent table
    tm2 = TableMapping(source_schema="legacy_db", source_table="non_existent", target_schema="sales", target_table="customers")

    mapping = CompiledSchemaMapping(table_mappings=(tm1, tm2))
    val_res = MappingValidator.validate(model, mapping)

    assert val_res.is_valid is False
    errors = val_res.get_errors()
    assert any(e.rule == "SOURCE_TABLE_NOT_FOUND" for e in errors)


def test_mapping_serialization_roundtrip():
    tm = TableMapping(
        source_schema="legacy_db",
        source_table="customers",
        target_schema="sales",
        target_table="dim_customers",
        column_mappings=(ColumnMapping(source_column="id", target_column="customer_id"),),
    )
    mapping = CompiledSchemaMapping(
        schema_routes=(SchemaMappingRule(source_schema="legacy_db", target_schema="sales"),),
        table_mappings=(tm,),
        global_table_prefix="tgt_",
    )

    json_str = MappingSerializer.to_json(mapping)
    reconstructed = MappingSerializer.from_json(json_str)

    assert reconstructed.global_table_prefix == "tgt_"
    assert len(reconstructed.schema_routes) == 1
    assert reconstructed.schema_routes[0].target_schema == "sales"
    assert len(reconstructed.table_mappings) == 1
    assert reconstructed.table_mappings[0].target_table == "dim_customers"
