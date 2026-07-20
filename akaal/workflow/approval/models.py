"""Enterprise Approval Domain Models & Data Transfer Objects."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Sequence
from akaal.workflow.utils.serialization import compute_sha256


class ApprovalStatus(str, Enum):
    """Approval request and token status enum."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    DELEGATED = "DELEGATED"
    CANCELLED = "CANCELLED"


class PrincipalType(str, Enum):
    """Approval principal identity type."""
    USER = "USER"
    ROLE = "ROLE"
    GROUP = "GROUP"


@dataclass(frozen=True, slots=True)
class ApprovalPrincipal:
    """Typed approval principal representing a user, role, or group."""
    principal_id: str
    principal_type: PrincipalType
    display_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "principal_type": self.principal_type.value,
            "display_name": self.display_name,
        }


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """Approval request specification for an ordered approval gate."""
    request_id: str
    workflow_id: str
    gate_number: int  # 1: Plan Readiness, 2: Migration Progression, 3: Final Cutover
    gate_name: str
    assigned_principal: ApprovalPrincipal
    timeout_seconds: float = 3600.0
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: str = "2026-01-01T00:00:00+00:00"
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "request_id": self.request_id,
            "workflow_id": self.workflow_id,
            "gate_number": self.gate_number,
            "gate_name": self.gate_name,
            "assigned_principal": self.assigned_principal.to_dict(),
            "timeout_seconds": self.timeout_seconds,
            "status": self.status.value,
            "requested_at": self.requested_at,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "workflow_id": self.workflow_id,
            "gate_number": self.gate_number,
            "gate_name": self.gate_name,
            "assigned_principal": self.assigned_principal.to_dict(),
            "timeout_seconds": self.timeout_seconds,
            "status": self.status.value,
            "requested_at": self.requested_at,
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class ApprovalDecision:
    """Decision made by a principal on an approval request."""
    decision_id: str
    request_id: str
    acting_principal: ApprovalPrincipal
    status: ApprovalStatus  # APPROVED or REJECTED
    reason: str = ""
    decided_at: str = "2026-01-01T00:00:00+00:00"
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "acting_principal": self.acting_principal.to_dict(),
            "status": self.status.value,
            "reason": self.reason,
            "decided_at": self.decided_at,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "acting_principal": self.acting_principal.to_dict(),
            "status": self.status.value,
            "reason": self.reason,
            "decided_at": self.decided_at,
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class ApprovalDelegation:
    """Record of approval authority delegation."""
    delegation_id: str
    request_id: str
    from_principal: ApprovalPrincipal
    to_principal: ApprovalPrincipal
    delegated_by: str
    reason: str
    delegated_at: str = "2026-01-01T00:00:00+00:00"
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "delegation_id": self.delegation_id,
            "request_id": self.request_id,
            "from_principal": self.from_principal.to_dict(),
            "to_principal": self.to_principal.to_dict(),
            "delegated_by": self.delegated_by,
            "reason": self.reason,
            "delegated_at": self.delegated_at,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "delegation_id": self.delegation_id,
            "request_id": self.request_id,
            "from_principal": self.from_principal.to_dict(),
            "to_principal": self.to_principal.to_dict(),
            "delegated_by": self.delegated_by,
            "reason": self.reason,
            "delegated_at": self.delegated_at,
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class ApprovalToken:
    """Immutable cryptographically verified token generated upon approval decision."""
    token_id: str
    request_id: str
    workflow_id: str
    gate_number: int
    approved_by: ApprovalPrincipal
    status: ApprovalStatus
    decided_at: str = "2026-01-01T00:00:00+00:00"
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "token_id": self.token_id,
            "request_id": self.request_id,
            "workflow_id": self.workflow_id,
            "gate_number": self.gate_number,
            "approved_by": self.approved_by.to_dict(),
            "status": self.status.value,
            "decided_at": self.decided_at,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "request_id": self.request_id,
            "workflow_id": self.workflow_id,
            "gate_number": self.gate_number,
            "approved_by": self.approved_by.to_dict(),
            "status": self.status.value,
            "decided_at": self.decided_at,
            "checksum": self.checksum,
        }
