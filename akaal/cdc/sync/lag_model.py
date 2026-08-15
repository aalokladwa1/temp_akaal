"""
AKAAL CDC Engine-Aware Lag Model & Synchronization Stability Evaluator.
========================================================================
Tracks captured, buffered, applied, checkpointed, and acknowledged positions with engine-aware lag semantics,
backlog metrics, and configurable stability window evaluations.
"""

from typing import Dict, Any, Optional, List
import time
import datetime
import logging

from akaal.cdc.domain.positions import CDCSourcePosition

logger = logging.getLogger(__name__)


class CDCLagMetrics:
    """Engine-aware CDC Lag and Catch-up Metrics representation."""

    def __init__(
        self,
        cdc_session_id: str,
        source_engine: str,
        captured_position: Optional[CDCSourcePosition] = None,
        applied_position: Optional[CDCSourcePosition] = None,
        acknowledged_position: Optional[CDCSourcePosition] = None,
        buffered_transactions: int = 0,
        buffered_events: int = 0,
        buffered_bytes: int = 0,
        capture_rate_events_sec: float = 0.0,
        apply_rate_events_sec: float = 0.0,
        time_lag_ms: float = 0.0,
    ) -> None:
        self.cdc_session_id = cdc_session_id
        self.source_engine = source_engine.upper()
        self.captured_position = captured_position
        self.applied_position = applied_position
        self.acknowledged_position = acknowledged_position
        self.buffered_transactions = buffered_transactions
        self.buffered_events = buffered_events
        self.buffered_bytes = buffered_bytes
        self.capture_rate_events_sec = capture_rate_events_sec
        self.apply_rate_events_sec = apply_rate_events_sec
        self.time_lag_ms = time_lag_ms

    def estimate_catchup_time_sec(self) -> float:
        """Estimates remaining catch-up time based on apply rate and event backlog."""
        if self.buffered_events == 0:
            return 0.0
        rate = max(0.1, self.apply_rate_events_sec)
        return round(self.buffered_events / rate, 2)

    def is_backlog_zero(self) -> bool:
        return self.buffered_events == 0 and self.buffered_transactions == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cdc_session_id": self.cdc_session_id,
            "source_engine": self.source_engine,
            "captured_position": self.captured_position.to_string() if self.captured_position else None,
            "applied_position": self.applied_position.to_string() if self.applied_position else None,
            "acknowledged_position": self.acknowledged_position.to_string() if self.acknowledged_position else None,
            "buffered_transactions": self.buffered_transactions,
            "buffered_events": self.buffered_events,
            "buffered_bytes": self.buffered_bytes,
            "capture_rate_events_sec": round(self.capture_rate_events_sec, 2),
            "apply_rate_events_sec": round(self.apply_rate_events_sec, 2),
            "time_lag_ms": round(self.time_lag_ms, 2),
            "estimated_catchup_time_sec": self.estimate_catchup_time_sec(),
        }


class CDCSynchronizationStabilityEvaluator:
    """Evaluates sustained synchronization stability over a configurable observation window."""

    def __init__(
        self,
        required_stability_window_sec: float = 10.0,
        required_observation_count: int = 3,
        max_allowed_lag_ms: float = 2000.0,
        max_allowed_backlog_events: int = 5,
    ) -> None:
        self.required_stability_window_sec = required_stability_window_sec
        self.required_observation_count = required_observation_count
        self.max_allowed_lag_ms = max_allowed_lag_ms
        self.max_allowed_backlog_events = max_allowed_backlog_events

        self.synchronized_since: Optional[float] = None
        self.consecutive_stable_observations: int = 0

    def evaluate(self, metrics: CDCLagMetrics) -> Dict[str, Any]:
        """Evaluates current metrics against stability requirements."""
        now = time.time()
        is_lag_low = metrics.time_lag_ms <= self.max_allowed_lag_ms
        is_backlog_low = metrics.buffered_events <= self.max_allowed_backlog_events

        is_currently_stable = is_lag_low and is_backlog_low

        if is_currently_stable:
            if self.synchronized_since is None:
                self.synchronized_since = now
            self.consecutive_stable_observations += 1
        else:
            # Reset stability window on regression!
            self.synchronized_since = None
            self.consecutive_stable_observations = 0

        elapsed_stable = (now - self.synchronized_since) if self.synchronized_since else 0.0
        is_sustained = (
            self.synchronized_since is not None
            and elapsed_stable >= self.required_stability_window_sec
            and self.consecutive_stable_observations >= self.required_observation_count
        )

        return {
            "is_synchronized": is_sustained,
            "is_currently_stable": is_currently_stable,
            "consecutive_observations": self.consecutive_stable_observations,
            "required_observations": self.required_observation_count,
            "elapsed_stable_sec": round(elapsed_stable, 2),
            "required_stable_sec": self.required_stability_window_sec,
            "metrics": metrics.to_dict(),
        }
