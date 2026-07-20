"""Append-Only Event Store with snapshotting, event replay, and WORM compliance."""

import threading
from typing import Dict, List, Optional, Tuple
from akaal.workflow.events.cloudevents import CloudEventV1
from akaal.workflow.utils.clock import IClock, SystemClock
from akaal.workflow.utils.id_generator import IIdGenerator, UUIDIdGenerator


class EventStore:
    """Thread-safe append-only event store supporting event sourcing and snapshots."""

    def __init__(self, clock: IClock | None = None, id_generator: IIdGenerator | None = None) -> None:
        self._clock = clock or SystemClock()
        self._id_generator = id_generator or UUIDIdGenerator()
        self._events: List[CloudEventV1] = []
        self._snapshots: Dict[str, Tuple[int, dict]] = {}  # key: workflow_id -> (event_index, snapshot_data)
        self._legal_holds: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def append(self, event: CloudEventV1) -> CloudEventV1:
        """Append a new CloudEvent to the immutable event log."""
        with self._lock:
            self._events.append(event)
            return event

    def get_events_for_subject(self, subject: str, from_index: int = 0) -> List[CloudEventV1]:
        """Fetch all domain events for a given workflow subject."""
        with self._lock:
            return [e for i, e in enumerate(self._events[from_index:]) if e.subject == subject]

    def create_snapshot(self, workflow_id: str, snapshot_data: dict) -> int:
        """Create a state snapshot for a workflow instance at current event offset."""
        with self._lock:
            index = len(self._events)
            self._snapshots[workflow_id] = (index, snapshot_data)
            return index

    def get_latest_snapshot(self, workflow_id: str) -> Optional[Tuple[int, dict]]:
        with self._lock:
            return self._snapshots.get(workflow_id)

    def set_legal_hold(self, workflow_id: str, hold: bool) -> None:
        """Set legal hold status preventing compaction or pruning."""
        with self._lock:
            self._legal_holds[workflow_id] = hold

    def is_legal_hold_active(self, workflow_id: str) -> bool:
        with self._lock:
            return self._legal_holds.get(workflow_id, False)

    def count(self) -> int:
        with self._lock:
            return len(self._events)
