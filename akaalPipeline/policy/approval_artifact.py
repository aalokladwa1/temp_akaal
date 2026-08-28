"""akaalPipeline.policy.approval_artifact
======================================
Canonical 17-dimension cryptographic governance approval artifact.
Binds execution intent, plan revision, identities, approvers, and security state into a tamper-evident record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.serialization import (
    AKAAL_CANONICAL_PROFILE_V1,
    canonical_fingerprint,
    canonical_serialize_bytes,
)


class ApprovalIntegrityError(ValueError):
    """Raised when an approval artifact is invalid, tampered, or violates governance invariants."""
    pass


@dataclass(frozen=True)
class GovernanceApprovalArtifact:
    """Immutable 17-dimension cryptographic governance approval record."""

    approval_id: str
    tenant_id: str
    workspace_id: str
    project_id: str
    migration_id: str
    plan_id: str
    plan_revision: int
    execution_mode: str
    requester_id: str
    approvers: List[str]
    source_identity_fingerprint: str
    target_identity_fingerprint: str
    config_fingerprint: str
    selection_fingerprint: str
    init_fingerprint: str
    security_revision: int
    key_id: str
    status: str = "APPROVED"
    expires_at: Optional[str] = None
    issued_at: Optional[str] = None

    def compute_fingerprint(self) -> str:
        """Compute deterministic canonical SHA-256 fingerprint."""
        payload = {
            "canonicalization_profile": AKAAL_CANONICAL_PROFILE_V1,
            "approval_id": self.approval_id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "plan_id": self.plan_id,
            "plan_revision": self.plan_revision,
            "execution_mode": self.execution_mode,
            "requester_id": self.requester_id,
            "approvers": sorted(self.approvers),
            "source_identity_fingerprint": self.source_identity_fingerprint,
            "target_identity_fingerprint": self.target_identity_fingerprint,
            "config_fingerprint": self.config_fingerprint,
            "selection_fingerprint": self.selection_fingerprint,
            "init_fingerprint": self.init_fingerprint,
            "security_revision": self.security_revision,
            "key_id": self.key_id,
            "status": self.status,
            "expires_at": self.expires_at,
        }
        return canonical_fingerprint(payload)

    def validate_invariants(self, allow_self_approval: bool = False) -> None:
        """Enforce strict governance invariants."""
        if not self.tenant_id or not self.migration_id or not self.plan_id:
            raise ApprovalIntegrityError("Approval artifact missing mandatory identity fields")

        if not self.approvers:
            raise ApprovalIntegrityError("Approval artifact must have at least one valid approver")

        # Maker-Checker / SoD validation
        if not allow_self_approval and self.requester_id in self.approvers:
            raise ApprovalIntegrityError(
                f"Self-approval prohibited: requester {self.requester_id!r} cannot be in approvers list"
            )

        # Duplicate approver validation
        if len(self.approvers) != len(set(self.approvers)):
            raise ApprovalIntegrityError("Duplicate approvers in approval artifact are prohibited")

        # Expiration validation
        if self.expires_at and TimeAuthority.is_expired(self.expires_at):
            raise ApprovalIntegrityError(f"Approval artifact expired at {self.expires_at}")

        if self.status != "APPROVED":
            raise ApprovalIntegrityError(f"Approval artifact status is {self.status!r}, expected 'APPROVED'")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "plan_id": self.plan_id,
            "plan_revision": self.plan_revision,
            "execution_mode": self.execution_mode,
            "requester_id": self.requester_id,
            "approvers": self.approvers,
            "source_identity_fingerprint": self.source_identity_fingerprint,
            "target_identity_fingerprint": self.target_identity_fingerprint,
            "config_fingerprint": self.config_fingerprint,
            "selection_fingerprint": self.selection_fingerprint,
            "init_fingerprint": self.init_fingerprint,
            "security_revision": self.security_revision,
            "key_id": self.key_id,
            "status": self.status,
            "expires_at": self.expires_at,
            "issued_at": self.issued_at,
            "approval_fingerprint": self.compute_fingerprint(),
        }
