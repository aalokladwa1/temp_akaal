"""
Storage-Agnostic Repository Interfaces for Enterprise Orchestration.
Follows Clean Architecture and Dependency Inversion. The WorkflowEngine interacts
only with repository interfaces.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from akaal.orchestration.domain.identifiers import JobId, WorkflowId, SessionId
from akaal.orchestration.domain.types import EngineState
from akaal.orchestration.models.job import MigrationJob
from akaal.orchestration.session.session import WorkflowSession
from akaal.orchestration.audit.audit_logger import AuditRecord


class WorkflowRepository(ABC):
    """Storage-agnostic repository for MigrationJob and workflow state persistence."""

    @abstractmethod
    def save_job(self, job: MigrationJob) -> None:
        pass

    @abstractmethod
    def get_job(self, job_id: JobId) -> Optional[MigrationJob]:
        pass

    @abstractmethod
    def update_job(self, job: MigrationJob) -> None:
        pass

    @abstractmethod
    def delete_job(self, job_id: JobId) -> None:
        pass

    @abstractmethod
    def query_jobs(self, state: Optional[EngineState] = None) -> List[MigrationJob]:
        pass

    @abstractmethod
    def save_execution_history(self, workflow_id: WorkflowId, record: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_execution_history(self, workflow_id: WorkflowId) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_execution_variable(self, workflow_id: WorkflowId, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def get_execution_variable(self, workflow_id: WorkflowId, key: str) -> Any:
        pass

    @abstractmethod
    def save_pending_approval(self, workflow_id: WorkflowId, approval_info: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_pending_approvals(self, workflow_id: WorkflowId) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def remove_pending_approval(self, workflow_id: WorkflowId, approval_id: str) -> None:
        pass


class SessionRepository(ABC):
    """Storage-agnostic repository for WorkflowSession tracking."""

    @abstractmethod
    def save_session(self, session: WorkflowSession) -> None:
        pass

    @abstractmethod
    def get_session(self, session_id: SessionId) -> Optional[WorkflowSession]:
        pass

    @abstractmethod
    def update_session(self, session: WorkflowSession) -> None:
        pass

    @abstractmethod
    def delete_session(self, session_id: SessionId) -> None:
        pass


class CheckpointRepository(ABC):
    """Storage-agnostic repository for WorkflowCheckpoint persistence."""

    @abstractmethod
    def save_checkpoint(self, checkpoint: Any) -> None:
        pass

    @abstractmethod
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    def get_latest_checkpoint(self, workflow_id: WorkflowId) -> Optional[Any]:
        pass

    @abstractmethod
    def list_checkpoints(self, workflow_id: WorkflowId) -> List[Any]:
        pass


class AuditRepository(ABC):
    """Storage-agnostic repository for AuditRecord persistence."""

    @abstractmethod
    def save_audit_record(self, record: AuditRecord) -> None:
        pass

    @abstractmethod
    def query_audit_records(self, aggregate_id: Optional[str] = None) -> List[AuditRecord]:
        pass
