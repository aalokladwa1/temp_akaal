"""
akaalEngine.fabric.workload_identity.models
==============================================
P7B.3 -- Workload Identity & Cloud Authentication models.

CRITICAL LAW (repeated everywhere in this package because it is the single most
important P7B invariant): cloud authentication != AKAAL authorization. A
`CloudIdentityContext` proves only that some cloud IAM system has vouched for a
principal; it carries no AKAAL permission of any kind. See
`akaalEngine.fabric.workload_identity.boundary` for the only sanctioned path from a
`CloudIdentityContext` to an AKAAL authorization decision -- and note that path always
delegates the actual decision to a caller-supplied callback (in production, Pipeline's
`CentralAuthorizationEngine`), never decides on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping, Optional
from types import MappingProxyType


class CloudAuthProvider(str, Enum):
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"
    OCI = "OCI"


class WorkloadIdentityError(RuntimeError):
    """Base class for all workload-identity resolution errors."""


class WorkloadIdentityExpiredError(WorkloadIdentityError):
    """Raised when a cloud identity's credential/token has expired. Never silently extended."""


class WorkloadIdentityDependencyMissing(WorkloadIdentityError):
    """Raised when the cloud SDK required to resolve a workload identity is not installed."""


class WorkloadIdentityDeniedError(WorkloadIdentityError):
    """Raised when the cloud IAM system itself denies the identity/role-assumption request."""


class WorkloadIdentityUnavailableError(WorkloadIdentityError):
    """Raised when the cloud identity provider is unreachable."""


@dataclass(frozen=True)
class CloudIdentityContext:
    """
    Immutable record of a cloud-native authenticated identity. This object carries NO
    AKAAL permission -- it is purely a statement of "cloud IAM system X vouches for
    principal Y until time Z". Consuming code must never treat its mere existence, or
    even a non-expired state, as authorization to perform any AKAAL action.
    """
    provider: CloudAuthProvider
    principal_id: str
    account_boundary: str
    assumed_role: Optional[str] = None
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    raw_claims: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not self.principal_id or not self.principal_id.strip():
            raise WorkloadIdentityError("CloudIdentityContext.principal_id must be non-empty.")
        if not isinstance(self.raw_claims, MappingProxyType):
            object.__setattr__(self, "raw_claims", MappingProxyType(dict(self.raw_claims)))

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """
        Returns True only if an explicit expiry was recorded and has passed. If no expiry
        was recorded (some ambient-credential flows genuinely have none available to the
        caller), this truthfully returns False rather than fabricating an expiry -- callers
        that require a bounded-lifetime guarantee must check `expires_at is not None`
        themselves rather than relying solely on `is_expired()`.
        """
        if self.expires_at is None:
            return False
        current = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return current >= expiry

    def has_bounded_lifetime(self) -> bool:
        return self.expires_at is not None
