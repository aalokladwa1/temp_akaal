"""
akaalEngine.schema.models.table
===============================
Canonical Table and Column structural models with physical semantics, precision/scale, and constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from akaalEngine.schema.models.constraints import (
    CanonicalCheckConstraint,
    CanonicalExclusionConstraint,
    CanonicalForeignKey,
    CanonicalPrimaryKey,
    CanonicalUniqueConstraint,
)
from akaalEngine.schema.models.indexes import CanonicalIndex
from akaalEngine.schema.models.partitioning import CanonicalPartitioning
from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory, freeze_deep


class TablePhysicalType(str, Enum):
    """Table physical storage types."""
    TABLE = "TABLE"
    EXTERNAL_TABLE = "EXTERNAL_TABLE"
    MATERIALIZED_VIEW = "MATERIALIZED_VIEW"
    VIEW = "VIEW"
    UNLOGGED_TABLE = "UNLOGGED_TABLE"
    TEMPORARY_TABLE = "TEMPORARY_TABLE"
    DOCUMENT_COLLECTION = "DOCUMENT_COLLECTION"
    KEYSPACE_TABLE = "KEYSPACE_TABLE"
    TIME_SERIES_TABLE = "TIME_SERIES_TABLE"


class StorageFormat(str, Enum):
    """Underlying physical storage format."""
    RELATIONAL = "RELATIONAL"
    PARQUET = "PARQUET"
    ORC = "ORC"
    AVRO = "AVRO"
    CSV = "CSV"
    JSON = "JSON"
    BSON = "BSON"
    DELTA = "DELTA"
    ICEBERG = "ICEBERG"


@dataclass(frozen=True)
class CanonicalColumn:
    """Canonical column with dual source-native and canonical datatype representation."""
    name: str
    ordinal_position: int
    source_native_type: str
    canonical_type: CanonicalType
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    byte_semantics: bool = False
    nullable: bool = True
    default_expression: Optional[str] = None
    is_identity: bool = False
    identity_generation: Optional[str] = None  # "ALWAYS" or "BY DEFAULT"
    is_computed: bool = False
    computed_expression: Optional[str] = None
    is_lob: bool = False
    is_array: bool = False
    array_element_type: Optional[str] = None
    comment: Optional[str] = None
    raw_metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_metadata", freeze_deep(self.raw_metadata))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ordinal_position": self.ordinal_position,
            "source_native_type": self.source_native_type,
            "canonical_type": self.canonical_type.to_dict(),
            "length": self.length,
            "precision": self.precision,
            "scale": self.scale,
            "byte_semantics": self.byte_semantics,
            "nullable": self.nullable,
            "default_expression": self.default_expression,
            "is_identity": self.is_identity,
            "identity_generation": self.identity_generation,
            "is_computed": self.is_computed,
            "computed_expression": self.computed_expression,
            "is_lob": self.is_lob,
            "is_array": self.is_array,
            "array_element_type": self.array_element_type,
            "comment": self.comment,
            "raw_metadata": dict(self.raw_metadata),
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalTable:
    """Canonical Table semantic representation containing columns, constraints, indexes, and partitioning."""
    table_name: str
    schema_name: str = "public"
    catalog_name: Optional[str] = None
    table_type: TablePhysicalType = TablePhysicalType.TABLE
    storage_format: StorageFormat = StorageFormat.RELATIONAL
    columns: Tuple[CanonicalColumn, ...] = field(default_factory=tuple)
    primary_key: Optional[CanonicalPrimaryKey] = None
    foreign_keys: Tuple[CanonicalForeignKey, ...] = field(default_factory=tuple)
    unique_constraints: Tuple[CanonicalUniqueConstraint, ...] = field(default_factory=tuple)
    check_constraints: Tuple[CanonicalCheckConstraint, ...] = field(default_factory=tuple)
    exclusion_constraints: Tuple[CanonicalExclusionConstraint, ...] = field(default_factory=tuple)
    indexes: Tuple[CanonicalIndex, ...] = field(default_factory=tuple)
    partitioning: CanonicalPartitioning = field(default_factory=CanonicalPartitioning)
    row_format: Optional[str] = None
    compression: Optional[str] = None
    tablespace: Optional[str] = None
    comment: Optional[str] = None
    raw_source_properties: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        for attr in ("columns", "foreign_keys", "unique_constraints", "check_constraints", "exclusion_constraints", "indexes"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))
        object.__setattr__(self, "raw_source_properties", freeze_deep(self.raw_source_properties))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def qualified_name(self) -> str:
        if self.schema_name:
            return f"{self.schema_name}.{self.table_name}"
        return self.table_name

    def get_column(self, col_name: str) -> Optional[CanonicalColumn]:
        col_lower = col_name.lower()
        for col in self.columns:
            if col.name.lower() == col_lower:
                return col
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "catalog_name": self.catalog_name,
            "table_type": self.table_type.value,
            "storage_format": self.storage_format.value,
            "columns": [c.to_dict() for c in self.columns],
            "primary_key": self.primary_key.to_dict() if self.primary_key else None,
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
            "unique_constraints": [uc.to_dict() for uc in self.unique_constraints],
            "check_constraints": [ck.to_dict() for ck in self.check_constraints],
            "exclusion_constraints": [ec.to_dict() for ec in self.exclusion_constraints],
            "indexes": [idx.to_dict() for idx in self.indexes],
            "partitioning": self.partitioning.to_dict(),
            "row_format": self.row_format,
            "compression": self.compression,
            "tablespace": self.tablespace,
            "comment": self.comment,
            "raw_source_properties": dict(self.raw_source_properties),
            "extra": dict(self.extra),
        }
