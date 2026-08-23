"""
akaalEngine.schema.assessment.projection
=======================================
Target capacity and structural storage projection models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple

from akaalEngine.schema.models.schema import CanonicalSchemaModel
from akaalEngine.schema.models.types import CanonicalTypeCategory


@dataclass(frozen=True)
class TableCapacityProjection:
    """Projected storage metrics for a single table."""
    table_name: str
    schema_name: str
    estimated_row_count: int
    estimated_bytes_source: int
    estimated_bytes_target: int
    estimated_compression_ratio: float = 1.0


@dataclass(frozen=True)
class TargetCapacityReport:
    """Consolidated schema storage capacity projection report."""
    total_tables: int
    total_estimated_rows: int
    total_source_bytes: int
    total_projected_target_bytes: int
    table_projections: Tuple[TableCapacityProjection, ...] = field(default_factory=tuple)
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.table_projections, tuple):
            object.__setattr__(self, "table_projections", tuple(self.table_projections))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tables": self.total_tables,
            "total_estimated_rows": self.total_estimated_rows,
            "total_source_bytes": self.total_source_bytes,
            "total_projected_target_bytes": self.total_projected_target_bytes,
            "table_projections": [
                {
                    "table_name": tp.table_name,
                    "schema_name": tp.schema_name,
                    "estimated_row_count": tp.estimated_row_count,
                    "estimated_bytes_source": tp.estimated_bytes_source,
                    "estimated_bytes_target": tp.estimated_bytes_target,
                    "estimated_compression_ratio": tp.estimated_compression_ratio,
                }
                for tp in self.table_projections
            ],
            "extra": dict(self.extra),
        }


class TargetCapacitySchemaProjection:
    """Calculates deterministic structural storage projections based on column datatypes and discovered volume facts."""

    @classmethod
    def calculate_projection(cls, model: CanonicalSchemaModel, target_engine: str) -> TargetCapacityReport:
        table_projs: List[TableCapacityProjection] = []
        total_rows = 0
        total_src_b = 0
        total_tgt_b = 0

        # Estimated average byte sizes per canonical type category
        CATEGORY_BYTE_WEIGHTS = {
            CanonicalTypeCategory.EXACT_NUMERIC: 8,
            CanonicalTypeCategory.APPROX_NUMERIC: 8,
            CanonicalTypeCategory.CHARACTER: 64,
            CanonicalTypeCategory.BINARY: 128,
            CanonicalTypeCategory.DATETIME: 8,
            CanonicalTypeCategory.INTERVAL: 8,
            CanonicalTypeCategory.BOOLEAN: 1,
            CanonicalTypeCategory.JSON: 256,
            CanonicalTypeCategory.XML: 256,
            CanonicalTypeCategory.SPATIAL: 32,
            CanonicalTypeCategory.VECTOR: 512,
            CanonicalTypeCategory.UDT: 64,
            CanonicalTypeCategory.LOB: 4096,
            CanonicalTypeCategory.ARRAY: 128,
            CanonicalTypeCategory.UNKNOWN: 32,
        }

        for tbl in model.tables:
            # Calculate estimated row width
            row_width = sum(CATEGORY_BYTE_WEIGHTS.get(c.canonical_type.category, 32) for c in tbl.columns)
            est_rows = tbl.raw_source_properties.get("estimated_rows", 1000)
            src_bytes = est_rows * row_width

            # Columnar warehouses (Snowflake, BigQuery, Redshift) achieve ~3x compression
            comp_ratio = 0.35 if target_engine.upper() in ("SNOWFLAKE", "BIGQUERY", "REDSHIFT") else 1.0
            tgt_bytes = int(src_bytes * comp_ratio)

            total_rows += est_rows
            total_src_b += src_bytes
            total_tgt_b += tgt_bytes

            table_projs.append(
                TableCapacityProjection(
                    table_name=tbl.table_name,
                    schema_name=tbl.schema_name,
                    estimated_row_count=est_rows,
                    estimated_bytes_source=src_bytes,
                    estimated_bytes_target=tgt_bytes,
                    estimated_compression_ratio=comp_ratio,
                )
            )

        return TargetCapacityReport(
            total_tables=len(model.tables),
            total_estimated_rows=total_rows,
            total_source_bytes=total_src_b,
            total_projected_target_bytes=total_tgt_b,
            table_projections=tuple(table_projs),
        )
