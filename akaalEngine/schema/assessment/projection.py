"""
akaalEngine.schema.assessment.projection
=======================================
Target capacity and structural storage projection models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple

from akaalEngine.schema.models.schema import CanonicalSchemaModel
from akaalEngine.schema.models.types import CanonicalTypeCategory, freeze_deep


class CapacityEvidenceKind(str, Enum):
    """Evidence basis for capacity projections."""
    MEASURED = "MEASURED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TableCapacityProjection:
    """Projected storage metrics for a single table."""
    table_name: str
    schema_name: str
    estimated_row_count: Optional[int]
    estimated_bytes_source: Optional[int]
    estimated_bytes_target: Optional[int]
    estimated_compression_ratio: float = 1.0
    evidence_kind: CapacityEvidenceKind = CapacityEvidenceKind.ESTIMATED
    source_row_evidence_kind: CapacityEvidenceKind = CapacityEvidenceKind.UNKNOWN
    target_bytes_evidence_kind: CapacityEvidenceKind = CapacityEvidenceKind.UNKNOWN
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", freeze_deep(self.extra))


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
        object.__setattr__(self, "extra", freeze_deep(self.extra))

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
                    "evidence_kind": tp.evidence_kind.value,
                    "source_row_evidence_kind": tp.source_row_evidence_kind.value,
                    "target_bytes_evidence_kind": tp.target_bytes_evidence_kind.value,
                    "extra": dict(tp.extra),
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

        has_unknown = False

        for tbl in model.tables:
            # Calculate estimated row width
            row_width = sum(CATEGORY_BYTE_WEIGHTS.get(c.canonical_type.category, 32) for c in tbl.columns)
            
            raw_rows = None
            for key in ("row_count", "estimated_rows", "num_rows", "approximate_row_count"):
                if key in tbl.raw_source_properties and tbl.raw_source_properties[key] is not None:
                    raw_rows = tbl.raw_source_properties[key]
                    break

            if raw_rows is not None:
                est_rows = int(raw_rows)
                is_exact = tbl.raw_source_properties.get("is_exact_count", False) or ("row_count" in tbl.raw_source_properties)
                source_row_evidence = CapacityEvidenceKind.MEASURED if is_exact else CapacityEvidenceKind.ESTIMATED
                
                # For 0 rows, 0 bytes is physically exact (MEASURED). For > 0 rows, projected width and target compression are heuristic (ESTIMATED).
                if est_rows == 0:
                    src_bytes = 0
                    tgt_bytes = 0
                    comp_ratio = 1.0
                    target_bytes_evidence = CapacityEvidenceKind.MEASURED if is_exact else CapacityEvidenceKind.ESTIMATED
                    evidence = CapacityEvidenceKind.MEASURED if is_exact else CapacityEvidenceKind.ESTIMATED
                else:
                    src_bytes = est_rows * row_width
                    comp_ratio = 1.0
                    if target_engine.upper() in ("SNOWFLAKE", "BIGQUERY", "REDSHIFT", "DATABRICKS"):
                        comp_ratio = 0.35
                    elif target_engine.upper() in ("POSTGRESQL", "ORACLE", "MYSQL", "MSSQL", "DB2"):
                        comp_ratio = 0.90
                    tgt_bytes = int(src_bytes * comp_ratio)
                    target_bytes_evidence = CapacityEvidenceKind.ESTIMATED
                    evidence = CapacityEvidenceKind.ESTIMATED

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
                        evidence_kind=evidence,
                        source_row_evidence_kind=source_row_evidence,
                        target_bytes_evidence_kind=target_bytes_evidence,
                        extra={"is_heuristic_compression": comp_ratio != 1.0},
                    )
                )
            else:
                has_unknown = True
                table_projs.append(
                    TableCapacityProjection(
                        table_name=tbl.table_name,
                        schema_name=tbl.schema_name,
                        estimated_row_count=None,
                        estimated_bytes_source=None,
                        estimated_bytes_target=None,
                        estimated_compression_ratio=1.0,
                        evidence_kind=CapacityEvidenceKind.UNKNOWN,
                        source_row_evidence_kind=CapacityEvidenceKind.UNKNOWN,
                        target_bytes_evidence_kind=CapacityEvidenceKind.UNKNOWN,
                        extra={"is_heuristic_compression": False},
                    )
                )

        return TargetCapacityReport(
            total_tables=len(model.tables),
            total_estimated_rows=total_rows,
            total_source_bytes=total_src_b,
            total_projected_target_bytes=total_tgt_b,
            table_projections=tuple(table_projs),
            extra={"has_unknown_volumes": has_unknown},
        )
