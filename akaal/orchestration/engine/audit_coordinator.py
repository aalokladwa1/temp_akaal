"""
AuditCoordinator module.
Connects domain events to WorkflowAuditLogger and persists records to AuditRepository.
"""

from typing import List, Optional

from akaal.orchestration.events.events import InProcessEventDispatcher, DomainEvent
from akaal.orchestration.audit.audit_logger import WorkflowAuditLogger, AuditRecord
from akaal.orchestration.repository.interfaces import AuditRepository


class AuditCoordinator:
    """
    Coordinates audit recording by subscribing WorkflowAuditLogger to domain events.
    """

    def __init__(self, dispatcher: InProcessEventDispatcher, repository: AuditRepository) -> None:
        self._dispatcher = dispatcher
        self._repository = repository
        self._audit_logger = WorkflowAuditLogger()
        self._dispatcher.subscribe(self._audit_logger)

    def flush_audit_records(self) -> None:
        """Persist in-memory audit logger records to AuditRepository."""
        for record in self._audit_logger.get_records():
            self._repository.save_audit_record(record)

    def query_audit_trail(self, aggregate_id: Optional[str] = None) -> List[AuditRecord]:
        """Query audit records from repository."""
        return self._repository.query_audit_records(aggregate_id)
