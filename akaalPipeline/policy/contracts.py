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
    effective_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    evidence_fingerprint: Optional[str] = None

    def is_expired(self, current_time_iso: Optional[str] = None) -> bool:
        if not self.expires_at:
            return False
        now = current_time_iso or datetime.now(timezone.utc).isoformat()
        return now > self.expires_at
