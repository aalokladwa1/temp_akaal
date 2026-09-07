"""akaalEngine.intelligence.models.context
===========================================
IntelligenceContext -- the canonical-state binding dimensions used for artifact
fingerprinting and staleness detection (P7C brief §P7C.1 "Context fingerprint").

This does NOT redefine tenant identity. It carries the same tenant/workspace/project
dimensions already canonical in akaalPipeline.security.context.PipelineActorContext,
plus the additional dimensions (subject version, canonical-state fingerprint, policy
and algorithm versions) that determine whether a previously generated artifact is
still valid against *current* state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class IntelligenceContext:
    tenant_id: str
    subject_type: str
    subject_id: str
    subject_version: str
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    canonical_state_fingerprint: Optional[str] = None
    policy_version: str = "p7c1-policy-v1"
    algorithm_version: str = "p7c1-kernel-v1"
    extra_dimensions: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tenant_id or not str(self.tenant_id).strip():
            raise ValueError("IntelligenceContext.tenant_id cannot be empty")
        if not self.subject_type or not str(self.subject_type).strip():
            raise ValueError("IntelligenceContext.subject_type cannot be empty")
        if not self.subject_id or not str(self.subject_id).strip():
            raise ValueError("IntelligenceContext.subject_id cannot be empty")
        object.__setattr__(self, "extra_dimensions", dict(self.extra_dimensions))

    @classmethod
    def from_actor(
        cls,
        actor: Any,
        *,
        subject_type: str,
        subject_id: str,
        subject_version: str,
        canonical_state_fingerprint: Optional[str] = None,
        policy_version: str = "p7c1-policy-v1",
        algorithm_version: str = "p7c1-kernel-v1",
        extra_dimensions: Optional[Mapping[str, str]] = None,
    ) -> "IntelligenceContext":
        """Builds a context bound to an authenticated PipelineActorContext's tenant
        dimensions. `actor` is duck-typed (must expose .organization_id/.tenant_id,
        .workspace_id, .project_id) so this stays decoupled from a hard import cycle
        with akaalPipeline; callers pass the real PipelineActorContext in production."""
        tenant_id = getattr(actor, "tenant_id", None) or getattr(actor, "organization_id", None)
        if not tenant_id:
            raise ValueError("IntelligenceContext.from_actor requires a resolvable tenant_id on actor")
        return cls(
            tenant_id=tenant_id,
            workspace_id=getattr(actor, "workspace_id", None),
            project_id=getattr(actor, "project_id", None),
            subject_type=subject_type,
            subject_id=subject_id,
            subject_version=subject_version,
            canonical_state_fingerprint=canonical_state_fingerprint,
            policy_version=policy_version,
            algorithm_version=algorithm_version,
            extra_dimensions=extra_dimensions or {},
        )

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "subject_version": self.subject_version,
            "canonical_state_fingerprint": self.canonical_state_fingerprint,
            "policy_version": self.policy_version,
            "algorithm_version": self.algorithm_version,
            "extra_dimensions": dict(self.extra_dimensions),
        }
