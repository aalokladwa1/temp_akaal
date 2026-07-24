"""
AKAAL Platform 7 — Service Health Aggregator.
"""

from typing import Dict, Optional, List
import datetime

from akaal.operational_reliability.domain.models import ServiceHealthNode
from akaal.operational_reliability.domain.enums import HealthStatus


class ServiceHealthAggregator:
    """Aggregates latency, error rates, and availability across monitored services."""

    def __init__(self) -> None:
        self._nodes: Dict[str, ServiceHealthNode] = {}

    def ingest_health(self, service_id: str, status: HealthStatus, latency_p99_ms: float, error_rate_pct: float) -> ServiceHealthNode:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        node = ServiceHealthNode(
            service_id=service_id,
            status=status,
            latency_p99_ms=latency_p99_ms,
            error_rate_pct=error_rate_pct,
            updated_at=now,
        )
        self._nodes[service_id] = node
        return node

    def get_service_health(self, service_id: str) -> Optional[ServiceHealthNode]:
        return self._nodes.get(service_id)

    def compute_aggregate_status(self) -> HealthStatus:
        if not self._nodes:
            return HealthStatus.HEALTHY
        statuses = [n.status for n in self._nodes.values()]
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
