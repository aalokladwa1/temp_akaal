"""
AKAAL CDC Telemetry & Monitoring DTO Extension Model.
=====================================================
Extends canonical monitoring DTO with CDC capture rate, apply rate, event backlog, time lag,
and position tracking.
"""

from typing import Dict, Any, Optional
import datetime


class CDCMonitoringDTO:
    """Canonical CDC Monitoring DTO extending platform monitoring snapshots."""

    def __init__(
        self,
        cdc_session_id: str,
        migration_id: str,
        job_id: str,
        run_id: str,
        status: str = "SYNCHRONIZED",
        capture_status: str = "CAPTURING",
        events_captured_total: int = 0,
        events_applied_total: int = 0,
        events_acknowledged_total: int = 0,
        event_backlog_count: int = 0,
        time_lag_ms: float = 0.0,
        capture_rate_events_sec: float = 0.0,
        apply_rate_events_sec: float = 0.0,
        captured_position: Optional[str] = None,
        applied_position: Optional[str] = None,
        acknowledged_position: Optional[str] = None,
        active_transactions_count: int = 0,
        catchup_progress_percent: float = 100.0,
        is_cutover_ready: bool = False,
    ) -> None:
        self.cdc_session_id = cdc_session_id
        self.migration_id = migration_id
        self.job_id = job_id
        self.run_id = run_id
        self.status = status
        self.capture_status = capture_status
        self.events_captured_total = events_captured_total
        self.events_applied_total = events_applied_total
        self.events_acknowledged_total = events_acknowledged_total
        self.event_backlog_count = event_backlog_count
        self.time_lag_ms = time_lag_ms
        self.capture_rate_events_sec = capture_rate_events_sec
        self.apply_rate_events_sec = apply_rate_events_sec
        self.captured_position = captured_position
        self.applied_position = applied_position
        self.acknowledged_position = acknowledged_position
        self.active_transactions_count = active_transactions_count
        self.catchup_progress_percent = catchup_progress_percent
        self.is_cutover_ready = is_cutover_ready
        self.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cdc_session_id": self.cdc_session_id,
            "migration_id": self.migration_id,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "status": self.status,
            "capture_status": self.capture_status,
            "events_captured_total": self.events_captured_total,
            "events_applied_total": self.events_applied_total,
            "events_acknowledged_total": self.events_acknowledged_total,
            "event_backlog_count": self.event_backlog_count,
            "time_lag_ms": self.time_lag_ms,
            "capture_rate_events_sec": self.capture_rate_events_sec,
            "apply_rate_events_sec": self.apply_rate_events_sec,
            "captured_position": self.captured_position,
            "applied_position": self.applied_position,
            "acknowledged_position": self.acknowledged_position,
            "active_transactions_count": self.active_transactions_count,
            "catchup_progress_percent": self.catchup_progress_percent,
            "is_cutover_ready": self.is_cutover_ready,
            "updated_at": self.updated_at,
        }
