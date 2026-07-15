"""
Akaal — Storage Layout Validator
=================================
Validates tablespace sizing, row width limits, partition constraints,
and projected quota limits against physical storage properties.
"""

from typing import List

from akaal.core.comparison.models import Schema
from akaal.core.intelligence.common.models import Diagnostic, DiagnosticCategory, Severity
from akaal.core.intelligence.storage_optimization.models import StorageConstraint
from akaal.core.intelligence.common.models import StorageReport


class StorageLayoutValidator:
    """Audits projected physical sizes against block-level and quota-level constraints."""
    def validate_storage(
        self,
        schema: Schema,
        report: StorageReport,
        constraints: StorageConstraint,
        session_id: str = "",
        correlation_id: str = "",
        trace_id: str = ""
    ) -> List[Diagnostic]:
        """Runs validation audits against estimated physical database sizes."""
        diagnostics: List[Diagnostic] = []

        total_db_size = report.projected_total_size_kb

        # 1. Database Quota Limit check
        if total_db_size > constraints.max_database_size_kb:
            diagnostics.append(Diagnostic(
                diagnostic_code="STORAGE_DB_QUOTA_EXCEEDED",
                severity=Severity.CRITICAL,
                category=DiagnosticCategory.STORAGE,
                message=f"Projected database size {total_db_size} KB exceeds quota {constraints.max_database_size_kb} KB.",
                path="schema.tables",
                explanation="Total calculated data and index sizes exceed maximum allowed database sizes.",
                root_cause="Large row allocations or extensive transaction indices.",
                suggested_fix="Enable index compression, partition tables, or request database storage expansions.",
                affected_session=session_id,
                correlation_id=correlation_id,
                trace_id=trace_id
            ))

        for table in schema.tables:
            tbl_alloc = report.allocations.get(table.name)
            if not tbl_alloc:
                continue

            tbl_size = tbl_alloc["total_size_kb"]
            avg_row_len = tbl_alloc["avg_row_len_bytes"]
            growth_1yr = tbl_alloc["projected_growth_1yr_kb"]

            # 2. Block size constraints / Raw row size limits
            # Row length must fit within target physical blocks (e.g. 8KB) minus block header overhead
            max_row_bytes = constraints.block_size_bytes - 256
            if avg_row_len > max_row_bytes:
                diagnostics.append(Diagnostic(
                    diagnostic_code="STORAGE_ROW_SIZE_EXCEEDED",
                    severity=Severity.CRITICAL,
                    category=DiagnosticCategory.STORAGE,
                    message=f"Table '{table.name}' average row width {avg_row_len} bytes exceeds block limit {max_row_bytes} bytes.",
                    path=f"tables.{table.name}",
                    explanation="A database row cannot span blocks without row chaining or migration overhead.",
                    root_cause="Extensive columns count or large VARCHAR column boundaries.",
                    suggested_fix="Move large character/binary fields to LOB segments or separate tables.",
                    affected_event=table.name,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))

            # 3. Partition Strategy / Large table check
            # Any table larger than 100MB should have a partitioning scheme
            is_large_table = tbl_size > 100 * 1024
            has_partitioning = any("PARTITION" in idx.name.upper() or "PART" in idx.name.upper() for idx in table.indexes)
            
            if is_large_table and not has_partitioning:
                diagnostics.append(Diagnostic(
                    diagnostic_code="STORAGE_PARTITION_MISSING",
                    severity=Severity.WARNING,
                    category=DiagnosticCategory.STORAGE,
                    message=f"Table '{table.name}' is large ({tbl_size} KB) but does not define a partition index.",
                    path=f"tables.{table.name}.indexes",
                    explanation="Large tables without range or hash partitions result in full-table scans and degraded IO query performances.",
                    root_cause="Omission of partition indexing during table design.",
                    suggested_fix="Define date range partition parameters or hash keys on primary search keys.",
                    affected_event=table.name,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))

            # 4. Tablespace size limits check
            if tbl_size > constraints.max_tablespace_size_kb:
                diagnostics.append(Diagnostic(
                    diagnostic_code="STORAGE_TABLESPACE_QUOTA_EXCEEDED",
                    severity=Severity.CRITICAL,
                    category=DiagnosticCategory.STORAGE,
                    message=f"Table '{table.name}' size {tbl_size} KB exceeds tablespace quota limit {constraints.max_tablespace_size_kb} KB.",
                    path=f"tables.{table.name}",
                    explanation="Individual table allocations must fit within target tablespace size limits.",
                    root_cause="Large historical data staged in medium/small data segments.",
                    suggested_fix="Separate tables across smaller custom tablespaces or archive historic data.",
                    affected_event=table.name,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))

            # 5. Growth warning check
            # Warn if projected 1-year growth exceeds 50% of the table's current size
            if growth_1yr > tbl_size * 0.5:
                diagnostics.append(Diagnostic(
                    diagnostic_code="STORAGE_GROWTH_WARNING",
                    severity=Severity.WARNING,
                    category=DiagnosticCategory.STORAGE,
                    message=f"Table '{table.name}' has high projected annual growth: {growth_1yr} KB.",
                    path=f"tables.{table.name}",
                    explanation="High annual growth projections indicate capacity limitations.",
                    root_cause="Rapid transactional table growth rate assumptions.",
                    suggested_fix="Review autoextend tablespace parameters and index structures.",
                    affected_event=table.name,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))

        return diagnostics
