"""
Enterprise MigrationJob Domain Model.
The MigrationJob represents the business domain object while the Workflow represents execution.
These responsibilities remain strictly separated.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import json

from akaal.orchestration.domain.identifiers import (
    JobId,
    WorkflowId,
    SessionId,
    ConfigurationId,
)
from akaal.orchestration.domain.types import (
    EngineState,
    WorkflowStepName,
    Version,
    Checksum,
    AuditMetadata,
)


@dataclass(frozen=True)
class MigrationJob:
    """
    Immutable MigrationJob domain model.
    Represents the business identity, profiles, state, progress, and audit metadata of a job.
    """
    job_id: JobId
    workflow_id: WorkflowId
    session_id: SessionId
    config_id: ConfigurationId
    source_profile: Dict[str, Any]
    target_profile: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    progress: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    audit_metadata: AuditMetadata = field(default_factory=AuditMetadata)
    current_state: EngineState = EngineState.CREATED
    current_step: str = WorkflowStepName.ANALYSIS.value
    version: Version = field(default_factory=Version)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checksum: Checksum = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "checksum", self.compute_checksum())

    def compute_checksum(self) -> Checksum:
        """
        Computes SHA-256 checksum over immutable job core fields.
        Ensures job integrity cannot be tampered with.
        """
        payload = {
            "job_id": str(self.job_id),
            "workflow_id": str(self.workflow_id),
            "session_id": str(self.session_id),
            "config_id": str(self.config_id),
            "source_profile": self.source_profile,
            "target_profile": self.target_profile,
            "metadata": self.metadata,
            "current_state": self.current_state.value,
            "current_step": self.current_step,
            "version": int(self.version),
            "created_at": self.created_at,
        }
        return Checksum.from_dict(payload)

    def with_updates(
        self,
        current_state: Optional[EngineState] = None,
        current_step: Optional[str] = None,
        progress: Optional[Dict[str, Any]] = None,
        statistics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[SessionId] = None,
        updated_by: Optional[str] = None,
    ) -> "MigrationJob":
        """
        Returns a new immutable MigrationJob instance with updated values,
        incremented version, new updated timestamp, and recalculated integrity checksum.
        """
        new_state = current_state if current_state is not None else self.current_state
        new_step = current_step if current_step is not None else self.current_step
        new_progress = progress if progress is not None else dict(self.progress)
        new_stats = statistics if statistics is not None else dict(self.statistics)
        new_meta = metadata if metadata is not None else dict(self.metadata)
        new_session = session_id if session_id is not None else self.session_id
        
        new_audit = self.audit_metadata
        if updated_by:
            new_audit = AuditMetadata(
                created_by=self.audit_metadata.created_by,
                updated_by=updated_by,
                tenant_id=self.audit_metadata.tenant_id,
                correlation_id=self.audit_metadata.correlation_id,
                extra=self.audit_metadata.extra,
            )

        new_instance = replace(
            self,
            session_id=new_session,
            current_state=new_state,
            current_step=new_step,
            progress=new_progress,
            statistics=new_stats,
            metadata=new_meta,
            audit_metadata=new_audit,
            version=self.version.increment(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        return new_instance

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to a serializable dictionary."""
        return {
            "job_id": str(self.job_id),
            "workflow_id": str(self.workflow_id),
            "session_id": str(self.session_id),
            "config_id": str(self.config_id),
            "source_profile": self.source_profile,
            "target_profile": self.target_profile,
            "metadata": self.metadata,
            "progress": self.progress,
            "statistics": self.statistics,
            "audit_metadata": {
                "created_by": self.audit_metadata.created_by,
                "updated_by": self.audit_metadata.updated_by,
                "tenant_id": self.audit_metadata.tenant_id,
                "correlation_id": self.audit_metadata.correlation_id,
                "extra": self.audit_metadata.extra,
            },
            "current_state": self.current_state.value,
            "current_step": self.current_step,
            "version": int(self.version),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "checksum": str(self.checksum),
        }
