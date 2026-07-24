"""
AKAAL Platform 7 — Maintenance Window Manager.
"""

from typing import Dict, List, Optional
import datetime
import uuid

from akaal.operational_reliability.domain.models import MaintenanceWindow
from akaal.operational_reliability.domain.enums import MaintenanceState, MaintenanceType


class MaintenanceManager:
    """Manages planned downtime, change windows, and maintenance schedules."""

    def __init__(self) -> None:
        self._windows: Dict[str, MaintenanceWindow] = {}

    def schedule_maintenance(
        self,
        service_id: str,
        title: str,
        maintenance_type: MaintenanceType,
        start_time: str,
        end_time: str,
        suppress_alerts: bool = True,
        approved_by: str = "change_advisory_board",
    ) -> MaintenanceWindow:
        window_id = f"maint-{uuid.uuid4().hex[:8]}"
        window = MaintenanceWindow(
            window_id=window_id,
            service_id=service_id,
            title=title,
            maintenance_type=maintenance_type,
            state=MaintenanceState.SCHEDULED,
            start_time=start_time,
            end_time=end_time,
            suppress_alerts=suppress_alerts,
            approved_by=approved_by,
        )
        self._windows[window_id] = window
        return window

    def is_service_in_maintenance(self, service_id: str) -> bool:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for w in self._windows.values():
            if w.service_id == service_id and w.state in [MaintenanceState.SCHEDULED, MaintenanceState.IN_PROGRESS]:
                if w.start_time <= now <= w.end_time:
                    return True
        return False

    def list_active_windows(self) -> List[MaintenanceWindow]:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return [w for w in self._windows.values() if w.start_time <= now <= w.end_time]
