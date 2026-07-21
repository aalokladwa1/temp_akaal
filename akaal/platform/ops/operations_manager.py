"""
AKAAL Platform Part 6 - Operations Subsystem.
Runbook Manager, Incident Lifecycle Manager & Maintenance Windows.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Callable, Dict, List, Optional


class IncidentState(Enum):
    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


@dataclass
class Incident:
    incident_id: str
    title: str
    severity: str
    state: IncidentState
    created_at_ms: int
    updated_at_ms: int
    assigned_runbook: Optional[str] = None


class RunbookManager:
    """Automated operational runbook executor."""

    def __init__(self) -> None:
        self._runbooks: Dict[str, Callable[[], bool]] = {}

    def register_runbook(self, name: str, procedure: Callable[[], bool]) -> None:
        self._runbooks[name] = procedure

    def execute_runbook(self, name: str) -> bool:
        procedure = self._runbooks.get(name)
        if procedure:
            try:
                return procedure()
            except Exception:
                return False
        return True


class IncidentManager:
    """State machine managing incident lifecycle."""

    def __init__(self) -> None:
        self._incidents: Dict[str, Incident] = {}

    def create_incident(self, title: str, severity: str) -> Incident:
        inc_id = f"inc-{len(self._incidents) + 1}"
        ts = int(time.time() * 1000)
        inc = Incident(
            incident_id=inc_id,
            title=title,
            severity=severity,
            state=IncidentState.DETECTED,
            created_at_ms=ts,
            updated_at_ms=ts,
        )
        self._incidents[inc_id] = inc
        return inc

    def transition_state(self, inc_id: str, new_state: IncidentState) -> bool:
        inc = self._incidents.get(inc_id)
        if inc:
            inc.state = new_state
            inc.updated_at_ms = int(time.time() * 1000)
            return True
        return False


class MaintenanceManager:
    """Manages scheduled maintenance windows for cluster nodes."""

    def __init__(self) -> None:
        self._active_window = False

    def start_maintenance_window(self) -> None:
        self._active_window = True

    def end_maintenance_window(self) -> None:
        self._active_window = False

    def is_in_maintenance(self) -> bool:
        return self._active_window


class OperationsManager:
    """Master controller orchestrating runbooks, incident lifecycles, and maintenance windows."""

    def __init__(self) -> None:
        self.runbooks = RunbookManager()
        self.incidents = IncidentManager()
        self.maintenance = MaintenanceManager()
