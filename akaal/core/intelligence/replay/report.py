"""
Akaal — Replay Subsystem Reports
===============================
Implements the ReplayReportBuilder to generate diagnostic reports and statistics
for transaction log validation sessions.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from akaal.core.intelligence.common.models import (
    Diagnostic,
    ReportMetadata,
    ReplayReport,
    Severity,
)
from akaal.core.intelligence.replay.models import ReplaySession


class ReplayReportBuilder:
    """Builder class constructing immutable ReplayReports."""
    def __init__(
        self,
        session_id: str,
        correlation_id: str,
        trace_id: str,
        request_id: str,
        migration_id: str,
        replay_id: str = ""
    ) -> None:
        self.session_id = session_id
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.request_id = request_id
        self.migration_id = migration_id
        self.replay_id = replay_id

    def build_report(
        self,
        session: ReplaySession,
        diagnostics: List[Diagnostic],
        execution_duration_ms: float
    ) -> ReplayReport:
        """Assembles validation alerts, event statistics, and session metrics into a ReplayReport."""
        warning_count = sum(1 for d in diagnostics if d.severity == Severity.WARNING)
        error_count = sum(1 for d in diagnostics if d.severity == Severity.CRITICAL)

        validation_passed = (error_count == 0)

        diagnostics_summary = {
            "warnings": warning_count,
            "errors": error_count,
            "infos": sum(1 for d in diagnostics if d.severity == Severity.INFO)
        }

        # Confidence Scoring: Base 1.0, deduct for issues
        confidence = 1.0
        if error_count > 0:
            confidence -= min(0.8, 0.2 * error_count)
        if warning_count > 0:
            confidence -= min(0.2, 0.05 * warning_count)
        confidence = max(0.0, confidence)

        confidence_summary = {
            "score": confidence,
            "rating": "HIGH" if confidence >= 0.8 else ("MEDIUM" if confidence >= 0.5 else "LOW")
        }

        metadata = ReportMetadata(
            report_id=f"rep:replay:{uuid.uuid4().hex[:12]}",
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
            request_id=self.request_id,
            migration_id=self.migration_id,
            replay_id=self.replay_id or f"rep_session_{self.session_id}",
            generated_timestamp=datetime.now(timezone.utc),
            execution_duration_ms=execution_duration_ms,
            subsystem_version="1.0.0",
            diagnostics_summary=diagnostics_summary,
            warning_count=warning_count,
            error_count=error_count,
            recommendation_count=0,
            confidence_summary=confidence_summary
        )

        timeline_stats = {
            "total_events": session.timeline.statistics.total_events,
            "insert_count": session.timeline.statistics.insert_count,
            "update_count": session.timeline.statistics.update_count,
            "delete_count": session.timeline.statistics.delete_count,
            "sequence_gaps_count": session.timeline.statistics.sequence_gaps_count,
            "out_of_order_count": session.timeline.statistics.out_of_order_count,
            "min_sequence": session.timeline.statistics.min_sequence,
            "max_sequence": session.timeline.statistics.max_sequence,
            "duration_seconds": session.timeline.statistics.duration_seconds
        }

        session_stats = {
            "total_transitions": session.statistics.total_transitions,
            "active_duration_seconds": session.statistics.active_duration_seconds,
            "error_count": session.statistics.error_count,
            "last_checkpoint_sequence": session.statistics.last_checkpoint_sequence,
            "checkpoint_count": session.statistics.checkpoint_count
        }

        replay_summary = {
            "session_id": session.session_id,
            "current_state": session.state.value,
            "checkpoints_recorded": len(session.checkpoints),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }

        validation_summary = {
            "validation_passed": validation_passed,
            "diagnostics_run": len(diagnostics),
            "criticals_found": error_count,
            "warnings_found": warning_count
        }

        # Gather detected gaps commit sequences
        detected_gaps: List[int] = []
        for event in session.timeline.events:
            # We will gather event IDs or commit sequence numbers that represent gaps
            pass

        return ReplayReport(
            metadata=metadata,
            session_id=session.session_id,
            validation_passed=validation_passed,
            detected_gaps=(),
            out_of_order_count=session.timeline.statistics.out_of_order_count,
            timeline_summary={
                "events_count": len(session.timeline.events),
                "has_gaps": session.timeline.statistics.sequence_gaps_count > 0,
                "has_out_of_order": session.timeline.statistics.out_of_order_count > 0
            },
            replay_summary=replay_summary,
            validation_summary=validation_summary,
            timeline_statistics=timeline_stats,
            session_statistics=session_stats
        )
