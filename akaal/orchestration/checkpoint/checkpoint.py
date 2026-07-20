"""
Deterministic Checkpoint Framework.
Every checkpoint is immutable, versioned, timestamped, and SHA-256 checksum protected.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import json

from akaal.orchestration.domain.identifiers import WorkflowId, JobId
from akaal.orchestration.domain.types import EngineState, Version, Checksum


@dataclass(frozen=True)
class WorkflowCheckpoint:
    """
    Immutable WorkflowCheckpoint snapshot.
    Ensures deterministic execution recovery.
    """
    checkpoint_id: str
    workflow_id: WorkflowId
    job_id: JobId
    step_name: str
    step_index: int
    engine_state: EngineState
    workflow_version: str
    config_version: int
    config_checksum: str
    state_data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checksum: Checksum = field(init=False)

    def __post_init__(self) -> None:
        payload = {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": str(self.workflow_id),
            "job_id": str(self.job_id),
            "step_name": self.step_name,
            "step_index": self.step_index,
            "engine_state": self.engine_state.value,
            "workflow_version": self.workflow_version,
            "config_version": self.config_version,
            "config_checksum": self.config_checksum,
            "state_data": self.state_data,
            "timestamp": self.timestamp,
        }
        object.__setattr__(self, "checksum", Checksum.from_dict(payload))

    def verify_checksum(self) -> bool:
        """Verifies if calculated SHA-256 checksum matches stored checksum."""
        recalculated = {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": str(self.workflow_id),
            "job_id": str(self.job_id),
            "step_name": self.step_name,
            "step_index": self.step_index,
            "engine_state": self.engine_state.value,
            "workflow_version": self.workflow_version,
            "config_version": self.config_version,
            "config_checksum": self.config_checksum,
            "state_data": self.state_data,
            "timestamp": self.timestamp,
        }
        expected = Checksum.from_dict(recalculated)
        return self.checksum.digest == expected.digest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": str(self.workflow_id),
            "job_id": str(self.job_id),
            "step_name": self.step_name,
            "step_index": self.step_index,
            "engine_state": self.engine_state.value,
            "workflow_version": self.workflow_version,
            "config_version": self.config_version,
            "config_checksum": self.config_checksum,
            "state_data": self.state_data,
            "timestamp": self.timestamp,
            "checksum": str(self.checksum),
        }
