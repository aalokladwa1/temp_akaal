"""
AKAAL Platform 7 — Maintenance Scheduler.
"""

from typing import List
from akaal.operational_reliability.domain.models import MaintenanceWindow


class MaintenanceScheduler:
    """Schedules and coordinates non-overlapping operational change windows."""

    def detect_overlapping_windows(self, windows: List[MaintenanceWindow]) -> bool:
        sorted_w = sorted(windows, key=lambda x: x.start_time)
        for i in range(len(sorted_w) - 1):
            if sorted_w[i].end_time > sorted_w[i+1].start_time and sorted_w[i].service_id == sorted_w[i+1].service_id:
                return True
        return False
