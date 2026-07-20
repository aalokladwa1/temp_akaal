"""
Thread-safe In-Memory Repository implementations for testing and replay.
"""

from threading import RLock
from typing import Optional, List, Dict, Any

from akaal.orchestration.domain.identifiers import JobId, WorkflowId, SessionId
from akaal.orchestration.domain.types import EngineState
from akaal.orchestration.domain.errors import RepositoryError
from akaal.orchestration.models.job import MigrationJob
from akaal.orchestration.session.session import WorkflowSession
from akaal.orchestration.audit.audit_logger import AuditRecord
from akaal.orchestration.repository.interfaces import (
    WorkflowRepository,
    SessionRepository,
    CheckpointRepository,
    AuditRepository,
)


class InMemoryWorkflowRepository(WorkflowRepository):

    def __init__(self) -> None:
        self._lock = RLock()
        self._jobs: Dict[str, MigrationJob] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._variables: Dict[str, Dict[str, Any]] = {}
        self._pending_approvals: Dict[str, List[Dict[str, Any]]] = {}

    def save_job(self, job: MigrationJob) -> None:
        with self._lock:
            key = str(job.job_id)
            if key in self._jobs:
                raise RepositoryError(f"Job {key} already exists.")
            self._jobs[key] = job

    def get_job(self, job_id: JobId) -> Optional[MigrationJob]:
        with self._lock:
            return self._jobs.get(str(job_id))

    def update_job(self, job: MigrationJob) -> None:
        with self._lock:
            key = str(job.job_id)
            if key not in self._jobs:
                raise RepositoryError(f"Job {key} does not exist.")
            self._jobs[key] = job

    def delete_job(self, job_id: JobId) -> None:
        with self._lock:
            key = str(job_id)
            if key in self._jobs:
                del self._jobs[key]

    def query_jobs(self, state: Optional[EngineState] = None) -> List[MigrationJob]:
        with self._lock:
            if state is None:
                return list(self._jobs.values())
            return [j for j in self._jobs.values() if j.current_state == state]

    def save_execution_history(self, workflow_id: WorkflowId, record: Dict[str, Any]) -> None:
        with self._lock:
            w_id = str(workflow_id)
            if w_id not in self._history:
                self._history[w_id] = []
            self._history[w_id].append(dict(record))

    def get_execution_history(self, workflow_id: WorkflowId) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history.get(str(workflow_id), []))

    def save_execution_variable(self, workflow_id: WorkflowId, key: str, value: Any) -> None:
        with self._lock:
            w_id = str(workflow_id)
            if w_id not in self._variables:
                self._variables[w_id] = {}
            self._variables[w_id][key] = value

    def get_execution_variable(self, workflow_id: WorkflowId, key: str) -> Any:
        with self._lock:
            return self._variables.get(str(workflow_id), {}).get(key)

    def save_pending_approval(self, workflow_id: WorkflowId, approval_info: Dict[str, Any]) -> None:
        with self._lock:
            w_id = str(workflow_id)
            if w_id not in self._pending_approvals:
                self._pending_approvals[w_id] = []
            self._pending_approvals[w_id].append(dict(approval_info))

    def get_pending_approvals(self, workflow_id: WorkflowId) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._pending_approvals.get(str(workflow_id), []))

    def remove_pending_approval(self, workflow_id: WorkflowId, approval_id: str) -> None:
        with self._lock:
            w_id = str(workflow_id)
            if w_id in self._pending_approvals:
                self._pending_approvals[w_id] = [
                    a for a in self._pending_approvals[w_id] if a.get("approval_id") != approval_id
                ]


class InMemorySessionRepository(SessionRepository):

    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: Dict[str, WorkflowSession] = {}

    def save_session(self, session: WorkflowSession) -> None:
        with self._lock:
            s_id = str(session.session_id)
            if s_id in self._sessions:
                raise RepositoryError(f"Session {s_id} already exists.")
            self._sessions[s_id] = session

    def get_session(self, session_id: SessionId) -> Optional[WorkflowSession]:
        with self._lock:
            return self._sessions.get(str(session_id))

    def update_session(self, session: WorkflowSession) -> None:
        with self._lock:
            s_id = str(session.session_id)
            if s_id not in self._sessions:
                raise RepositoryError(f"Session {s_id} does not exist.")
            self._sessions[s_id] = session

    def delete_session(self, session_id: SessionId) -> None:
        with self._lock:
            s_id = str(session_id)
            if s_id in self._sessions:
                del self._sessions[s_id]


class InMemoryCheckpointRepository(CheckpointRepository):

    def __init__(self) -> None:
        self._lock = RLock()
        self._checkpoints: Dict[str, Any] = {}
        self._by_workflow: Dict[str, List[Any]] = {}

    def save_checkpoint(self, checkpoint: Any) -> None:
        with self._lock:
            c_id = checkpoint.checkpoint_id
            w_id = str(checkpoint.workflow_id)
            self._checkpoints[c_id] = checkpoint
            if w_id not in self._by_workflow:
                self._by_workflow[w_id] = []
            self._by_workflow[w_id].append(checkpoint)

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Any]:
        with self._lock:
            return self._checkpoints.get(checkpoint_id)

    def get_latest_checkpoint(self, workflow_id: WorkflowId) -> Optional[Any]:
        with self._lock:
            w_id = str(workflow_id)
            cps = self._by_workflow.get(w_id, [])
            return cps[-1] if cps else None

    def list_checkpoints(self, workflow_id: WorkflowId) -> List[Any]:
        with self._lock:
            return list(self._by_workflow.get(str(workflow_id), []))


class InMemoryAuditRepository(AuditRepository):

    def __init__(self) -> None:
        self._lock = RLock()
        self._records: List[AuditRecord] = []

    def save_audit_record(self, record: AuditRecord) -> None:
        with self._lock:
            self._records.append(record)

    def query_audit_records(self, aggregate_id: Optional[str] = None) -> List[AuditRecord]:
        with self._lock:
            if aggregate_id is None:
                return list(self._records)
            return [r for r in self._records if r.aggregate_id == aggregate_id]
