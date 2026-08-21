"""akaalPipeline.policy.contracts
================================
Policy & approval decision data models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class PolicyResult(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class PolicySubject:
    actor_id: str
    actor_type: str
    roles: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PolicyAction:
    name: str  # e.g. "migration.start", "migration.initialize", "mode.M1"


@dataclass(frozen=True)
class PolicyResource:
    resource_id: str
    resource_type: str  # e.g. "migration", "definition", "initialization"
    artifact_fingerprint: Optional[str] = None


@dataclass(frozen=True)
class PolicyDecision:
    decision_id: str
    policy_version: str
    subject: PolicySubject
    action: PolicyAction
    resource: PolicyResource
    result: PolicyResult
    reason: str
    issuer_id: Optional[str] = None
    issuer_roles: List[str] = field(default_factory=list)
    effective_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    evidence_fingerprint: Optional[str] = None

    def is_expired(self, current_time_iso: Optional[str] = None) -> bool:
        if not self.expires_at:
            return False
        now = current_time_iso or datetime.now(timezone.utc).isoformat()
        return now > self.expires_at

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "policy_version": self.policy_version,
            "subject": {"actor_id": self.subject.actor_id, "actor_type": self.subject.actor_type, "roles": list(self.subject.roles)},
            "action": {"name": self.action.name},
            "resource": {"resource_id": self.resource.resource_id, "resource_type": self.resource.resource_type, "artifact_fingerprint": self.resource.artifact_fingerprint},
            "result": self.result.value,
            "reason": self.reason,
            "issuer_id": self.issuer_id,
            "issuer_roles": list(self.issuer_roles),
            "effective_at": self.effective_at,
            "expires_at": self.expires_at,
            "evidence_fingerprint": self.evidence_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PolicyDecision:
        subj = data.get("subject", {})
        act = data.get("action", {})
        res = data.get("resource", {})
        return cls(
            decision_id=data["decision_id"],
            policy_version=data.get("policy_version", "1.0.0"),
            subject=PolicySubject(
                actor_id=subj.get("actor_id", "actor-default"),
                actor_type=subj.get("actor_type", "user"),
                roles=list(subj.get("roles", [])),
            ),
            action=PolicyAction(name=act.get("name", "action-default")),
            resource=PolicyResource(
                resource_id=res.get("resource_id", "res-default"),
                resource_type=res.get("resource_type", "migration"),
                artifact_fingerprint=res.get("artifact_fingerprint"),
            ),
            result=PolicyResult(data["result"]),
            reason=data.get("reason", ""),
            issuer_id=data.get("issuer_id"),
            issuer_roles=list(data.get("issuer_roles", [])),
            effective_at=data.get("effective_at", datetime.now(timezone.utc).isoformat()),
            expires_at=data.get("expires_at"),
            evidence_fingerprint=data.get("evidence_fingerprint"),
        )
