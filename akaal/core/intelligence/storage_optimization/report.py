"""
Akaal — Storage Report Builder
==============================
Assembles capacity projections, diagnostic alerts, and confidence rankings
into the unified StorageReport structure.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from akaal.core.intelligence.common.models import (
    Diagnostic,
    ReportMetadata,
    StorageReport,
    Severity,
)


class StorageReportBuilder:
    """Builder class constructing immutable StorageReports."""
    def __init__(
        self,
        correlation_id: str,
        trace_id: str,
        request_id: str,
        migration_id: str
    ) -> None:
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.request_id = request_id
        self.migration_id = migration_id

    def build_report(
        self,
        base_report: StorageReport,
        diagnostics: List[Diagnostic],
        execution_duration_ms: float
    ) -> StorageReport:
        """Enriches sizing allocations and diagnostic warnings into a final StorageReport."""
        warning_count = sum(1 for d in diagnostics if d.severity == Severity.WARNING)
        error_count = sum(1 for d in diagnostics if d.severity == Severity.CRITICAL)

        diagnostics_summary = {
            "warnings": warning_count,
            "errors": error_count,
            "infos": sum(1 for d in diagnostics if d.severity == Severity.INFO)
        }

        # Calculate confidence metric: starts at 1.0, drops for errors
        confidence = 1.0
        if error_count > 0:
            confidence -= min(0.6, 0.15 * error_count)
        if warning_count > 0:
            confidence -= min(0.3, 0.05 * warning_count)
        confidence = max(0.1, confidence)

        confidence_summary = {
            "score": confidence,
            "rating": "HIGH" if confidence >= 0.85 else ("MEDIUM" if confidence >= 0.60 else "LOW")
        }

        metadata = ReportMetadata(
            report_id=f"rep:storage:{uuid.uuid4().hex[:12]}",
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
            request_id=self.request_id,
            migration_id=self.migration_id,
            replay_id=None,
            generated_timestamp=datetime.now(timezone.utc),
            execution_duration_ms=execution_duration_ms,
            subsystem_version="1.0.0",
            diagnostics_summary=diagnostics_summary,
            warning_count=warning_count,
            error_count=error_count,
            recommendation_count=0,
            confidence_summary=confidence_summary
        )

        return StorageReport(
            metadata=metadata,
            total_tables=base_report.total_tables,
            projected_total_size_kb=base_report.projected_total_size_kb,
            allocations=base_report.allocations,
            warnings=tuple(d.message for d in diagnostics)
        )
