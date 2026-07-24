"""ResilienceEngSession: Session state tracking object."""

import time
import uuid
from typing import List, Optional
from akaal.resilience_eng.core.models import ResilienceExperimentResult, ResilienceEngStatus


class ResilienceEngSession:
    """State tracking object for active resilience experiment pipeline run."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.results: List[ResilienceExperimentResult] = []
        self.state: ResilienceEngStatus = ResilienceEngStatus.PENDING

    @property
    def total_actions_executed(self) -> int:
        return sum(r.total_actions for r in self.results)

    @property
    def is_successful(self) -> bool:
        return all(r.status == ResilienceEngStatus.COMPLETED for r in self.results)

    def add_result(self, result: ResilienceExperimentResult) -> None:
        self.results.append(result)

    def mark_completed(self) -> None:
        self.end_time = time.time()
        self.state = ResilienceEngStatus.COMPLETED if self.is_successful else ResilienceEngStatus.FAILED
