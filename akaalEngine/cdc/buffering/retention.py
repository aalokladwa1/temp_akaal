from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from akaalEngine.cdc.models.capabilities import RetentionState


@dataclass
class RetentionAssessment:
    state: RetentionState = RetentionState.HEALTHY
    remaining_seconds: Optional[float] = 86400.0
    free_percent: float = 100.0
    details: Optional[Dict[str, Any]] = None


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

    def assess_retention(self, adapter: Any) -> RetentionAssessment:
        if adapter is None:
            return RetentionAssessment(state=RetentionState.HEALTHY, remaining_seconds=86400.0)
        if hasattr(adapter, "get_retention_assessment"):
            try:
                res = adapter.get_retention_assessment()
                if isinstance(res, RetentionAssessment):
                    return res
                if isinstance(res, dict):
                    return RetentionAssessment(
                        state=RetentionState(res.get("state", "HEALTHY")),
                        remaining_seconds=res.get("remaining_seconds", 86400.0),
                        free_percent=res.get("free_percent", 100.0),
                        details=res.get("details"),
                    )
            except Exception:
                pass
        return RetentionAssessment(state=RetentionState.HEALTHY, remaining_seconds=86400.0, free_percent=100.0)
