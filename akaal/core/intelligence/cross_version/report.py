"""
Akaal — Cross-Version Compatibility Report Builder
===================================================
Assembles findings, diagnostics, statistics, and summary into an
immutable CompatibilityReport using shared ReportMetadata conventions.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.models import DbVersion
from akaal.core.intelligence.common.models import ReportMetadata, Diagnostic, Severity
from akaal.core.intelligence.cross_version.models import (
    CompatibilityReport,
    CompatibilityFinding,
    CompatibilityStatistics,
    CompatibilitySummary,
)


class CompatibilityReportBuilder:
    """
    Constructs a fully populated, immutable CompatibilityReport.

    Usage:
        builder = CompatibilityReportBuilder(
            correlation_id="abc", trace_id="def",
            request_id="req1", migration_id="mig1"
        )
        report = builder.build_report(
            source_dialect=..., target_dialect=...,
            target_version=..., findings=..., ...
        )
    """

    def __init__(
        self,
        correlation_id: str,
        trace_id: str,
        request_id: str,
        migration_id: str,
        replay_id: Optional[str] = None,
    ) -> None:
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.request_id = request_id
        self.migration_id = migration_id
        self.replay_id = replay_id

    def build_report(
        self,
        source_dialect: SystemType,
        target_dialect: SystemType,
        target_version: DbVersion,
        findings: Tuple[CompatibilityFinding, ...],
        diagnostics: Tuple[Diagnostic, ...],
        statistics: CompatibilityStatistics,
        summary: CompatibilitySummary,
        duration_ms: float,
        warnings: Tuple[str, ...] = (),
    ) -> CompatibilityReport:
        """
        Assembles and returns the final immutable CompatibilityReport.

        Args:
            source_dialect: Migration source system type.
            target_dialect: Migration target system type.
            target_version: Target database version.
            findings: Tuple of CompatibilityFinding results.
            diagnostics: Tuple of Diagnostic records.
            statistics: Aggregated CompatibilityStatistics.
            summary: CompatibilitySummary executive overview.
            duration_ms: Total analysis duration in milliseconds.
            warnings: Optional human-readable warning messages.

        Returns:
            Immutable CompatibilityReport.
        """
        warning_count = sum(
            1 for d in diagnostics if d.severity == Severity.WARNING
        )
        error_count = sum(
            1 for d in diagnostics if d.severity == Severity.CRITICAL
        )

        diagnostics_summary = {
            "warnings": warning_count,
            "errors": error_count,
            "infos": sum(
                1 for d in diagnostics if d.severity == Severity.INFO
            ),
        }

        # Confidence degrades with errors and warnings
        confidence = 1.0
        if error_count > 0:
            confidence -= min(0.5, 0.10 * error_count)
        if warning_count > 0:
            confidence -= min(0.3, 0.04 * warning_count)
        confidence = max(0.10, round(confidence, 4))

        confidence_summary = {
            "score": confidence,
            "rating": (
                "HIGH" if confidence >= 0.85
                else ("MEDIUM" if confidence >= 0.60 else "LOW")
            ),
        }

        metadata = ReportMetadata(
            report_id=f"rep:compat:{uuid.uuid4().hex[:12]}",
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
            request_id=self.request_id,
            migration_id=self.migration_id,
            replay_id=self.replay_id,
            generated_timestamp=datetime.now(timezone.utc),
            execution_duration_ms=duration_ms,
            subsystem_version="1.0.0",
            diagnostics_summary=diagnostics_summary,
            warning_count=warning_count,
            error_count=error_count,
            recommendation_count=statistics.blocking_issues_count + statistics.warning_issues_count,
            confidence_summary=confidence_summary,
        )

        return CompatibilityReport(
            metadata=metadata,
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            target_version=target_version,
            statistics=statistics,
            summary=summary,
            findings=findings,
            diagnostics=diagnostics,
            warnings=warnings,
        )
