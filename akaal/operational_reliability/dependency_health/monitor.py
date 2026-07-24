"""
AKAAL Platform 7 — Dependency Health Monitor.
"""

from typing import Dict, List, Optional
from akaal.operational_reliability.domain.models import DependencyHealthNode
from akaal.operational_reliability.domain.enums import HealthStatus


class DependencyHealthMonitor:
    """Monitors inter-service and cross-platform dependency health graph."""

    def __init__(self) -> None:
        self._dependencies: Dict[str, DependencyHealthNode] = {}

    def register_dependency(self, source_id: str, target_id: str, status: HealthStatus, cascade_risk_score: float) -> DependencyHealthNode:
        key = f"{source_id}->{target_id}"
        node = DependencyHealthNode(
            source_service_id=source_id,
            target_service_id=target_id,
            status=status,
            cascade_risk_score=cascade_risk_score,
        )
        self._dependencies[key] = node
        return node

    def list_dependencies_for_service(self, service_id: str) -> List[DependencyHealthNode]:
        return [d for d in self._dependencies.values() if d.source_service_id == service_id or d.target_service_id == service_id]
