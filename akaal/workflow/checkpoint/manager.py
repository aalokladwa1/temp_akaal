"""CheckpointManager orchestrating checkpoint persistence and recovery."""

from typing import Tuple
from akaal.workflow.checkpoint.storage import ICheckpointStorage, InMemoryCheckpointStorage
from akaal.workflow.models.checkpoint import WorkflowCheckpoint
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.utils.clock import IClock, SystemClock
from akaal.workflow.utils.id_generator import IIdGenerator, UUIDIdGenerator


class CheckpointManager:
    """Manager orchestrating state persistence, snapshot generation, and recovery."""

    def __init__(
        self,
        storage: ICheckpointStorage | None = None,
        clock: IClock | None = None,
        id_generator: IIdGenerator | None = None,
    ) -> None:
        self._storage = storage or InMemoryCheckpointStorage()
        self._clock = clock or SystemClock()
        self._id_generator = id_generator or UUIDIdGenerator()

    def create_checkpoint(
        self,
        context: WorkflowContext,
        step_id: str,
        state: str,
        completed_steps: Tuple[str, ...] = (),
        pending_steps: Tuple[str, ...] = (),
    ) -> WorkflowCheckpoint:
        """Create and persist a state snapshot checkpoint."""
        checkpoint_id = self._id_generator.generate_uuid()
        checkpoint = WorkflowCheckpoint(
            checkpoint_id=checkpoint_id,
            workflow_id=context.workflow_id,
            run_id=context.run_id,
            step_id=step_id,
            state=state,
            context=context,
            completed_steps=completed_steps,
            pending_steps=pending_steps,
            created_at=self._clock.now_utc(),
        )
        self._storage.save_checkpoint(checkpoint)
        return checkpoint

    def get_latest_checkpoint(self, workflow_id: str, run_id: str) -> WorkflowCheckpoint | None:
        """Load the most recent checkpoint for a workflow run."""
        return self._storage.load_latest_checkpoint(workflow_id, run_id)

    def get_checkpoint_by_id(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        """Load a specific checkpoint by ID."""
        return self._storage.load_checkpoint_by_id(checkpoint_id)

    def list_checkpoints(self, workflow_id: str) -> Tuple[WorkflowCheckpoint, ...]:
        """List all checkpoints for a workflow."""
        return self._storage.list_checkpoints(workflow_id)
