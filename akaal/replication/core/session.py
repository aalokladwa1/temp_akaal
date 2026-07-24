"""ReplicationSession: Represents a single execution run across domain replicators."""

import time
import uuid
from typing import List, Dict, Any, Optional
from akaal.replication.core.models import ReplicationResult, ReplicationStatus, ReplicationOutcome


class ReplicationSession:
    """State tracking object for active replication pipeline run."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.results: List[ReplicationResult] = []
        self.state: ReplicationStatus = ReplicationStatus.PENDING

    @property
    def total_actions_executed(self) -> int:
        return sum(r.total_actions for r in self.results)

    @property
    def is_successful(self) -> bool:
        return all(r.status == ReplicationStatus.COMPLETED for r in self.results)

    def add_result(self, result: ReplicationResult) -> None:
        self.results.append(result)

    def mark_completed(self) -> None:
        self.end_time = time.time()
        self.state = ReplicationStatus.COMPLETED if self.is_successful else ReplicationStatus.FAILED
