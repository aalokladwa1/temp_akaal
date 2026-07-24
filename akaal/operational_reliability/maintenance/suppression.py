"""
AKAAL Platform 7 — Maintenance Alert Suppression Engine.
"""

from akaal.operational_reliability.maintenance.maintenance_manager import MaintenanceManager


class AlertSuppressionEngine:
    """Suppresses false production alerts during approved maintenance windows."""

    def __init__(self, manager: MaintenanceManager) -> None:
        self._manager = manager

    def should_suppress_alert(self, service_id: str) -> bool:
        return self._manager.is_service_in_maintenance(service_id)
