"""
akaalEngine.connection.models.capability
========================================
Canonical capability truth and proof level models.
Enforces strict fail-closed evaluation: UNKNOWN != SUPPORTED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.connection.models.endpoint import AuthenticationType, EndpointRole
from akaalEngine.connection.security.redaction import SafeReprMixin


class CapabilitySupportStatus(str, Enum):
    """Authoritative support status for an endpoint capability."""
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"
    PARTIAL = "PARTIAL"
    PROVIDER_DEFINED = "PROVIDER_DEFINED"


class ProofLevel(str, Enum):
    """
    Authoritative proof level of capability verification.
    Distinguishes static/code presence from automated unit proof, integration proof, and physical live proof.
    """
    IMPLEMENTED = "IMPLEMENTED"                 # Class exists & imports cleanly
    UNIT_PROVEN = "UNIT_PROVEN"                 # Verified against mocks / synthetic harnesses
    INTEGRATION_PROVEN = "INTEGRATION_PROVEN"   # Verified against emulator / local testcontainer
    LIVE_PROVEN = "LIVE_PROVEN"                 # Verified against real physical enterprise endpoint


@dataclass(frozen=True)
class CapabilityDescriptor(SafeReprMixin):
    """Specification of an Engine capability attribute."""
    capability_id: str
    name: str
    description: str
    category: str                               # e.g., "CORE", "SCHEMA", "TRANSACTION", "CDC", "STORAGE", "OPTIMIZATION"
    requires_role: Optional[EndpointRole] = None
    parameters_schema: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StaticCapabilityManifest(SafeReprMixin):
    """
    Authoritative static descriptor of provider capabilities and supported features.
    """
    provider_id: str
    provider_version: str
    family: str                                 # "relational", "warehouse", "nosql", "streaming", "storage", "cloud"
    vendor_name: str
    supported_roles: Sequence[EndpointRole] = field(default_factory=lambda: [EndpointRole.SOURCE, EndpointRole.TARGET])
    supported_auth: Sequence[AuthenticationType] = field(default_factory=lambda: [AuthenticationType.PASSWORD])
    supports_tls: bool = True
    supports_mtls: bool = False
    capabilities: Mapping[str, CapabilitySupportStatus] = field(default_factory=dict)
    proof_level: ProofLevel = ProofLevel.IMPLEMENTED
    restrictions: Sequence[str] = field(default_factory=list)
    required_privileges: Sequence[str] = field(default_factory=list)
    fastpath_features: Sequence[str] = field(default_factory=list)

    def is_capability_supported(self, capability_id: str) -> bool:
        """Fail-closed check: returns True ONLY if status is explicitly SUPPORTED."""
        status = self.capabilities.get(capability_id, CapabilitySupportStatus.UNKNOWN)
        return status == CapabilitySupportStatus.SUPPORTED

    def get_status(self, capability_id: str) -> CapabilitySupportStatus:
        """Returns the truthful support status."""
        return self.capabilities.get(capability_id, CapabilitySupportStatus.UNKNOWN)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "family": self.family,
            "vendor_name": self.vendor_name,
            "supported_roles": [r.value for r in self.supported_roles],
            "supported_auth": [a.value for a in self.supported_auth],
            "supports_tls": self.supports_tls,
            "supports_mtls": self.supports_mtls,
            "capabilities": {k: v.value for k, v in self.capabilities.items()},
            "proof_level": self.proof_level.value,
            "restrictions": list(self.restrictions),
            "required_privileges": list(self.required_privileges),
            "fastpath_features": list(self.fastpath_features),
        }


@dataclass(frozen=True)
class ProbedCapabilitySnapshot(SafeReprMixin):
    """
    Live result of probing an endpoint's active capabilities.
    """
    provider_id: str
    endpoint_fingerprint: str
    capabilities: Mapping[str, CapabilitySupportStatus]
    proof_level: ProofLevel
    evidence: Mapping[str, Any] = field(default_factory=dict)
    snapshot_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_supported(self, capability_id: str) -> bool:
        return self.capabilities.get(capability_id, CapabilitySupportStatus.UNKNOWN) == CapabilitySupportStatus.SUPPORTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "capabilities": {k: v.value for k, v in self.capabilities.items()},
            "proof_level": self.proof_level.value,
            "evidence": dict(self.evidence),
            "snapshot_timestamp": self.snapshot_timestamp,
        }


@dataclass(frozen=True)
class PermissionSnapshot(SafeReprMixin):
    """
    Live verified permissions and authorization facts for an authenticated endpoint session.
    """
    provider_id: str
    endpoint_fingerprint: str
    granted_privileges: Sequence[str]
    missing_privileges: Sequence[str]
    is_read_only: bool
    can_write: bool
    can_ddl: bool
    can_cdc: bool
    is_admin: bool
    evidence: Mapping[str, Any] = field(default_factory=dict)
    snapshot_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def has_privilege(self, privilege_name: str) -> bool:
        return privilege_name.upper() in [p.upper() for p in self.granted_privileges]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "granted_privileges": list(self.granted_privileges),
            "missing_privileges": list(self.missing_privileges),
            "is_read_only": self.is_read_only,
            "can_write": self.can_write,
            "can_ddl": self.can_ddl,
            "can_cdc": self.can_cdc,
            "is_admin": self.is_admin,
            "evidence": dict(self.evidence),
            "snapshot_timestamp": self.snapshot_timestamp,
        }
