"""
WorkflowContext parameter object for Enterprise Workflow Steps.
Bundles runtime dependencies into a single context object to prevent primitive obsession
and wide function signatures.
"""

from dataclasses import dataclass, field
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


@dataclass
class WorkflowContext:
    """
    WorkflowContext provided to every WorkflowStep execution method.
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
