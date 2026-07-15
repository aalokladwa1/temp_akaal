"""
Akaal — Compression Report Builder
===================================
Constructs the final CompressionReport, compiling metadata,
statistics summaries, diagnostic lints, and recommended actions.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from akaal.core.intelligence.common.models import ReportMetadata, Diagnostic, Severity
from akaal.core.intelligence.compression_aware.models import (
    CompressionReport,
    CompressionStatistics,
    CompressionSummary,
    CompressionTranslation,
    CompressionRecommendation,
)


class CompressionReportBuilder:
    """Consolidates metadata metrics and translates diagnostics into a CompressionReport."""

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
        statistics: CompressionStatistics,
        summary: CompressionSummary,
        translations: Dict[str, CompressionTranslation],
        recommendations: List[CompressionRecommendation],
        diagnostics: List[Diagnostic],
        execution_duration_ms: float
    ) -> CompressionReport:
        """Assembles metrics, recommendations, and diagnostic lints into a CompressionReport."""
        warning_count = sum(1 for d in diagnostics if d.severity == Severity.WARNING)
        error_count = sum(1 for d in diagnostics if d.severity == Severity.CRITICAL)

        diagnostics_summary = {
            "warnings": warning_count,
            "errors": error_count,
            "infos": sum(1 for d in diagnostics if d.severity == Severity.INFO)
        }

        # Compute confidence: starts at 1.0, falls for translations loss or warnings
        confidence = 1.0
        if error_count > 0:
            confidence -= min(0.5, 0.10 * error_count)
        if warning_count > 0:
            confidence -= min(0.3, 0.05 * warning_count)
        
        # Factor in average ratio loss to represent capacity confidence
        loss_factor = sum(t.estimated_ratio_loss for t in translations.values()) / max(1, len(translations))
        confidence -= min(0.20, loss_factor * 0.5)
        confidence = max(0.10, round(confidence, 4))

        confidence_summary = {
            "score": confidence,
            "rating": "HIGH" if confidence >= 0.85 else ("MEDIUM" if confidence >= 0.60 else "LOW")
        }

        metadata = ReportMetadata(
            report_id=f"rep:compression:{uuid.uuid4().hex[:12]}",
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
            recommendation_count=len(recommendations),
            confidence_summary=confidence_summary
        )

        return CompressionReport(
            metadata=metadata,
            statistics=statistics,
            summary=summary,
            translations=translations,
            recommendations=tuple(recommendations),
            diagnostics=tuple(diagnostics),
            warnings=tuple(d.message for d in diagnostics if d.severity == Severity.WARNING)
        )
