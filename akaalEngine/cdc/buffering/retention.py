"""
akaalEngine.cdc.buffering.retention
===================================
Source Log Retention Monitor evaluating WAL, binlog, and archive log retention pressure.
"""

from typing import Any, Dict, Optional

from akaalEngine.cdc.models.capabilities import RetentionState


class SourceRetentionMonitor:
    """Monitors source log retention remaining capacity and emits warning/critical alert states."""

    def __init__(self, warning_threshold_percent: float = 15.0) -> None:
        self.warning_threshold_percent = warning_threshold_percent

    def evaluate_retention(
        self,
        engine_name: str,
        total_capacity_bytes: int,
        used_bytes: int,
    ) -> RetentionState:
        if total_capacity_bytes <= 0:
            return RetentionState.UNKNOWN

        free_bytes = total_capacity_bytes - used_bytes
        free_percent = (free_bytes / total_capacity_bytes) * 100.0

        if free_percent <= 0:
            return RetentionState.RETENTION_LOST
        elif free_percent <= 5.0:
            return RetentionState.CRITICAL
        elif free_percent <= self.warning_threshold_percent:
            return RetentionState.WARNING
        return RetentionState.HEALTHY
