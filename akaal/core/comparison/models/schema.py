"""
Akaal — Immutable Schema Models
===============================
Frozen, immutable dataclass representations of database schemas.
Encapsulates structural state of tables, columns, indexes, and constraints.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from akaal.core.models.enums import SystemType
from akaal.core.comparison.models.context import ComparisonContext


from enum import Enum

class IdentityMode(str, Enum):
    GENERATED_ALWAYS = "GENERATED_ALWAYS"
    GENERATED_BY_DEFAULT = "GENERATED_BY_DEFAULT"
    SERIAL_FALLBACK = "SERIAL_FALLBACK"
    EMULATED_TRIGGER = "EMULATED_TRIGGER"


@dataclass(frozen=True)
class IdentityDefinition:
    """
    Immutable representation of an identity column specification.
    """
    mode: IdentityMode
    start: int = 1
    increment: int = 1
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    cycle: bool = False
    cache: Optional[int] = None
    order: bool = False
    explicit_insert_policy: str = "BLOCKED"
    source_engine: Optional[str] = None
    source_version: Optional[str] = None

    def __post_init__(self) -> None:
        if self.increment == 0:
            raise ValueError("Identity increment cannot be zero.")


@dataclass(frozen=True)
class ColumnSchema:
    """
    Immutable representation of a database column.
    """
    name: str
    data_type: str
    raw_type: str
    nullable: bool
    default_value: Optional[str] = None
    raw_default: Optional[str] = None
    identity: Optional[IdentityDefinition] = None

    def is_equivalent(self, other: "ColumnSchema", context: ComparisonContext, is_pk: bool = False) -> bool:
        """
        Evaluate if this column is equivalent to another column,
        taking ComparisonContext options into account.
        """
        from akaal.core.comparison.support.identifier_resolver import resolve_identifier
        from akaal.core.comparison.support.equivalence_rules import are_types_equivalent, are_defaults_equivalent

        name_self = resolve_identifier(self.name, context)
        name_other = resolve_identifier(other.name, context)
        if name_self != name_other:
            return False

        # Data type check
        if not are_types_equivalent(
            self.data_type, other.data_type, self.raw_type, other.raw_type, context
        ):
            return False
        
        # Nullability check
        if self.nullable != other.nullable:
            return False

        # Defaults evaluation
        if not are_defaults_equivalent(
            self.default_value or "NULL",
            other.default_value or "NULL",
            self.data_type,
            other.data_type,
            is_pk,
        ):
            return False

        # Identity evaluation
        if self.identity != other.identity:
            return False

        return True


@dataclass(frozen=True)
class PrimaryKeySchema:
    """
    Immutable representation of a primary key constraint.
    """
    name: Optional[str]
    columns: Tuple[str, ...]  # Ordered column names for composite PKs


@dataclass(frozen=True)
class ForeignKeySchema:
    """
    Immutable representation of a foreign key constraint.
    """
    name: str
    from_columns: Tuple[str, ...]
    to_table: str
    to_columns: Tuple[str, ...]
    on_delete: Optional[str] = None
    on_update: Optional[str] = None


@dataclass(frozen=True)
class IndexSchema:
    """
    Immutable representation of a database index.
    """
    name: str
    columns: Tuple[str, ...]  # Ordered column names for composite indexes
    unique: bool


@dataclass(frozen=True)
class ConstraintSchema:
    """
    Immutable representation of a unique or check constraint.
    """
    name: str
    type: str  # e.g., "UNIQUE", "CHECK"
    columns: Tuple[str, ...] = ()  # For unique constraints
    definition: Optional[str] = None  # For check constraints


@dataclass(frozen=True)
class TableSchema:
    """
    Immutable representation of a database table schema.
    """
    name: str
    columns: Tuple[ColumnSchema, ...]
    primary_key: Optional[PrimaryKeySchema] = None
    foreign_keys: Tuple[ForeignKeySchema, ...] = ()
    indexes: Tuple[IndexSchema, ...] = ()
    constraints: Tuple[ConstraintSchema, ...] = ()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TableSchema):
            return False
        return (
            self.name == other.name
            and self.columns == other.columns
            and self.primary_key == other.primary_key
            and set(self.foreign_keys) == set(other.foreign_keys)
            and set(self.indexes) == set(other.indexes)
            and set(self.constraints) == set(other.constraints)
        )

    def __hash__(self) -> int:
        return hash((
            self.name,
            self.columns,
            self.primary_key,
            frozenset(self.foreign_keys),
            frozenset(self.indexes),
            frozenset(self.constraints),
        ))


@dataclass(frozen=True)
class Schema:
    """
    Immutable top-level representation of a database schema.
    """
    tables: Tuple[TableSchema, ...]
    
    # Optional Extensible Metadata
    schema_name: Optional[str] = None
    schema_version: Optional[str] = None
    vendor: Optional[SystemType] = None
    encoding: Optional[str] = None
    collation: Optional[str] = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Schema):
            return False
        return (
            set(self.tables) == set(other.tables)
            and self.schema_name == other.schema_name
            and self.schema_version == other.schema_version
            and self.vendor == other.vendor
            and self.encoding == other.encoding
            and self.collation == other.collation
        )

    def __hash__(self) -> int:
        return hash((
            frozenset(self.tables),
            self.schema_name,
            self.schema_version,
            self.vendor,
            self.encoding,
            self.collation,
        ))
