"""
AKAAL Schema Engine — Canonical Schema Domain Model
===================================================
Defines database-agnostic, strongly typed canonical domain models for database
objects (tables, columns, PKs, FKs, constraints, indexes, sequences, identities,
partitions, views, procedures, functions, triggers).
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class CanonicalObjectIdentity:
    """Unique identity representation of a database object preserving original and normalized names."""
    schema_name: str
    object_name: str
    object_type: str = "TABLE"  # TABLE, VIEW, INDEX, SEQUENCE, PROCEDURE, FUNCTION, TRIGGER
    catalog: Optional[str] = None
    parent_object: Optional[str] = None
    quoted_identifier: str = ""
    normalized_identifier: str = ""

    def __post_init__(self):
        if not self.normalized_identifier:
            self.normalized_identifier = f"{self.schema_name.lower()}.{self.object_name.lower()}"
        if not self.quoted_identifier:
            self.quoted_identifier = f'"{self.schema_name}"."{self.object_name}"'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "catalog": self.catalog,
            "schema_name": self.schema_name,
            "object_name": self.object_name,
            "object_type": self.object_type,
            "parent_object": self.parent_object,
            "quoted_identifier": self.quoted_identifier,
            "normalized_identifier": self.normalized_identifier,
        }


@dataclass
class CanonicalColumn:
    """Canonical representation of a database table column."""
    name: str
    ordinal_position: int
    source_native_type: str
    canonical_type: str = "TEXT"
    canonical_type_model: Optional[Any] = None  # Holds CanonicalType instance
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    nullable: bool = True
    default_expression: Optional[str] = None
    is_identity: bool = False
    is_primary_key: bool = False
    is_lob: bool = False
    is_binary: bool = False
    timezone_aware: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ordinal_position": self.ordinal_position,
            "source_native_type": self.source_native_type,
            "canonical_type": self.canonical_type,
            "canonical_type_model": self.canonical_type_model.to_dict() if hasattr(self.canonical_type_model, "to_dict") else None,
            "length": self.length,
            "precision": self.precision,
            "scale": self.scale,
            "nullable": self.nullable,
            "default_expression": self.default_expression,
            "is_identity": self.is_identity,
            "is_primary_key": self.is_primary_key,
            "is_lob": self.is_lob,
            "is_binary": self.is_binary,
            "timezone_aware": self.timezone_aware,
            "extra": self.extra,
        }


@dataclass
class CanonicalPrimaryKey:
    """Canonical representation of a primary key constraint."""
    table_name: str
    column_names: List[str]
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "column_names": sorted(self.column_names),
        }


@dataclass
class CanonicalForeignKey:
    """Canonical representation of a foreign key constraint."""
    table_name: str
    column_names: List[str]
    referenced_schema: str
    referenced_table: str
    referenced_columns: List[str]
    name: Optional[str] = None
    on_update: Optional[str] = "NO ACTION"
    on_delete: Optional[str] = "NO ACTION"
    is_deferrable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "column_names": self.column_names,
            "referenced_schema": self.referenced_schema,
            "referenced_table": self.referenced_table,
            "referenced_columns": self.referenced_columns,
            "on_update": self.on_update,
            "on_delete": self.on_delete,
            "is_deferrable": self.is_deferrable,
        }


@dataclass
class CanonicalUniqueConstraint:
    """Canonical representation of a unique constraint."""
    table_name: str
    column_names: List[str]
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "column_names": sorted(self.column_names),
        }


@dataclass
class CanonicalCheckConstraint:
    """Canonical representation of a check constraint."""
    table_name: str
    check_clause: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "check_clause": self.check_clause,
        }


@dataclass
class CanonicalDefault:
    """Canonical representation of a column default value constraint."""
    column_name: str
    default_expression: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "column_name": self.column_name,
            "default_expression": self.default_expression,
        }


@dataclass
class CanonicalIndex:
    """Canonical representation of a table index."""
    name: str
    table_name: str
    column_names: List[str]
    is_unique: bool = False
    is_primary: bool = False
    index_type: Optional[str] = None
    filter_clause: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "column_names": self.column_names,
            "is_unique": self.is_unique,
            "is_primary": self.is_primary,
            "index_type": self.index_type,
            "filter_clause": self.filter_clause,
        }


@dataclass
class CanonicalSequence:
    """Canonical representation of an independent database sequence."""
    name: str
    schema_name: str = "public"
    start_value: int = 1
    increment_by: int = 1
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    is_cycling: bool = False
    cache_size: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "start_value": self.start_value,
            "increment_by": self.increment_by,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "is_cycling": self.is_cycling,
            "cache_size": self.cache_size,
        }


@dataclass
class CanonicalIdentity:
    """Canonical representation of an auto-increment/identity column property."""
    column_name: str
    generation_type: str = "ALWAYS"  # ALWAYS or BY DEFAULT
    seed: int = 1
    increment: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "column_name": self.column_name,
            "generation_type": self.generation_type,
            "seed": self.seed,
            "increment": self.increment,
        }


@dataclass
class CanonicalPartition:
    """Canonical representation of table partitioning bounds and strategy."""
    table_name: str
    strategy: str = "SINGLE_STREAM"
    partition_key_columns: List[str] = field(default_factory=list)
    partition_name: Optional[str] = None
    lower_bound: Optional[Any] = None
    upper_bound: Optional[Any] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "strategy": self.strategy,
            "partition_key_columns": self.partition_key_columns,
            "partition_name": self.partition_name,
            "lower_bound": str(self.lower_bound) if self.lower_bound is not None else None,
            "upper_bound": str(self.upper_bound) if self.upper_bound is not None else None,
            "extra": self.extra,
        }


@dataclass
class CanonicalView:
    """Canonical metadata container for database views."""
    name: str
    schema_name: str = "public"
    source_definition: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "source_definition": self.source_definition,
            "dependencies": sorted(self.dependencies),
        }


@dataclass
class CanonicalMaterializedView:
    """Canonical metadata container for materialized views."""
    name: str
    schema_name: str = "public"
    source_definition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "source_definition": self.source_definition,
        }


@dataclass
class CanonicalProcedure:
    """Canonical metadata container for stored procedures."""
    name: str
    schema_name: str = "public"
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    source_definition: Optional[str] = None
    language: str = "PLSQL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "parameters": self.parameters,
            "source_definition": self.source_definition,
            "language": self.language,
        }


@dataclass
class CanonicalFunction:
    """Canonical metadata container for user-defined functions."""
    name: str
    schema_name: str = "public"
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: str = "VOID"
    source_definition: Optional[str] = None
    language: str = "PLSQL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "source_definition": self.source_definition,
            "language": self.language,
        }


@dataclass
class CanonicalTrigger:
    """Canonical metadata container for database triggers."""
    name: str
    schema_name: str = "public"
    table_name: str = ""
    timing: str = "BEFORE"
    events: List[str] = field(default_factory=list)
    source_definition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "table_name": self.table_name,
            "timing": self.timing,
            "events": sorted(self.events),
            "source_definition": self.source_definition,
        }


@dataclass
class CanonicalTable:
    """Canonical representation of a relational database table."""
    identity: CanonicalObjectIdentity
    columns: List[CanonicalColumn] = field(default_factory=list)
    primary_key: Optional[CanonicalPrimaryKey] = None
    foreign_keys: List[CanonicalForeignKey] = field(default_factory=list)
    unique_constraints: List[CanonicalUniqueConstraint] = field(default_factory=list)
    check_constraints: List[CanonicalCheckConstraint] = field(default_factory=list)
    indexes: List[CanonicalIndex] = field(default_factory=list)
    partitions: List[CanonicalPartition] = field(default_factory=list)
    comment: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "columns": [c.to_dict() for c in sorted(self.columns, key=lambda x: x.ordinal_position)],
            "primary_key": self.primary_key.to_dict() if self.primary_key else None,
            "foreign_keys": [fk.to_dict() for fk in sorted(self.foreign_keys, key=lambda x: x.name or "")],
            "unique_constraints": [uc.to_dict() for uc in sorted(self.unique_constraints, key=lambda x: x.name or "")],
            "check_constraints": [cc.to_dict() for cc in sorted(self.check_constraints, key=lambda x: x.name or "")],
            "indexes": [idx.to_dict() for idx in sorted(self.indexes, key=lambda x: x.name)],
            "partitions": [p.to_dict() for p in self.partitions],
            "comment": self.comment,
            "extra": self.extra,
        }


@dataclass
class CanonicalSchemaModel:
    """Top-level database-agnostic canonical schema model container."""
    schema_name: str
    engine: str
    tables: Dict[str, CanonicalTable] = field(default_factory=dict)
    views: Dict[str, CanonicalView] = field(default_factory=dict)
    sequences: Dict[str, CanonicalSequence] = field(default_factory=dict)
    procedures: Dict[str, CanonicalProcedure] = field(default_factory=dict)
    functions: Dict[str, CanonicalFunction] = field(default_factory=dict)
    triggers: Dict[str, CanonicalTrigger] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def add_table(self, table: CanonicalTable) -> None:
        key = table.identity.object_name.lower()
        self.tables[key] = table

    def get_table(self, table_name: str) -> Optional[CanonicalTable]:
        return self.tables.get(table_name.lower())

    def to_dict(self) -> Dict[str, Any]:
        """Return a deterministic, sorted dictionary representation of the schema."""
        return {
            "schema_name": self.schema_name,
            "engine": self.engine.upper(),
            "tables": {k: self.tables[k].to_dict() for k in sorted(self.tables.keys())},
            "views": {k: self.views[k].to_dict() for k in sorted(self.views.keys())},
            "sequences": {k: self.sequences[k].to_dict() for k in sorted(self.sequences.keys())},
            "procedures": {k: self.procedures[k].to_dict() for k in sorted(self.procedures.keys())},
            "functions": {k: self.functions[k].to_dict() for k in sorted(self.functions.keys())},
            "triggers": {k: self.triggers[k].to_dict() for k in sorted(self.triggers.keys())},
            "extra": self.extra,
        }

    def compute_schema_fingerprint(self) -> str:
        """Compute SHA-256 deterministic schema structural fingerprint."""
        raw_json = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
