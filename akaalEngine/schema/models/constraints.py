"""
akaalEngine.schema.models.constraints
=====================================
Relational constraints models (Primary Key, Foreign Key, Unique, Check, Exclusion).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple


@dataclass(frozen=True)
class CanonicalPrimaryKey:
    """Canonical Primary Key constraint."""
    name: Optional[str]
    table_name: str
    columns: Tuple[str, ...]
    schema_name: str = "public"
    is_enforced: bool = True
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.columns, tuple):
            object.__setattr__(self, "columns", tuple(self.columns))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": list(self.columns),
            "is_enforced": self.is_enforced,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalForeignKey:
    """Canonical Foreign Key constraint with referential actions and deferrability."""
    name: Optional[str]
    table_name: str
    columns: Tuple[str, ...]
    referenced_schema: str
    referenced_table: str
    referenced_columns: Tuple[str, ...]
    schema_name: str = "public"
    on_update: str = "NO ACTION"  # CASCADE, SET NULL, SET DEFAULT, RESTRICT, NO ACTION
    on_delete: str = "NO ACTION"
    is_deferrable: bool = False
    is_initially_deferred: bool = False
    is_validated: bool = True
    is_enforced: bool = True
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.columns, tuple):
            object.__setattr__(self, "columns", tuple(self.columns))
        if not isinstance(self.referenced_columns, tuple):
            object.__setattr__(self, "referenced_columns", tuple(self.referenced_columns))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

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
            "is_initially_deferred": self.is_initially_deferred,
            "is_validated": self.is_validated,
            "is_enforced": self.is_enforced,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalUniqueConstraint:
    """Canonical Unique constraint."""
    name: Optional[str]
    table_name: str
    columns: Tuple[str, ...]
    schema_name: str = "public"
    is_deferrable: bool = False
    nulls_not_distinct: bool = False
    is_enforced: bool = True
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.columns, tuple):
            object.__setattr__(self, "columns", tuple(self.columns))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": list(self.columns),
            "is_deferrable": self.is_deferrable,
            "nulls_not_distinct": self.nulls_not_distinct,
            "is_enforced": self.is_enforced,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalCheckConstraint:
    """Canonical Check constraint."""
    name: Optional[str]
    table_name: str
    check_clause: str
    schema_name: str = "public"
    is_enforced: bool = True
    is_not_null: bool = False
    not_null_column: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "check_clause": self.check_clause,
            "is_enforced": self.is_enforced,
            "is_not_null": self.is_not_null,
            "not_null_column": self.not_null_column,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CanonicalExclusionConstraint:
    """Canonical Exclusion constraint (e.g. PostgreSQL gist/box/daterange exclusion)."""
    name: Optional[str]
    table_name: str
    access_method: str  # e.g. "GIST", "SPGIST"
    elements: Tuple[Tuple[str, str], ...]  # Tuple of (column_or_expr, operator)
    where_clause: Optional[str] = None
    schema_name: str = "public"
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.elements, tuple):
            object.__setattr__(self, "elements", tuple(self.elements))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "access_method": self.access_method,
            "elements": [list(e) for e in self.elements],
            "where_clause": self.where_clause,
            "extra": dict(self.extra),
        }
