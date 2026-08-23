"""
akaalEngine.connection.models.identity
======================================
Canonical physical endpoint identity, immutable binding fingerprints, and drift detection models.
Excludes secret material from all fingerprinting algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional

from akaalEngine.connection.models.endpoint import EndpointRole, RouteType
from akaalEngine.connection.security.redaction import SafeReprMixin


class DriftType(str, Enum):
    """Classification of detected drift between attested and live endpoint."""
    NONE = "NONE"
    IP_MUTATION = "IP_MUTATION"
    PORT_CHANGE = "PORT_CHANGE"
    SERVER_VERSION_CHANGE = "SERVER_VERSION_CHANGE"
    ROLE_TOPOLOGY_CHANGE = "ROLE_TOPOLOGY_CHANGE"
    PERMISSION_REVOCATION = "PERMISSION_REVOCATION"
    CAPABILITY_CHANGE = "CAPABILITY_CHANGE"
    CERTIFICATE_CHANGE = "CERTIFICATE_CHANGE"
    AUTHENTICATION_ROTATION = "AUTHENTICATION_ROTATION"
    DATABASE_CATALOG_CHANGE = "DATABASE_CATALOG_CHANGE"


class DriftSeverity(str, Enum):
    """Operational severity of detected drift."""
    INFO = "INFO"
    WARNING = "WARNING"
    INVALIDATING_ERROR = "INVALIDATING_ERROR"


@dataclass(frozen=True)
class EndpointBindingFingerprint(SafeReprMixin):
    """
    Deterministic cryptographic hash uniquely binding an execution-time endpoint configuration.
    Guaranteed secret-free.
    """
    fingerprint_sha256: str
    canonical_payload_json: str
    algorithm: str = "SHA-256"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __str__(self) -> str:
        return self.fingerprint_sha256


@dataclass(frozen=True)
class PhysicalEndpointIdentity(SafeReprMixin):
    """
    Attested physical facts captured from live connection handshake and system metadata.
    Does NOT contain secret material.
    """
    provider_id: str
    provider_version: str
    role: EndpointRole
    resolved_host: str
    resolved_ip: Optional[str] = None
    resolved_port: Optional[int] = None
    server_version: Optional[str] = None
    server_cluster_name: Optional[str] = None
    catalog_or_database: Optional[str] = None
    schema_name: Optional[str] = None
    principal_identity: Optional[str] = None
    cloud_resource_id: Optional[str] = None
    cloud_region: Optional[str] = None
    cloud_account_id: Optional[str] = None
    route_type: RouteType = RouteType.DIRECT
    tls_cipher: Optional[str] = None
    tls_peer_cert_sha256: Optional[str] = None
    capability_hash: Optional[str] = None
    permission_hash: Optional[str] = None
    topology_role: Optional[str] = None        # e.g., "PRIMARY", "REPLICA", "LEADER", "STANDALONE"
    topology_generation: int = 1
    attestation_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "role": self.role.value,
            "resolved_host": self.resolved_host,
            "resolved_ip": self.resolved_ip,
            "resolved_port": self.resolved_port,
            "server_version": self.server_version,
            "server_cluster_name": self.server_cluster_name,
            "catalog_or_database": self.catalog_or_database,
            "schema_name": self.schema_name,
            "principal_identity": self.principal_identity,
            "cloud_resource_id": self.cloud_resource_id,
            "cloud_region": self.cloud_region,
            "cloud_account_id": self.cloud_account_id,
            "route_type": self.route_type.value,
            "tls_cipher": self.tls_cipher,
            "tls_peer_cert_sha256": self.tls_peer_cert_sha256,
            "capability_hash": self.capability_hash,
            "permission_hash": self.permission_hash,
            "topology_role": self.topology_role,
            "topology_generation": self.topology_generation,
            "attestation_timestamp": self.attestation_timestamp,
        }


@dataclass(frozen=True)
class DriftReport(SafeReprMixin):
    """
    Result of comparing an attested endpoint identity against a live endpoint probe.
    """
    has_drift: bool
    drift_type: DriftType
    severity: DriftSeverity
    baseline_fingerprint: str
    current_fingerprint: str
    drifted_fields: Mapping[str, tuple[Any, Any]] = field(default_factory=dict)  # field -> (old_val, new_val)
    requires_pool_invalidation: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_drift": self.has_drift,
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "baseline_fingerprint": self.baseline_fingerprint,
            "current_fingerprint": self.current_fingerprint,
            "drifted_fields": {k: [str(v[0]), str(v[1])] for k, v in self.drifted_fields.items()},
            "requires_pool_invalidation": self.requires_pool_invalidation,
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }
