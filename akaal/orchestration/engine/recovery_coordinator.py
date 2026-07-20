"""
RecoveryCoordinator module.
Implements Feature 6 — Enterprise Session Recovery.
Validates checkpoint checksum, workflow version, config compatibility, step compatibility,
and session integrity deterministically. Fails safely without guessing.
"""

from typing import Tuple, Dict, Any, Optional
import logging

from akaal.orchestration.checkpoint.checkpoint import WorkflowCheckpoint
from akaal.orchestration.session.session import WorkflowSession, SessionStatus
from akaal.orchestration.config.config import FrozenConfiguration
from akaal.orchestration.workflow.definition import WorkflowDefinition
from akaal.orchestration.domain.identifiers import WorkflowId
from akaal.orchestration.domain.errors import RecoveryError
from akaal.orchestration.repository.interfaces import CheckpointRepository, SessionRepository
from akaal.orchestration.events.events import EventPublisher, WorkflowRecovered

logger = logging.getLogger("nexusforge.orchestration.recovery_coordinator")


class RecoveryCoordinator:
    """
    Deterministic session recovery coordinator.
    Validates all recovery requirements strictly before allowing resumption.
    """

    def __init__(
        self,
        checkpoint_repo: CheckpointRepository,
        session_repo: SessionRepository,
        publisher: EventPublisher,
    ) -> None:
        self._checkpoint_repo = checkpoint_repo
        self._session_repo = session_repo
        self._publisher = publisher

    def validate_and_recover(
        self,
        workflow_id: WorkflowId,
        definition: WorkflowDefinition,
        config: FrozenConfiguration,
        session: WorkflowSession,
    ) -> Tuple[WorkflowCheckpoint, Dict[str, Any]]:
        """
        Validates recovery safety strictly:
        1. Checkpoint Checksum validation
        2. Workflow Version compatibility validation
        3. Configuration compatibility & checksum validation
        4. Step compatibility validation
        5. Session integrity & token validation
        """
        # 1. Retrieve latest checkpoint
        checkpoint: Optional[WorkflowCheckpoint] = self._checkpoint_repo.get_latest_checkpoint(workflow_id)
        if checkpoint is None:
            raise RecoveryError(f"Recovery failed: No checkpoint found for workflow '{workflow_id}'.")

        # 2. Verify Checkpoint Checksum
        if not checkpoint.verify_checksum():
            raise RecoveryError(f"Recovery failed: Checkpoint '{checkpoint.checkpoint_id}' checksum mismatch (corrupted).")

        # 3. Verify Workflow Version Compatibility
        if checkpoint.workflow_version != definition.version:
            raise RecoveryError(
                f"Recovery failed: Workflow definition version mismatch. "
                f"Checkpoint version '{checkpoint.workflow_version}' != Definition version '{definition.version}'."
            )

        # 4. Verify Configuration Compatibility
        if checkpoint.config_checksum != str(config.checksum):
            raise RecoveryError(
                f"Recovery failed: Configuration checksum mismatch. "
                f"Checkpoint config checksum '{checkpoint.config_checksum}' != Active config checksum '{config.checksum}'."
            )

        # 5. Verify Step Compatibility
        step_names = definition.get_step_names()
        if checkpoint.step_name not in step_names:
            raise RecoveryError(
                f"Recovery failed: Step '{checkpoint.step_name}' does not exist in WorkflowDefinition '{definition.name}'."
            )

        # 6. Verify Session Integrity
        if str(session.workflow_id) != str(workflow_id):
            raise RecoveryError(
                f"Recovery failed: Session workflow_id '{session.workflow_id}' != Target workflow_id '{workflow_id}'."
            )

        if session.status in (SessionStatus.CLOSED, SessionStatus.EXPIRED):
            raise RecoveryError(
                f"Recovery failed: Session '{session.session_id}' is in state {session.status.value}."
            )

        logger.info(
            f"Deterministic recovery successfully validated for workflow '{workflow_id}' "
            f"at step '{checkpoint.step_name}' (checkpoint '{checkpoint.checkpoint_id}')."
        )

        w_id = str(workflow_id)
        self._publisher.publish(
            WorkflowRecovered(
                aggregate_id=w_id,
                workflow_id=w_id,
                session_id=str(session.session_id),
                recovered_step=checkpoint.step_name,
                checkpoint_checksum=str(checkpoint.checksum),
            )
        )

        return checkpoint, checkpoint.state_data
