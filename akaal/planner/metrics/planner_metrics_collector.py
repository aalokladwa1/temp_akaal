"""
Akaal — Planner Metrics Collector
====================================
Operational metrics collector for Planner Platform pipeline execution.
"""

from typing import Dict, Any


class PlannerMetricsCollector:
    """Operational metrics collector for Planner Platform."""

    def __init__(self) -> None:
        self.total_tasks_planned: int = 0
        self.total_stages: int = 0
        self.total_decisions: int = 0
        self.planning_time_ms: float = 0.0
        self.conflict_count: int = 0

    def record_planning_time(self, duration_ms: float) -> None:
        self.planning_time_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks_planned": self.total_tasks_planned,
            "total_stages": self.total_stages,
            "total_decisions": self.total_decisions,
            "planning_time_ms": round(self.planning_time_ms, 2),
            "conflict_count": self.conflict_count,
        }
