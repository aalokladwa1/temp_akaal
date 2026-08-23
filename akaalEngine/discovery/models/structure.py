"""
akaalEngine.discovery.models.structure
======================================
Column, constraint, and index physical metadata models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


class ConstraintType(str, Enum):
    """Types of database constraints."""
    PRIMARY_KEY = "PRIMARY_KEY"
    FOREIGN_KEY = "FOREIGN_KEY"
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    NOT_NULL = "NOT_NULL"
    EXCLUSION = "EXCLUSION"


class IndexAccessMethod(str, Enum):
    """Physical index storage structures and access methods."""
    BTREE = "BTREE"
    HASH = "HASH"
    GIN = "GIN"
    GIST = "GIST"
    BITMAP = "BITMAP"
    BRIN = "BRIN"
    HNSW = "HNSW"
    IVFFLAT = "IVFFLAT"
    SPATIAL = "SPATIAL"
    CLUSTERED = "CLUSTERED"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class ColumnPhysicalMetadata:
    """
    Authoritative physical facts about a single column or field as stored natively in the catalog.
    Does NOT contain canonical type mappings (which belong to Schema Authority #4).
    """
    name: str
    ordinal_position: int
    native_type: str
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
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
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ordinal_position": self.ordinal_position,
            "native_type": self.native_type,
            "length": self.length,
            "precision": self.precision,
            "scale": self.scale,
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
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class PrimaryKeyFacts:
    """Discovered primary key constraint facts."""
    name: Optional[str]
    table_name: str
    columns: Tuple[str, ...]
    schema_name: str = "public"

    def __post_init__(self) -> None:
        if not isinstance(self.columns, tuple):
            object.__setattr__(self, "columns", tuple(self.columns))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": list(self.columns),
        }


@dataclass(frozen=True)
class ForeignKeyFacts:
    """Discovered foreign key constraint facts."""
    name: Optional[str]
    table_name: str
    columns: Tuple[str, ...]
    referenced_schema: str
    referenced_table: str
    referenced_columns: Tuple[str, ...]
    schema_name: str = "public"
    on_update: Optional[str] = "NO ACTION"
    on_delete: Optional[str] = "NO ACTION"
    is_deferrable: bool = False
    is_validated: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.columns, tuple):
            object.__setattr__(self, "columns", tuple(self.columns))
        if not isinstance(self.referenced_columns, tuple):
            object.__setattr__(self, "referenced_columns", tuple(self.referenced_columns))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": list(self.columns),
            "referenced_schema": self.referenced_schema,
            "referenced_table": self.referenced_table,
            "referenced_columns": list(self.referenced_columns),
            "on_update": self.on_update,
            "on_delete": self.on_delete,
            "is_deferrable": self.is_deferrable,
            "is_validated": self.is_validated,
        }


@dataclass(frozen=True)
class UniqueConstraintFacts:
    """Discovered unique constraint facts."""
    name: Optional[str]
    table_name: str
    columns: Tuple[str, ...]
    schema_name: str = "public"
    is_deferrable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.columns, tuple):
            object.__setattr__(self, "columns", tuple(self.columns))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": list(self.columns),
            "is_deferrable": self.is_deferrable,
        }


@dataclass(frozen=True)
class CheckConstraintFacts:
    """Discovered check constraint facts."""
    name: Optional[str]
    table_name: str
    check_clause: str
    schema_name: str = "public"
    is_validated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "check_clause": self.check_clause,
            "is_validated": self.is_validated,
        }


@dataclass(frozen=True)
class IndexFacts:
    """Discovered secondary or backing index facts."""
    name: str
    table_name: str
    columns: Tuple[str, ...]
    schema_name: str = "public"
    is_unique: bool = False
    is_primary: bool = False
    access_method: IndexAccessMethod = IndexAccessMethod.BTREE
    included_columns: Tuple[str, ...] = field(default_factory=tuple)
    expression: Optional[str] = None
    filter_predicate: Optional[str] = None
    is_clustered: bool = False
    vector_dimension: Optional[int] = None
    vector_metric: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.columns, tuple):
            object.__setattr__(self, "columns", tuple(self.columns))
        if not isinstance(self.included_columns, tuple):
            object.__setattr__(self, "included_columns", tuple(self.included_columns))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": list(self.columns),
            "is_unique": self.is_unique,
            "is_primary": self.is_primary,
            "access_method": self.access_method.value,
            "included_columns": list(self.included_columns),
            "expression": self.expression,
            "filter_predicate": self.filter_predicate,
            "is_clustered": self.is_clustered,
            "vector_dimension": self.vector_dimension,
            "vector_metric": self.vector_metric,
        }


@dataclass(frozen=True)
class ObjectStructureFacts:
    """Complete physical column and structural fact model for a table or collection."""
    table_name: str
    schema_name: str = "public"
    columns: Tuple[ColumnPhysicalMetadata, ...] = field(default_factory=tuple)
    primary_key: Optional[PrimaryKeyFacts] = None
    foreign_keys: Tuple[ForeignKeyFacts, ...] = field(default_factory=tuple)
    unique_constraints: Tuple[UniqueConstraintFacts, ...] = field(default_factory=tuple)
    check_constraints: Tuple[CheckConstraintFacts, ...] = field(default_factory=tuple)
    indexes: Tuple[IndexFacts, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for attr in ("columns", "foreign_keys", "unique_constraints", "check_constraints", "indexes"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": [c.to_dict() for c in self.columns],
            "primary_key": self.primary_key.to_dict() if self.primary_key else None,
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
            "unique_constraints": [uc.to_dict() for uc in self.unique_constraints],
            "check_constraints": [cc.to_dict() for cc in self.check_constraints],
            "indexes": [idx.to_dict() for idx in self.indexes],
        }
