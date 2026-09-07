"""
akaalEngine.fabric.execution_site.models
===========================================
P7B.5 -- Execution Site Trust & Registration.

An Execution Site represents AKAAL execution capacity at a location. Kubernetes is one
possible implementation of an Execution Site, never a universal AKAAL runtime
requirement:

    Execution Site
    |-- Kubernetes
    |-- Cloud VM
    |-- On-prem VM
    |-- Bare metal
    `-- future certified execution runtime

Zero-trust site law (never re-derive, always import this ladder):
    SITE REGISTRATION != SITE TRUST != SITE AUTHORIZATION

A site cannot self-grant tenant access, migration assignment, provider access,
capabilities, trusted status, or authorization -- see
akaalEngine.fabric.execution_site.registry.SiteRegistry, which is the only place any of
these state transitions may happen, and which requires an externally-supplied
authorization callback (never an internal default-allow) for every trust/assignment
elevation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import FrozenSet, Mapping, Optional, Tuple
from types import MappingProxyType


class SiteKind(str, Enum):
    KUBERNETES = "KUBERNETES"
    CLOUD_VM = "CLOUD_VM"
    ON_PREM_VM = "ON_PREM_VM"
    BARE_METAL = "BARE_METAL"


class SiteTrustState(str, Enum):
    """Strictly ordered ladder: registration is step 1 of 4, never a shortcut to TRUSTED."""
    UNREGISTERED = "UNREGISTERED"
    REGISTERED = "REGISTERED"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    TRUSTED = "TRUSTED"
    REVOKED = "REVOKED"


_TRUST_RANK = {
    SiteTrustState.UNREGISTERED: 0,
    SiteTrustState.REGISTERED: 1,
    SiteTrustState.IDENTITY_VERIFIED: 2,
    SiteTrustState.TRUSTED: 3,
    SiteTrustState.REVOKED: -1,  # always below every other state -- revocation is absolute
}


def trust_rank(state: SiteTrustState) -> int:
    return _TRUST_RANK[state]


class SiteHealthState(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNREACHABLE = "UNREACHABLE"


class SiteLifecycleState(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    DECOMMISSIONED = "DECOMMISSIONED"


class ExecutionSiteValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ExecutionSite:
    """
    Immutable Execution Site record. `trust_state` here is a SNAPSHOT of what the
    SiteRegistry has established, not a self-declaration -- always construct new
    ExecutionSite instances for state transitions via SiteRegistry, never by hand-setting
    trust_state to a caller-preferred value.
    """
    site_id: str
    site_kind: SiteKind
    environment_id: str  # points at an akaalEngine.fabric.environment.Environment
    display_name: str = ""
    geography: Optional[str] = None
    region: Optional[str] = None
    availability_zone: Optional[str] = None
    network_membership: Tuple[str, ...] = field(default_factory=tuple)
    capabilities: FrozenSet[str] = field(default_factory=frozenset)
    worker_pool_refs: Tuple[str, ...] = field(default_factory=tuple)
    reachable_endpoint_refs: Tuple[str, ...] = field(default_factory=tuple)
    staging_capable: bool = False
    # security_identity is a CLAIM (e.g. a SPIFFE URI string) until IDENTITY_VERIFIED is
    # reached via SiteRegistry.verify_identity -- never treated as proven before that.
    claimed_security_identity: Optional[str] = None
    health_state: SiteHealthState = SiteHealthState.UNKNOWN
    trust_state: SiteTrustState = SiteTrustState.UNREGISTERED
    policy_labels: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    runtime_characteristics: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    lifecycle_state: SiteLifecycleState = SiteLifecycleState.PROVISIONAL
    tenant_binding: Optional[str] = None
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.site_id or not self.site_id.strip():
            raise ExecutionSiteValidationError("ExecutionSite.site_id must be non-empty.")
        if not self.environment_id or not self.environment_id.strip():
            raise ExecutionSiteValidationError("ExecutionSite.environment_id must be non-empty.")
        if not isinstance(self.network_membership, tuple):
            object.__setattr__(self, "network_membership", tuple(self.network_membership))
        if not isinstance(self.capabilities, frozenset):
            object.__setattr__(self, "capabilities", frozenset(self.capabilities))
        if not isinstance(self.worker_pool_refs, tuple):
            object.__setattr__(self, "worker_pool_refs", tuple(self.worker_pool_refs))
        if not isinstance(self.reachable_endpoint_refs, tuple):
            object.__setattr__(self, "reachable_endpoint_refs", tuple(self.reachable_endpoint_refs))
        if not isinstance(self.policy_labels, MappingProxyType):
            object.__setattr__(self, "policy_labels", MappingProxyType(dict(self.policy_labels)))
        if not isinstance(self.runtime_characteristics, MappingProxyType):
            object.__setattr__(self, "runtime_characteristics", MappingProxyType(dict(self.runtime_characteristics)))

    def is_execution_authorized(self) -> bool:
        """
        Purely informational readiness check (TRUSTED + tenant bound + not draining/
        decommissioned). This is NEVER itself an authorization grant -- actual assignment
        validation always goes through SiteRegistry.assign_execution which additionally
        requires an explicit authorization callback decision.
        """
        return (
            self.trust_state == SiteTrustState.TRUSTED
            and self.tenant_binding is not None
            and self.lifecycle_state == SiteLifecycleState.ACTIVE
        )


@dataclass(frozen=True)
class SiteAssignment:
    """A canonical binding of an ExecutionSite to one migration's execution, carrying the
    fencing epoch that stale/replayed assignments must never be able to satisfy."""
    site_id: str
    tenant_id: str
    workspace_id: str
    migration_id: str
    plan_id: str
    fencing_epoch: int
    assigned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.fencing_epoch < 1:
            raise ExecutionSiteValidationError("SiteAssignment.fencing_epoch must be >= 1.")
        for field_name in ("site_id", "tenant_id", "workspace_id", "migration_id", "plan_id"):
            if not getattr(self, field_name):
                raise ExecutionSiteValidationError(f"SiteAssignment.{field_name} must be non-empty.")
