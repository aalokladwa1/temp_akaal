"""
Akaal — Storage Layout Analyzer
===============================
Estimates tablespace physical allocations, calculates index footprints,
and projects annual data growth curves from schema column definitions.
"""

from typing import Any, Dict, List, Tuple
import uuid
from datetime import datetime, timezone

from akaal.core.comparison.models import Schema, ColumnSchema, TableSchema
from akaal.core.models.enums import SystemType
from akaal.core.intelligence.storage_optimization.models import (
    TablespaceAllocation,
    PartitionStrategy,
    StorageProjection,
)
from akaal.core.intelligence.common.models import StorageReport, ReportMetadata
from akaal.core.intelligence.storage_optimization import IStorageAnalyzer


class StorageLayoutAnalyzer(IStorageAnalyzer):
    """Orchestrates sizing calculations, tablespace planning, and capacity projections."""
    def __init__(self, default_row_count: int = 10000) -> None:
        self.default_row_count = default_row_count

    def analyze_storage_layout(self, schema: Schema, target_dialect: SystemType) -> StorageReport:
        """Evaluates tables physical dimensions, calculates data growth, and returns a StorageReport."""
        allocations: Dict[str, Any] = {}
        total_size_kb = 0

        projections: List[StorageProjection] = []

        for table in schema.tables:
            # 1. Estimate average row length from columns
            row_header_overhead = 32  # standard database block row header bytes
            avg_row_len = row_header_overhead + sum(self._estimate_column_size_bytes(c) for c in table.columns)

            # Determine row count: look for metadata or default
            row_count = self.default_row_count

            # 2. Data Size Calculation
            data_size_kb = (row_count * avg_row_len) // 1024

            # 3. Index Size Sizing
            index_size_kb = 0
            for idx in table.indexes:
                # Sum indexed column sizes
                idx_col_bytes = sum(self._estimate_column_size_bytes(c) for c in table.columns if c.name in idx.columns)
                index_size_kb += (row_count * (idx_col_bytes + 16)) // 1024  # 16 bytes index page overhead

            tbl_total_kb = data_size_kb + index_size_kb
            growth_kb = int(tbl_total_kb * 0.2)  # default 20% annual growth expectation

            proj = StorageProjection(
                table_name=table.name,
                row_count=row_count,
                avg_row_length_bytes=avg_row_len,
                data_size_kb=data_size_kb,
                index_size_kb=index_size_kb,
                total_size_kb=tbl_total_kb,
                projected_growth_1yr_kb=growth_kb
            )
            projections.append(proj)
            total_size_kb += tbl_total_kb

            # Track allocations dictionary
            allocations[table.name] = {
                "tablespace": self._determine_tablespace(table, tbl_total_kb),
                "data_size_kb": data_size_kb,
                "index_size_kb": index_size_kb,
                "total_size_kb": tbl_total_kb,
                "avg_row_len_bytes": avg_row_len,
                "projected_growth_1yr_kb": growth_kb
            }

        # Build metadata block
        metadata = ReportMetadata(
            report_id=f"rep:storage:{uuid.uuid4().hex[:12]}",
            correlation_id="",
            trace_id="",
            request_id="",
            migration_id="",
            replay_id=None,
            generated_timestamp=datetime.now(timezone.utc),
            execution_duration_ms=0.0,
            subsystem_version="1.0.0",
            diagnostics_summary={"warnings": 0, "errors": 0},
            warning_count=0,
            error_count=0,
            recommendation_count=0,
            confidence_summary={}
        )

        return StorageReport(
            metadata=metadata,
            total_tables=len(schema.tables),
            projected_total_size_kb=total_size_kb,
            allocations=allocations,
            warnings=()
        )

    def _estimate_column_size_bytes(self, col: ColumnSchema) -> int:
        """Maps SQL data types to physical storage byte sizes."""
        dt = col.data_type.upper()
        
        # Numeric allocations
        if "BIGINT" in dt or "INT8" in dt:
            return 8
        elif "SMALLINT" in dt:
            return 2
        elif "TINYINT" in dt:
            return 1
        elif "INT" in dt or "INTEGER" in dt:
            return 4
        elif "FLOAT" in dt:
            return 4
        elif "DOUBLE" in dt or "REAL" in dt:
            return 8
        
        # Character string allocations
        elif "VARCHAR" in dt or "NVARCHAR" in dt or "VARCHAR2" in dt:
            # Parse VARCHAR(N) length if present, e.g. VARCHAR(255)
            # Default to average of 32 bytes if not extractable
            try:
                import re
                match = re.search(r'\d+', col.raw_type)
                if match:
                    # Estimate N / 2 bytes for variable characters
                    return max(1, int(match.group()) // 2)
            except Exception:
                pass
            return 32
        elif "CHAR" in dt:
            try:
                import re
                match = re.search(r'\d+', col.raw_type)
                if match:
                    return int(match.group())
            except Exception:
                pass
            return 1
            
        # Large Objects
        elif "TEXT" in dt or "CLOB" in dt or "BLOB" in dt or "JSON" in dt:
            return 1024  # default allocation estimate for large strings/objects
            
        # Temporal allocations
        elif "DATE" in dt or "TIMESTAMP" in dt or "TIME" in dt:
            return 8
            
        return 8  # fallback baseline

    def _determine_tablespace(self, table: TableSchema, total_kb: int) -> str:
        """Assigns tables to storage categories based on projected physical size."""
        if total_kb > 1024 * 1024:  # Large Tables > 1GB
            return "TS_LARGE_DATA"
        elif total_kb > 10 * 1024:  # Medium Tables > 10MB
            return "TS_MEDIUM_DATA"
        return "TS_SMALL_DATA"
