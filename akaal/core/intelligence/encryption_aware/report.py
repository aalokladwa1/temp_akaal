"""
Akaal — Encryption Report Builder
=================================
Assembles diagnostic outcome logs, statistics, and recommendations into reports.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional

from akaal.core.intelligence.common.models import ReportMetadata, Diagnostic, Severity
from akaal.core.intelligence.encryption_aware.models import (
    EncryptionReport,
    EncryptionStatistics,
    EncryptionSummary,
    EncryptionRecommendation,
    EncryptionTranslation,
)

class EncryptionReportBuilder:
    """Assembles diagnostics, telemetry data, and translation plans into an EncryptionReport."""

    def __init__(
        self,
        correlation_id: str,
        trace_id: str,
        request_id: str,
        migration_id: str,
        replay_id: Optional[str] = None
    ) -> None:
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.request_id = request_id
        self.migration_id = migration_id
        self.replay_id = replay_id

    def build_report(
        self,
        statistics: EncryptionStatistics,
        summary: EncryptionSummary,
        translations: Dict[str, EncryptionTranslation],
        recommendations: Tuple[EncryptionRecommendation, ...],
        diagnostics: Tuple[Diagnostic, ...],
        duration_ms: float,
        warnings: Tuple[str, ...] = ()
    ) -> EncryptionReport:
        """Assembles and returns the final immutable EncryptionReport."""
        warning_count = sum(1 for d in diagnostics if d.severity == Severity.WARNING)
        error_count = sum(1 for d in diagnostics if d.severity == Severity.CRITICAL)

        diagnostics_summary = {
            "warnings": warning_count,
            "errors": error_count,
            "infos": sum(1 for d in diagnostics if d.severity == Severity.INFO)
        }

        # Compute confidence score
        confidence = 1.0
        if error_count > 0:
            confidence -= min(0.5, 0.10 * error_count)
        if warning_count > 0:
            confidence -= min(0.3, 0.05 * warning_count)
        confidence = max(0.10, round(confidence, 4))

        confidence_summary = {
            "score": confidence,
            "rating": "HIGH" if confidence >= 0.85 else ("MEDIUM" if confidence >= 0.60 else "LOW")
        }

        metadata = ReportMetadata(
            report_id=f"rep:encryption:{uuid.uuid4().hex[:12]}",
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
            recommendation_count=len(recommendations),
            confidence_summary=confidence_summary
        )

        return EncryptionReport(
            metadata=metadata,
            statistics=statistics,
            summary=summary,
            translations=translations,
            recommendations=recommendations,
            diagnostics=diagnostics,
            warnings=warnings
        )
