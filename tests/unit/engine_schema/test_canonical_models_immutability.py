"""
tests.unit.engine_schema.test_canonical_models_immutability
===========================================================
Unit tests proving immutability, serialization round-trip, and semantic structure of Canonical Schema IR (SCH-001 - SCH-014).
"""

import dataclasses
import pytest
from types import MappingProxyType

from akaalEngine.schema.models.constraints import (
    CanonicalCheckConstraint,
    CanonicalExclusionConstraint,
    CanonicalForeignKey,
    CanonicalPrimaryKey,
    CanonicalUniqueConstraint,
)
from akaalEngine.schema.models.indexes import CanonicalIndex, IndexAccessMethod
from akaalEngine.schema.models.partitioning import CanonicalPartitioning, PartitionStrategy
from akaalEngine.schema.models.programmables import (
    CanonicalRoutine,
    CanonicalSequence,
    CanonicalUDT,
    ParameterMode,
    RoutineKind,
)
from akaalEngine.schema.models.schema import (
    CanonicalCatalog,
    CanonicalSchema,
    CanonicalSchemaModel,
    CanonicalSynonym,
    CanonicalView,
)
from akaalEngine.schema.models.table import (
    CanonicalColumn,
    CanonicalTable,
    StorageFormat,
    TablePhysicalType,
)
from akaalEngine.schema.models.types import (
    CanonicalType,
    CanonicalTypeCategory,
    ConversionSafety,
    TargetTypeEmission,
)


def test_canonical_type_immutability():
    ctype = CanonicalType(
        category=CanonicalTypeCategory.EXACT_NUMERIC,
        raw_vendor_type="NUMBER(10,2)",
        precision=10,
        scale=2,
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        ctype.precision = 12  # type: ignore

    d = ctype.to_dict()
    assert d["category"] == "EXACT_NUMERIC"
    assert d["precision"] == 10
    assert d["scale"] == 2

    # Roundtrip from_dict
    reconstructed = CanonicalType.from_dict(d)
    assert reconstructed.category == ctype.category
    assert reconstructed.precision == ctype.precision
    assert reconstructed.scale == ctype.scale


def test_canonical_column_and_table_immutability():
    col1 = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="BIGINT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="BIGINT", bits=64),
        nullable=False,
        is_identity=True,
    )
    col2 = CanonicalColumn(
        name="email",
        ordinal_position=2,
        source_native_type="VARCHAR(255)",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.CHARACTER, raw_vendor_type="VARCHAR(255)", length=255),
        nullable=False,
    )

    pk = CanonicalPrimaryKey(
        name="pk_users",
        table_name="users",
        columns=("id",),
        schema_name="public",
    )

    tbl = CanonicalTable(
        table_name="users",
        schema_name="public",
        columns=(col1, col2),
        primary_key=pk,
    )

    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        tbl.table_name = "customers"  # type: ignore

    assert tbl.qualified_name == "public.users"
    assert tbl.get_column("EMAIL") == col2
    assert tbl.get_column("nonexistent") is None

    tbl_dict = tbl.to_dict()
    assert tbl_dict["table_name"] == "users"
    assert len(tbl_dict["columns"]) == 2
    assert tbl_dict["primary_key"]["columns"] == ["id"]


def test_canonical_schema_model_full_hierarchy():
    col = CanonicalColumn(
        name="id",
        ordinal_position=1,
        source_native_type="INT",
        canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INT", bits=32),
    )
    tbl = CanonicalTable(table_name="orders", schema_name="sales", columns=(col,))
    view = CanonicalView(view_name="active_orders", schema_name="sales", definition_sql="SELECT * FROM orders")
    seq = CanonicalSequence(name="order_id_seq", schema_name="sales", start_value=100)
    udt = CanonicalUDT(name="order_status", schema_name="sales", enum_values=("PENDING", "SHIPPED", "DELIVERED"))

    model = CanonicalSchemaModel(
        model_id="test_estate_1",
        source_vendor="POSTGRESQL",
        source_version="15.2",
        tables=(tbl,),
        views=(view,),
        sequences=(seq,),
        udts=(udt,),
    )

    assert model.get_table("sales", "orders") == tbl
    assert model.get_view("sales", "active_orders") == view
    assert len(model.tables) == 1
    assert len(model.views) == 1
    assert len(model.sequences) == 1
    assert len(model.udts) == 1

    model_dict = model.to_dict()
    assert model_dict["model_id"] == "test_estate_1"
    assert model_dict["source_vendor"] == "POSTGRESQL"
    assert len(model_dict["tables"]) == 1
