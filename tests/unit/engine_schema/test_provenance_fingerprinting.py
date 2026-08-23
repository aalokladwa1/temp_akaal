"""
tests.unit.engine_schema.test_provenance_fingerprinting
=======================================================
Unit tests for deterministic SHA-256 schema provenance fingerprinting (SCH-071).
"""

import pytest

from akaalEngine.schema.core.provenance import DeterministicSchemaProvenanceHasher
from akaalEngine.schema.models.mapping import CompiledSchemaMapping, SchemaMappingRule
from akaalEngine.schema.models.schema import CanonicalSchema, CanonicalSchemaModel
from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory


def _create_model(model_id: str = "estate_1"):
    col = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT", bits=32),
    )
    tbl = CanonicalTable(table_name="t1", schema_name="public", columns=(col,))
    return CanonicalSchemaModel(
        model_id=model_id,
        source_vendor="POSTGRESQL",
        tables=(tbl,),
    )


def test_deterministic_provenance_stability():
    m1 = _create_model("test_1")
    m2 = _create_model("test_1")

    hash1 = DeterministicSchemaProvenanceHasher.compute_model_fingerprint(m1)
    hash2 = DeterministicSchemaProvenanceHasher.compute_model_fingerprint(m2)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex length


def test_provenance_changes_on_semantic_difference():
    m1 = _create_model("test_1")
    m2 = _create_model("test_2")

    hash1 = DeterministicSchemaProvenanceHasher.compute_model_fingerprint(m1)
    hash2 = DeterministicSchemaProvenanceHasher.compute_model_fingerprint(m2)

    assert hash1 != hash2


def test_compilation_provenance_composite():
    p1 = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
        "src_hash_1", "map_hash_1", "ddl_hash_1", "POSTGRESQL", "15.0"
    )
    p2 = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
        "src_hash_1", "map_hash_1", "ddl_hash_1", "POSTGRESQL", "15.0"
    )
    p3 = DeterministicSchemaProvenanceHasher.compute_compilation_provenance(
        "src_hash_1", "map_hash_1", "ddl_hash_1", "ORACLE", "19c"
    )

    assert p1 == p2
    assert p1 != p3
