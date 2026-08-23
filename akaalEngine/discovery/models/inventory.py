"""
akaalEngine.discovery.models.inventory
======================================
Namespace and data object inventory fact models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


class ObjectClassification(str, Enum):
    """Classification of discovered data objects."""
    USER = "USER"
    SYSTEM = "SYSTEM"
    INTERNAL = "INTERNAL"
    TEMPORARY = "TEMPORARY"
    RECYCLE_BIN = "RECYCLE_BIN"


class ObjectType(str, Enum):
    """Types of discovered physical objects."""
    TABLE = "TABLE"
    VIEW = "VIEW"
    MATERIALIZED_VIEW = "MATERIALIZED_VIEW"
    COLLECTION = "COLLECTION"
    TOPIC = "TOPIC"
    BUCKET = "BUCKET"
    KEYSPACE = "KEYSPACE"
    STREAM = "STREAM"
    FILE = "FILE"
    SEARCH_INDEX = "SEARCH_INDEX"
    GRAPH_LABEL = "GRAPH_LABEL"


@dataclass(frozen=True)
class TableFacts:
    """Basic physical facts for a discovered table or collection."""
    name: str
    schema_name: str = ""
    catalog_name: Optional[str] = None
    object_type: ObjectType = ObjectType.TABLE
    classification: ObjectClassification = ObjectClassification.USER
    is_temporary: bool = False
    is_unlogged: bool = False
    is_external: bool = False
    storage_format: Optional[str] = None
    row_count_estimate: Optional[int] = None
    size_bytes_estimate: Optional[int] = None
    comment: Optional[str] = None
    properties: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.properties, MappingProxyType):
            object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "catalog_name": self.catalog_name,
            "object_type": self.object_type.value,
            "classification": self.classification.value,
            "is_temporary": self.is_temporary,
            "is_unlogged": self.is_unlogged,
            "is_external": self.is_external,
            "storage_format": self.storage_format,
            "row_count_estimate": self.row_count_estimate,
            "size_bytes_estimate": self.size_bytes_estimate,
            "comment": self.comment,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class ViewFacts:
    """Discovered facts for views and materialized views."""
    name: str
    schema_name: str = ""
    is_materialized: bool = False
    definition_sql: Optional[str] = None
    refresh_mode: Optional[str] = None
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    comment: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.dependencies, tuple):
            object.__setattr__(self, "dependencies", tuple(self.dependencies))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "schema_name": self.schema_name,
            "is_materialized": self.is_materialized,
            "definition_sql": self.definition_sql,
            "refresh_mode": self.refresh_mode,
            "dependencies": list(self.dependencies),
            "comment": self.comment,
        }


@dataclass(frozen=True)
class NamespaceInventory:
    """Discovered catalogs, schemas, buckets, keyspaces, and topics."""
    catalogs: Tuple[str, ...] = field(default_factory=tuple)
    schemas: Tuple[str, ...] = field(default_factory=tuple)
    system_schemas: Tuple[str, ...] = field(default_factory=tuple)
    keyspaces: Tuple[str, ...] = field(default_factory=tuple)
    buckets: Tuple[str, ...] = field(default_factory=tuple)
    topics: Tuple[str, ...] = field(default_factory=tuple)
    default_schema: Optional[str] = None

    def __post_init__(self) -> None:
        for attr in ("catalogs", "schemas", "system_schemas", "keyspaces", "buckets", "topics"):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalogs": list(self.catalogs),
            "schemas": list(self.schemas),
            "system_schemas": list(self.system_schemas),
            "keyspaces": list(self.keyspaces),
            "buckets": list(self.buckets),
            "topics": list(self.topics),
            "default_schema": self.default_schema,
        }


@dataclass(frozen=True)
class ObjectInventory:
    """Complete or scoped collection of discovered data objects."""
    tables: Tuple[TableFacts, ...] = field(default_factory=tuple)
    views: Tuple[ViewFacts, ...] = field(default_factory=tuple)
    total_table_count: int = 0
    total_view_count: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.tables, tuple):
            object.__setattr__(self, "tables", tuple(self.tables))
        if not isinstance(self.views, tuple):
            object.__setattr__(self, "views", tuple(self.views))
        if not self.total_table_count:
            object.__setattr__(self, "total_table_count", len(self.tables))
        if not self.total_view_count:
            object.__setattr__(self, "total_view_count", len(self.views))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tables": [t.to_dict() for t in self.tables],
            "views": [v.to_dict() for v in self.views],
            "total_table_count": self.total_table_count,
            "total_view_count": self.total_view_count,
        }


@dataclass(frozen=True)
class ObjectInventoryPage:
    """Cursor-paginated page of object inventory items (tables and views)."""
    items: Tuple[TableFacts, ...]
    cursor: Optional[str] = None
    is_last_page: bool = True
    page_index: int = 0
    page_size: int = 500
    views: Tuple[ViewFacts, ...] = field(default_factory=tuple)
    total_items_estimate: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.items, tuple):
            object.__setattr__(self, "items", tuple(self.items))
        if not isinstance(self.views, tuple):
            object.__setattr__(self, "views", tuple(self.views))

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "views": [v.to_dict() for v in self.views],
            "cursor": self.cursor,
            "is_last_page": self.is_last_page,
            "page_index": self.page_index,
            "page_size": self.page_size,
            "total_items_estimate": self.total_items_estimate,
        }
