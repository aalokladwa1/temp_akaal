"""Pipeline Execution State Machine for Platform 5: explicit lifecycle management with 13 states."""

import time
import threading
from enum import Enum
from typing import Optional, Dict, Any


class PipelineStage(str, Enum):
    REQUESTED = "REQUESTED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    RESOURCES_RESERVED = "RESOURCES_RESERVED"
    DIGITAL_TWIN_BUILT = "DIGITAL_TWIN_BUILT"
    SIMULATION_COMPLETE = "SIMULATION_COMPLETE"
    EXECUTING = "EXECUTING"
    RECOVERING = "RECOVERING"
    VALIDATED = "VALIDATED"
    CERTIFIED = "CERTIFIED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


# Valid forward transitions
VALID_TRANSITIONS: Dict[PipelineStage, PipelineStage] = {
    PipelineStage.REQUESTED: PipelineStage.REVIEWED,
    PipelineStage.REVIEWED: PipelineStage.APPROVED,
    PipelineStage.APPROVED: PipelineStage.SCHEDULED,
    PipelineStage.SCHEDULED: PipelineStage.RESOURCES_RESERVED,
    PipelineStage.RESOURCES_RESERVED: PipelineStage.DIGITAL_TWIN_BUILT,
    PipelineStage.DIGITAL_TWIN_BUILT: PipelineStage.SIMULATION_COMPLETE,
    PipelineStage.SIMULATION_COMPLETE: PipelineStage.EXECUTING,
    PipelineStage.EXECUTING: PipelineStage.RECOVERING,
    PipelineStage.RECOVERING: PipelineStage.VALIDATED,
    PipelineStage.VALIDATED: PipelineStage.CERTIFIED,
    PipelineStage.CERTIFIED: PipelineStage.COMPLETED,
    PipelineStage.COMPLETED: PipelineStage.ARCHIVED,
}


class PipelineExecutionStateMachine:
    """Explicit lifecycle state machine for resilience experiment execution pipeline."""

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.current_stage: PipelineStage = PipelineStage.REQUESTED
        self._stage_history: list = [(PipelineStage.REQUESTED, time.time())]
        self._lock = threading.RLock()

    def advance(self) -> PipelineStage:
        with self._lock:
            next_stage = VALID_TRANSITIONS.get(self.current_stage)
            if next_stage is None:
                raise ValueError(f"Cannot advance from terminal stage {self.current_stage}")
            self.current_stage = next_stage
            self._stage_history.append((self.current_stage, time.time()))
            return self.current_stage

    def advance_to_archived(self) -> None:
        """Advance through all remaining stages to ARCHIVED."""
        with self._lock:
            while self.current_stage != PipelineStage.ARCHIVED:
                next_stage = VALID_TRANSITIONS.get(self.current_stage)
                if next_stage is None:
                    break
                self.current_stage = next_stage
                self._stage_history.append((self.current_stage, time.time()))

    def get_state_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "experiment_id": self.experiment_id,
                "current_stage": self.current_stage.value,
                "stages_completed": len(self._stage_history),
                "stage_history": [(s.value, t) for s, t in self._stage_history],
            }

    @property
    def is_complete(self) -> bool:
        with self._lock:
            return self.current_stage in (PipelineStage.COMPLETED, PipelineStage.ARCHIVED)
