"""
Optimization Snapshot Manager.
Captures system configurations, limits, active profiles, and health scores for diagnostic comparisons.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from threading import RLock


class OptimizationSnapshot:
    """Immutable diagnostic snapshot record."""

    def __init__(
        self,
        session_id: str,
        snapshot_type: str,
        runtime_config: Dict[str, Any],
        active_profile: str,
        active_rules: List[str],
        active_policies: List[str],
        resource_limits: Dict[str, Any],
        metrics: Dict[str, Any],
        health_score: float,
        optimizer_states: Dict[str, Any]
    ) -> None:
        self.session_id = session_id
        self.snapshot_type = snapshot_type  # "Pre-Optimization", "Post-Optimization", "Rollback"
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.runtime_config = dict(runtime_config)
        self.active_profile = active_profile
        self.active_rules = list(active_rules)
        self.active_policies = list(active_policies)
        self.resource_limits = dict(resource_limits)
        self.metrics = dict(metrics)
        self.health_score = health_score
        self.optimizer_states = dict(optimizer_states)


class OptimizationSnapshotManager:
    """Manages creation, retrieval, and historical comparisons of optimization snapshots."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshots: Dict[str, Dict[str, OptimizationSnapshot]] = {}

    def capture_snapshot(
        self,
        session_id: str,
        snapshot_type: str,
        runtime_config: Dict[str, Any],
        active_profile: str,
        active_rules: List[str],
        active_policies: List[str],
        resource_limits: Dict[str, Any],
        metrics: Dict[str, Any],
        health_score: float,
        optimizer_states: Dict[str, Any]
    ) -> OptimizationSnapshot:
        with self._lock:
            snap = OptimizationSnapshot(
                session_id=session_id,
                snapshot_type=snapshot_type,
                runtime_config=runtime_config,
                active_profile=active_profile,
                active_rules=active_rules,
                active_policies=active_policies,
                resource_limits=resource_limits,
                metrics=metrics,
                health_score=health_score,
                optimizer_states=optimizer_states
            )
            if session_id not in self._snapshots:
                self._snapshots[session_id] = {}
            self._snapshots[session_id][snapshot_type] = snap
            return snap

    def get_snapshot(self, session_id: str, snapshot_type: str) -> Optional[OptimizationSnapshot]:
        with self._lock:
            return self._snapshots.get(session_id, {}).get(snapshot_type)
