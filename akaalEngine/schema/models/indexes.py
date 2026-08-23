"""
akaalEngine.schema.models.indexes
=================================
Index semantic models across BTree, Hash, GIN, GiST, BRIN, Bitmap, Clustered, Partial, Functional, and Vector indexes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple


from akaalEngine.schema.models.types import freeze_deep


class IndexAccessMethod(str, Enum):
    """Index access methods and physical algorithms."""
    BTREE = "BTREE"
    HASH = "HASH"
    GIN = "GIN"
    GIST = "GIST"
    BRIN = "BRIN"
    BITMAP = "BITMAP"
    CLUSTERED = "CLUSTERED"
    SPATIAL = "SPATIAL"
    HNSW = "HNSW"
    IVFFLAT = "IVFFLAT"
    CUSTOM = "CUSTOM"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CanonicalIndex:
    """Canonical Index definition supporting relational, functional, partial, covering, and vector indexes."""
    name: str
    table_name: str
    columns: Tuple[str, ...]
    schema_name: str = "public"
    is_unique: bool = False
    is_primary: bool = False
    access_method: IndexAccessMethod = IndexAccessMethod.BTREE
    predicate_expression: Optional[str] = None  # Partial/filtered index WHERE clause
    included_columns: Tuple[str, ...] = field(default_factory=tuple)  # Covering INCLUDE columns
    expression: Optional[str] = None  # Functional/expression index definition (e.g. "LOWER(email)")
    is_clustered: bool = False
    vector_dimensions: Optional[int] = None
    distance_metric: Optional[str] = None  # "cosine", "l2", "ip" for vector indexes
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.columns, tuple):
            object.__setattr__(self, "columns", tuple(self.columns))
        if not isinstance(self.included_columns, tuple):
            object.__setattr__(self, "included_columns", tuple(self.included_columns))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": list(self.columns),
            "is_unique": self.is_unique,
            "is_primary": self.is_primary,
            "access_method": self.access_method.value,
            "predicate_expression": self.predicate_expression,
            "included_columns": list(self.included_columns),
            "expression": self.expression,
            "is_clustered": self.is_clustered,
            "vector_dimensions": self.vector_dimensions,
            "distance_metric": self.distance_metric,
            "extra": dict(self.extra),
        }
