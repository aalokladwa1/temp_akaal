"""akaalEngine.intelligence.models.request
===========================================
IntelligenceRequest / IntelligenceTask -- the typed inbound contract for the P7C.1
Intelligence Kernel. A request is never itself authority: it is validated, routed to
a registered producer, and only ever yields an IntelligenceArtifact that downstream
canonical authorities may choose to act on.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


class IntelligenceTask(str, enum.Enum):
    """Typed task taxonomy (P7C brief §P7C.1). Extensible -- later P7C sub-phases
    register producers against these values rather than inventing new dispatch
    mechanisms; adding a new task value here does not itself grant any capability."""

    ASSESS = "ASSESS"
    EXPLAIN = "EXPLAIN"
    RECOMMEND = "RECOMMEND"
    GENERATE = "GENERATE"
    OPTIMIZE = "OPTIMIZE"
    FORECAST = "FORECAST"
    CONVERT = "CONVERT"
    COMPARE = "COMPARE"
    QUERY = "QUERY"
    SIMULATE = "SIMULATE"


@dataclass(frozen=True)
class IntelligenceRequest:
    """Immutable inbound request to the Intelligence Kernel.

    `subject_type`/`subject_id`/`subject_version` bind the request to a concrete
    canonical AKAAL entity (e.g. subject_type="migration_plan", subject_id=plan_id,
    subject_version=plan_revision) so the resulting artifact's fingerprint can later
    be compared against current canonical state to detect staleness.
    """

    task: IntelligenceTask
    tenant_id: str
    subject_type: str
    subject_id: str
    subject_version: str
    requested_by: str
    request_id: str = field(default_factory=lambda: f"intel-req-{uuid.uuid4().hex}")
    capability: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    algorithm_version: str = "p7c1-kernel-v1"
    policy_version: str = "p7c1-policy-v1"
    timeout_seconds: float = 30.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.tenant_id or not str(self.tenant_id).strip():
            raise ValueError("IntelligenceRequest.tenant_id cannot be empty")
        if not self.subject_type or not str(self.subject_type).strip():
            raise ValueError("IntelligenceRequest.subject_type cannot be empty")
        if not self.subject_id or not str(self.subject_id).strip():
            raise ValueError("IntelligenceRequest.subject_id cannot be empty")
        if not self.requested_by or not str(self.requested_by).strip():
            raise ValueError("IntelligenceRequest.requested_by cannot be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("IntelligenceRequest.timeout_seconds must be positive")
        object.__setattr__(self, "parameters", dict(self.parameters))

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "task": self.task.value,
            "capability": self.capability,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "subject_version": self.subject_version,
            "requested_by": self.requested_by,
            "parameters": dict(self.parameters),
            "algorithm_version": self.algorithm_version,
            "policy_version": self.policy_version,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at,
        }
