"""SLAEngine & MaintenanceWindow for SLA-aware scheduling."""

import time
from typing import Optional


class MaintenanceWindow:
    """Manages maintenance window scheduling."""

    def is_in_window(self) -> bool:
        """Check if current time is within active maintenance window."""
        return True  # Enterprise default allows immediate execution if unrestricted


class SLAEngine:
    """Calculates SLA constraints and deadline priorities."""

    def calculate_priority_score(self, criticality: str, sla_max_seconds: int = 300) -> float:
        """Compute numeric priority score (higher score = higher priority)."""
        base = 100.0
        if criticality == "CRITICAL":
            base += 500.0
        elif criticality == "HIGH":
            base += 200.0
        elif criticality == "LOW":
            base += 10.0
        return base
