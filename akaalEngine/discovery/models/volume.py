"""
akaalEngine.discovery.models.volume
==================================
Data volume, largest objects ranking, LOB sizing, and migration capacity fact models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class LargestObjectItem:
    """Discovered heavy object ranking item for bottleneck mitigation."""
    object_name: str
    schema_name: str
    size_bytes: int
    row_count: int
    percentage_of_total: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_name": self.object_name,
            "schema_name": self.schema_name,
            "size_bytes": self.size_bytes,
            "row_count": self.row_count,
            "percentage_of_total": self.percentage_of_total,
        }


@dataclass(frozen=True)
class LOBVolumeFacts:
    """Discovered out-of-line Large Object sizing metrics."""
    table_name: str
    column_name: str
    schema_name: str = "public"
    total_lob_bytes: int = 0
    avg_lob_size_bytes: Optional[int] = None
    max_lob_size_bytes: Optional[int] = None
    is_inline: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "column_name": self.column_name,
            "schema_name": self.schema_name,
            "total_lob_bytes": self.total_lob_bytes,
            "avg_lob_size_bytes": self.avg_lob_size_bytes,
            "max_lob_size_bytes": self.max_lob_size_bytes,
            "is_inline": self.is_inline,
        }


@dataclass(frozen=True)
class VolumeSnapshot:
    """Complete volume analysis for selected migration scope."""
    total_selected_rows: int = 0
    total_selected_bytes: int = 0
    top_largest_objects: Tuple[LargestObjectItem, ...] = field(default_factory=tuple)
    lob_breakdown: Tuple[LOBVolumeFacts, ...] = field(default_factory=tuple)
    estimated_cdc_change_rate_bytes_per_sec: Optional[float] = None
    target_capacity_headroom_bytes: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.top_largest_objects, tuple):
            object.__setattr__(self, "top_largest_objects", tuple(self.top_largest_objects))
        if not isinstance(self.lob_breakdown, tuple):
            object.__setattr__(self, "lob_breakdown", tuple(self.lob_breakdown))

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_selected_rows": self.total_selected_rows,
            "total_selected_bytes": self.total_selected_bytes,
            "top_largest_objects": [item.to_dict() for item in self.top_largest_objects],
            "lob_breakdown": [lob.to_dict() for lob in self.lob_breakdown],
            "estimated_cdc_change_rate_bytes_per_sec": self.estimated_cdc_change_rate_bytes_per_sec,
            "target_capacity_headroom_bytes": self.target_capacity_headroom_bytes,
        }
