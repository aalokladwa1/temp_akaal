"""ReliabilitySession: State tracking object for reliability runs."""

import time
import uuid
from typing import List, Dict, Any, Optional
from akaal.reliability.core.models import ReliabilityResult, ReliabilityStatus, ReliabilityOutcome


class ReliabilitySession:
    """State tracking object for active reliability pipeline run."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.results: List[ReliabilityResult] = []
        self.state: ReliabilityStatus = ReliabilityStatus.PENDING

    @property
    def total_actions_executed(self) -> int:
        return sum(r.total_actions for r in self.results)

    @property
    def is_successful(self) -> bool:
        return all(r.status in (ReliabilityStatus.COMPLETED, ReliabilityStatus.DEGRADED) for r in self.results)

    def add_result(self, result: ReliabilityResult) -> None:
        self.results.append(result)

    def mark_completed(self) -> None:
        self.end_time = time.time()
        self.state = ReliabilityStatus.COMPLETED if self.is_successful else ReliabilityStatus.FAILED
