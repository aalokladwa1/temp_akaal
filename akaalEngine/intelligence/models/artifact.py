"""akaalEngine.intelligence.models.artifact
============================================
IntelligenceArtifact -- the durable, identity-bound record produced by the P7C.1
Intelligence Kernel (P7C brief "Intelligence Artifact Identity").
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from akaalEngine.intelligence.models.lifecycle import ArtifactLifecycleState
from akaalEngine.intelligence.models.request import IntelligenceTask


@dataclass(frozen=True)
class IntelligenceArtifact:
    artifact_id: str
    tenant_id: str
    subject_type: str
    subject_id: str
    subject_version: str
    task: IntelligenceTask
    algorithm_version: str
    policy_version: str
    canonical_state_fingerprint: str
    fingerprint: str
    result: Mapping[str, Any]
    lifecycle_state: ArtifactLifecycleState
    created_at: str
    requested_by: str
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    model_provider: Optional[str] = None
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    expires_at: Optional[str] = None
    superseded_by: Optional[str] = None
    updated_at: Optional[str] = None

    @staticmethod
    def new_id() -> str:
        return f"intel-art-{uuid.uuid4().hex}"

    def with_state(self, new_state: ArtifactLifecycleState, *, superseded_by: Optional[str] = None) -> "IntelligenceArtifact":
        import dataclasses as _dc

        return _dc.replace(
            self,
            lifecycle_state=new_state,
            superseded_by=superseded_by if superseded_by is not None else self.superseded_by,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "subject_version": self.subject_version,
            "task": self.task.value,
            "algorithm_version": self.algorithm_version,
            "policy_version": self.policy_version,
            "canonical_state_fingerprint": self.canonical_state_fingerprint,
            "fingerprint": self.fingerprint,
            "result": dict(self.result),
            "lifecycle_state": self.lifecycle_state.value,
            "created_at": self.created_at,
            "requested_by": self.requested_by,
            "model_provider": self.model_provider,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "expires_at": self.expires_at,
            "superseded_by": self.superseded_by,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IntelligenceArtifact":
        return cls(
            artifact_id=data["artifact_id"],
            tenant_id=data["tenant_id"],
            workspace_id=data.get("workspace_id"),
            project_id=data.get("project_id"),
            subject_type=data["subject_type"],
            subject_id=data["subject_id"],
            subject_version=data["subject_version"],
            task=IntelligenceTask(data["task"]),
            algorithm_version=data["algorithm_version"],
            policy_version=data["policy_version"],
            canonical_state_fingerprint=data["canonical_state_fingerprint"],
            fingerprint=data["fingerprint"],
            result=dict(data.get("result") or {}),
            lifecycle_state=ArtifactLifecycleState(data["lifecycle_state"]),
            created_at=data["created_at"],
            requested_by=data["requested_by"],
            model_provider=data.get("model_provider"),
            model_id=data.get("model_id"),
            model_version=data.get("model_version"),
            expires_at=data.get("expires_at"),
            superseded_by=data.get("superseded_by"),
            updated_at=data.get("updated_at"),
        )
