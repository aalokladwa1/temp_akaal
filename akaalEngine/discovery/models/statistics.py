"""
akaalEngine.discovery.models.statistics
======================================
Cardinality, row counts, and physical table size statistics fact models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


class CountAccuracy(str, Enum):
    """Factual confidence level of row counts and data volumes."""
    EXACT_ROW_COUNT = "EXACT_ROW_COUNT"          # Proved via bounded exact query
    CATALOG_ESTIMATE = "CATALOG_ESTIMATE"        # Derived from system catalog statistics (reltuples, etc.)
    STATISTICAL_SAMPLE = "STATISTICAL_SAMPLE"    # Extrapolated from deterministic sample observations
    UNAVAILABLE = "UNAVAILABLE"                  # Catalog does not expose estimates and scan was not run


@dataclass(frozen=True)
class TableSizeFacts:
    """Discovered physical sizing and cardinality metrics for a table."""
    table_name: str
    schema_name: str = "public"
    row_count: int = 0
    count_accuracy: CountAccuracy = CountAccuracy.CATALOG_ESTIMATE
    data_bytes: int = 0
    index_bytes: int = 0
    lob_or_toast_bytes: int = 0
    total_bytes: int = 0
    block_count: Optional[int] = None
    extent_count: Optional[int] = None
    last_analyzed_epoch: Optional[float] = None
    is_stale_estimate: bool = False

    def __post_init__(self) -> None:
        if not self.total_bytes:
            tot = self.data_bytes + self.index_bytes + self.lob_or_toast_bytes
            object.__setattr__(self, "total_bytes", tot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "row_count": self.row_count,
            "count_accuracy": self.count_accuracy.value,
            "data_bytes": self.data_bytes,
            "index_bytes": self.index_bytes,
            "lob_or_toast_bytes": self.lob_or_toast_bytes,
            "total_bytes": self.total_bytes,
            "block_count": self.block_count,
            "extent_count": self.extent_count,
            "last_analyzed_epoch": self.last_analyzed_epoch,
            "is_stale_estimate": self.is_stale_estimate,
        }


@dataclass(frozen=True)
class ColumnCardinalityFacts:
    """Discovered statistical properties for a specific column."""
    column_name: str
    distinct_values_estimate: Optional[int] = None
    null_fraction: Optional[float] = None
    average_width_bytes: Optional[int] = None
    min_value_repr: Optional[str] = None
    max_value_repr: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "column_name": self.column_name,
            "distinct_values_estimate": self.distinct_values_estimate,
            "null_fraction": self.null_fraction,
            "average_width_bytes": self.average_width_bytes,
            "min_value_repr": self.min_value_repr,
            "max_value_repr": self.max_value_repr,
        }


@dataclass(frozen=True)
class StatisticsSnapshot:
    """Aggregated statistics snapshot across all discovered tables in scope."""
    table_sizes: Tuple[TableSizeFacts, ...] = field(default_factory=tuple)
    total_estimated_rows: int = 0
    total_estimated_bytes: int = 0
    has_stale_statistics: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.table_sizes, tuple):
            object.__setattr__(self, "table_sizes", tuple(self.table_sizes))
        if not self.total_estimated_rows and self.table_sizes:
            tot_r = sum(t.row_count for t in self.table_sizes)
            tot_b = sum(t.total_bytes for t in self.table_sizes)
            stale = any(t.is_stale_estimate for t in self.table_sizes)
            object.__setattr__(self, "total_estimated_rows", tot_r)
            object.__setattr__(self, "total_estimated_bytes", tot_b)
            object.__setattr__(self, "has_stale_statistics", stale)

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_sizes": [t.to_dict() for t in self.table_sizes],
            "total_estimated_rows": self.total_estimated_rows,
            "total_estimated_bytes": self.total_estimated_bytes,
            "has_stale_statistics": self.has_stale_statistics,
        }
