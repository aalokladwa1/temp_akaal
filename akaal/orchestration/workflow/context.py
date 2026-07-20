"""
WorkflowContext parameter object for Enterprise Workflow Steps.
Bundles runtime dependencies into a single immutable context object to prevent primitive obsession
and wide function signatures.
"""

from dataclasses import dataclass, field, replace
import logging
from typing import Any, Dict, Optional

from akaal.orchestration.models.job import MigrationJob
from akaal.orchestration.session.session import WorkflowSession
from akaal.orchestration.config.config import FrozenConfiguration
from akaal.orchestration.repository.interfaces import (
    WorkflowRepository,
    SessionRepository,
    CheckpointRepository,
    AuditRepository,
)
from akaal.orchestration.events.events import EventPublisher


@dataclass
class CancellationToken:
    """Cancellation flag for cooperative step cancellation."""
    _cancelled: bool = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled


@dataclass(frozen=True)
class WorkflowContext:
    """
    Immutable WorkflowContext provided to every WorkflowStep execution method.
    Prevents unauthorized state mutation of context references.
    """
    job: MigrationJob
    session: WorkflowSession
    config: FrozenConfiguration
    workflow_repo: WorkflowRepository
    session_repo: SessionRepository
    checkpoint_repo: CheckpointRepository
    audit_repo: AuditRepository
    publisher: EventPublisher
    metrics: Any
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("nexusforge.orchestration"))
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)
    step_state: Dict[str, Any] = field(default_factory=dict)

    def with_job(self, new_job: MigrationJob) -> "WorkflowContext":
        """Returns a new immutable WorkflowContext instance with updated job reference."""
        return replace(self, job=new_job)

    def with_step_state(self, new_state: Dict[str, Any]) -> "WorkflowContext":
        """Returns a new immutable WorkflowContext instance with updated step execution state."""
        return replace(self, step_state=new_state)
