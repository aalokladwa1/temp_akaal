"""
Enterprise Operations Center.
Aggregates cluster statuses, active jobs, worker statuses, and queue overviews.
"""

from typing import Dict, Any
from threading import RLock

from akaal.operations.digital_twin.model import DigitalTwinModel
from akaal.operations.capability_registry.registry import OperationsCapabilityRegistry
from akaal.operations.health.engine import OperationsHealthEngine


class OperationsCenter:
    """Central operational monitoring view."""

    def __init__(
        self,
        digital_twin: DigitalTwinModel,
        capability_registry: OperationsCapabilityRegistry,
        health_engine: OperationsHealthEngine
    ) -> None:
        self._lock = RLock()
        self.digital_twin = digital_twin
        self.capability_registry = capability_registry
        self.health_engine = health_engine

    def get_dashboard_overview(self) -> Dict[str, Any]:
        with self._lock:
            twin_snapshot = self.digital_twin.get_snapshot()
            health_summary = self.health_engine.get_health_breakdown()
            capabilities = self.capability_registry.list_capabilities()

            return {
                "system_health": health_summary["overall_score"],
                "active_nodes_count": len(twin_snapshot["nodes"]),
                "active_workers_count": len(twin_snapshot["workers"]),
                "active_jobs_count": len(twin_snapshot["active_jobs"]),
                "registered_platforms": list(capabilities.keys()),
                "maintenance_mode": twin_snapshot["maintenance_mode"],
                "timestamp": twin_snapshot["last_updated"]
            }
