"""
Enterprise Incident Management Platform.
Implements incident state machine and lifecycle handling.
"""

from typing import Dict, List, Optional, Any
from threading import RLock
from enum import Enum
import time


class IncidentState(Enum):
    DETECTED = "Detected"
    CLASSIFIED = "Classified"
    ASSIGNED = "Assigned"
    INVESTIGATING = "Investigating"
    MITIGATING = "Mitigating"
    RECOVERING = "Recovering"
    VERIFYING = "Verifying"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class IncidentRecord:
    """Represents a tracked operational incident."""

    _VALID_TRANSITIONS = {
        IncidentState.DETECTED: [IncidentState.CLASSIFIED, IncidentState.CLOSED],
        IncidentState.CLASSIFIED: [IncidentState.ASSIGNED, IncidentState.CLOSED],
        IncidentState.ASSIGNED: [IncidentState.INVESTIGATING, IncidentState.CLOSED],
        IncidentState.INVESTIGATING: [IncidentState.MITIGATING, IncidentState.CLOSED],
        IncidentState.MITIGATING: [IncidentState.RECOVERING, IncidentState.CLOSED],
        IncidentState.RECOVERING: [IncidentState.VERIFYING, IncidentState.CLOSED],
        IncidentState.VERIFYING: [IncidentState.RESOLVED, IncidentState.CLOSED],
        IncidentState.RESOLVED: [IncidentState.CLOSED],
        IncidentState.CLOSED: []
    }

    def __init__(self, incident_id: str, title: str, severity: str = "HIGH") -> None:
        self._lock = RLock()
        self.incident_id = incident_id
        self.title = title
        self.severity = severity
        self.state = IncidentState.DETECTED
        self.assignee: Optional[str] = None
        self.created_at = time.time()
        self.closed_at: Optional[float] = None
        self.resolution_notes = ""

    def transition_to(self, target_state: IncidentState, reason: str = "") -> None:
        with self._lock:
            allowed = self._VALID_TRANSITIONS.get(self.state, [])
            if target_state not in allowed:
                raise ValueError(f"Invalid incident state transition from '{self.state.value}' to '{target_state.value}'.")
            self.state = target_state
            if target_state == IncidentState.CLOSED:
                self.closed_at = time.time()


class IncidentLifecycleManager:
    """Manages creation, tracking, and transitions of incidents."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._incidents: Dict[str, IncidentRecord] = {}

    def create_incident(self, title: str, severity: str = "HIGH") -> IncidentRecord:
        with self._lock:
            iid = f"inc_{time.time_ns()}_{len(self._incidents)}"
            inc = IncidentRecord(iid, title, severity)
            self._incidents[iid] = inc
            return inc

    def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        with self._lock:
            return self._incidents.get(incident_id)

    def transition_incident(self, incident_id: str, target_state: IncidentState, reason: str = "") -> bool:
        with self._lock:
            inc = self._incidents.get(incident_id)
            if not inc:
                return False
            inc.transition_to(target_state, reason)
            return True
