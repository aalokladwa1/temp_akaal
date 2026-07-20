"""
Enterprise Workflow Session Domain Model.
Designed for distributed multi-node execution readiness with heartbeats,
leases, locks, secure resume tokens, and crash detection.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
import hashlib
import hmac
import uuid

from akaal.orchestration.domain.identifiers import SessionId, WorkflowId, JobId
from akaal.orchestration.domain.errors import SessionExpiredError


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"
    CRASHED = "CRASHED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class WorkflowSession:
    """
    Immutable WorkflowSession model.
    Encapsulates session state, ownership, lease timeouts, heartbeats, and resume token generation.
    """
    session_id: SessionId
    workflow_id: WorkflowId
    job_id: JobId
    owner_node_id: str
    owner_worker_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    lease_timeout_seconds: float = 30.0
    heartbeat_interval_seconds: float = 5.0
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    last_heartbeat: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    resume_token: str = field(init=False)
    secret_key: str = field(default_factory=lambda: uuid.uuid4().hex, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "resume_token", self._generate_resume_token())

    def _generate_resume_token(self) -> str:
        """Generates a cryptographically derived resume token for session recovery verification."""
        message = f"{self.session_id}:{self.workflow_id}:{self.job_id}:{self.owner_node_id}:{self.created_at}"
        return hmac.new(self.secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_resume_token(self, token: str) -> bool:
        """Verifies if a provided resume token matches the session token."""
        return hmac.compare_digest(self.resume_token, token)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Checks if session lease has expired based on last heartbeat timestamp."""
        now = current_time if current_time is not None else datetime.now(timezone.utc).timestamp()
        return (now - self.last_heartbeat) > self.lease_timeout_seconds

    def with_heartbeat(self, current_time: Optional[float] = None) -> "WorkflowSession":
        """Returns updated session copy with refreshed heartbeat timestamp."""
        if self.status != SessionStatus.ACTIVE:
            raise SessionExpiredError(f"Cannot update heartbeat for session in state {self.status.value}")
        now = current_time if current_time is not None else datetime.now(timezone.utc).timestamp()
        return replace(self, last_heartbeat=now)

    def with_status(self, new_status: SessionStatus) -> "WorkflowSession":
        """Returns updated session copy with new status."""
        return replace(self, status=new_status)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": str(self.session_id),
            "workflow_id": str(self.workflow_id),
            "job_id": str(self.job_id),
            "owner_node_id": self.owner_node_id,
            "owner_worker_id": self.owner_worker_id,
            "status": self.status.value,
            "lease_timeout_seconds": self.lease_timeout_seconds,
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            "created_at": self.created_at,
            "last_heartbeat": self.last_heartbeat,
            "resume_token": self.resume_token,
        }
