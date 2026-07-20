"""
CheckpointCoordinator module.
Handles deterministic checkpoint creation, SHA-256 verification, and persistence.
"""

from typing import Dict, Any, Optional
import uuid

from akaal.orchestration.checkpoint.checkpoint import WorkflowCheckpoint
from akaal.orchestration.domain.identifiers import WorkflowId, JobId
from akaal.orchestration.domain.types import EngineState, Version
from akaal.orchestration.domain.errors import CheckpointError
from akaal.orchestration.repository.interfaces import CheckpointRepository
from akaal.orchestration.events.events import EventPublisher, CheckpointCreated


class CheckpointCoordinator:
    """
    Coordinates creation and validation of immutable WorkflowCheckpoint instances.
    """

    def __init__(self, repository: CheckpointRepository, publisher: EventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    def create_checkpoint(
        self,
        workflow_id: WorkflowId,
        job_id: JobId,
        step_name: str,
        step_index: int,
        engine_state: EngineState,
        workflow_version: str,
        config_version: int,
        config_checksum: str,
        state_data: Dict[str, Any],
    ) -> WorkflowCheckpoint:
        """Creates, verifies checksum, persists, and publishes event for a WorkflowCheckpoint."""
        c_id = f"chk_{uuid.uuid4().hex[:12]}"
        checkpoint = WorkflowCheckpoint(
            checkpoint_id=c_id,
            workflow_id=workflow_id,
            job_id=job_id,
            step_name=step_name,
            step_index=step_index,
            engine_state=engine_state,
            workflow_version=workflow_version,
            config_version=config_version,
            config_checksum=config_checksum,
            state_data=state_data,
        )

        if not checkpoint.verify_checksum():
            raise CheckpointError(f"Newly created checkpoint '{c_id}' failed checksum self-verification.")

        self._repository.save_checkpoint(checkpoint)

        w_id = str(workflow_id)
        self._publisher.publish(
            CheckpointCreated(
                aggregate_id=w_id,
                workflow_id=w_id,
                checkpoint_id=c_id,
                step_name=step_name,
                checksum=str(checkpoint.checksum),
            )
        )

        return checkpoint

    def get_latest_valid_checkpoint(self, workflow_id: WorkflowId) -> Optional[WorkflowCheckpoint]:
        """Retrieves and verifies the latest checkpoint for a workflow."""
        cp = self._repository.get_latest_checkpoint(workflow_id)
        if cp is not None:
            if not cp.verify_checksum():
                raise CheckpointError(f"Checkpoint '{cp.checkpoint_id}' checksum verification failed upon retrieval.")
        return cp
