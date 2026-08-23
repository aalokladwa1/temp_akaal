"""
akaalEngine.schema.models.mapping
=================================
Structural mapping models (Schema routing, Table mapping, Column mapping, Type overrides).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


from akaalEngine.schema.models.types import freeze_deep


@dataclass(frozen=True)
class DataTypeOverride:
    """Explicit operator override for a specific column's target data type."""
    target_data_type: str
    target_precision: Optional[int] = None
    target_scale: Optional[int] = None
    target_length: Optional[int] = None
    reason: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_data_type": self.target_data_type,
            "target_precision": self.target_precision,
            "target_scale": self.target_scale,
            "target_length": self.target_length,
            "reason": self.reason,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class ColumnMapping:
    """Structural column-level mapping rule."""
    source_column: str
    target_column: str
    is_included: bool = True
    ordinal_position: Optional[int] = None
    default_expression: Optional[str] = None
    datatype_override: Optional[DataTypeOverride] = None
    is_generated: bool = False
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_column": self.source_column,
            "target_column": self.target_column,
            "is_included": self.is_included,
            "ordinal_position": self.ordinal_position,
            "default_expression": self.default_expression,
            "datatype_override": self.datatype_override.to_dict() if self.datatype_override else None,
            "is_generated": self.is_generated,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class TableMapping:
    """Structural table-level mapping rule."""
    source_schema: str
    source_table: str
    target_schema: str = ""
    target_table: str = ""
    is_included: bool = True
    column_mappings: Tuple[ColumnMapping, ...] = field(default_factory=tuple)
    custom_filter_predicate: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.column_mappings, tuple):
            object.__setattr__(self, "column_mappings", tuple(self.column_mappings))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    @property
    def source_qualified_name(self) -> str:
        return f"{self.source_schema}.{self.source_table}"

    @property
    def target_qualified_name(self) -> str:
        return f"{self.target_schema}.{self.target_table}"

    def get_column_mapping(self, src_col: str) -> Optional[ColumnMapping]:
        src_lower = src_col.lower()
        for cm in self.column_mappings:
            if cm.source_column.lower() == src_lower:
                return cm
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_schema": self.source_schema,
            "source_table": self.source_table,
            "target_schema": self.target_schema,
            "target_table": self.target_table,
            "is_included": self.is_included,
            "column_mappings": [cm.to_dict() for cm in self.column_mappings],
            "custom_filter_predicate": self.custom_filter_predicate,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class SchemaMappingRule:
    """Namespace / schema routing rule."""
    source_schema: str
    target_schema: str
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    regex_pattern: Optional[str] = None
    regex_replacement: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_schema": self.source_schema,
            "target_schema": self.target_schema,
            "prefix": self.prefix,
            "suffix": self.suffix,
            "regex_pattern": self.regex_pattern,
            "regex_replacement": self.regex_replacement,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class CompiledSchemaMapping:
    """Complete compiled schema mapping configuration."""
    schema_routes: Tuple[SchemaMappingRule, ...] = field(default_factory=tuple)
    table_mappings: Tuple[TableMapping, ...] = field(default_factory=tuple)
    global_table_prefix: Optional[str] = None
    global_table_suffix: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        for attr in ("schema_routes", "table_mappings"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def get_table_mapping(self, src_schema: str, src_table: str) -> Optional[TableMapping]:
        src_s = src_schema.lower()
        src_t = src_table.lower()
        for tm in self.table_mappings:
            if tm.source_schema.lower() == src_s and tm.source_table.lower() == src_t:
                return tm
        if "estate_mapping" in self.extra:
            estate_map = self.extra["estate_mapping"]
            if isinstance(estate_map, CompiledSchemaMapping):
                return estate_map.get_table_mapping(src_schema, src_table)
        return None

    def resolve_target_schema(self, src_schema: str) -> str:
        src_lower = src_schema.lower()
        for r in self.schema_routes:
            if r.source_schema.lower() == src_lower:
                return r.target_schema
        return src_schema

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_routes": [r.to_dict() for r in self.schema_routes],
            "table_mappings": [tm.to_dict() for tm in self.table_mappings],
            "global_table_prefix": self.global_table_prefix,
            "global_table_suffix": self.global_table_suffix,
            "extra": dict(self.extra),
        }
