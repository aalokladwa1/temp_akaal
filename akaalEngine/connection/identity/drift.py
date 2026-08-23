"""
akaalEngine.connection.identity.drift
=====================================
Physical identity drift detection engine.
Compares attested baseline identities against live endpoint facts and determines pool invalidation requirements.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

from akaalEngine.connection.models.identity import (
    DriftReport,
    DriftSeverity,
    DriftType,
    PhysicalEndpointIdentity,
)

logger = logging.getLogger("akaalEngine.connection.identity.drift")


class DriftDetector:
    """
    Detects material runtime differences between baseline attested endpoint identity and live observed facts.
    """

    @classmethod
    def compare_identities(
        cls,
        baseline: PhysicalEndpointIdentity,
        current: PhysicalEndpointIdentity,
        baseline_fingerprint: str = "",
        current_fingerprint: str = "",
    ) -> DriftReport:
        """
        Compares baseline and current physical identities and produces an authoritative DriftReport.
        """
        drifted: dict[str, tuple[Any, Any]] = {}
        primary_drift_type = DriftType.NONE
        severity = DriftSeverity.INFO
        requires_pool_invalidation = False

        # 1. Topology Role Change (e.g., Primary became Replica or Failover occurred)
        if baseline.topology_role and current.topology_role and baseline.topology_role != current.topology_role:
            drifted["topology_role"] = (baseline.topology_role, current.topology_role)
            primary_drift_type = DriftType.ROLE_TOPOLOGY_CHANGE
            severity = DriftSeverity.INVALIDATING_ERROR
            requires_pool_invalidation = True

        # 2. Server Version Change (e.g., Major upgrade during migration)
        if baseline.server_version and current.server_version and baseline.server_version != current.server_version:
            drifted["server_version"] = (baseline.server_version, current.server_version)
            if primary_drift_type == DriftType.NONE:
                primary_drift_type = DriftType.SERVER_VERSION_CHANGE
            severity = DriftSeverity.INVALIDATING_ERROR
            requires_pool_invalidation = True

        # 3. Database / Catalog Change
        if baseline.catalog_or_database != current.catalog_or_database:
            drifted["catalog_or_database"] = (baseline.catalog_or_database, current.catalog_or_database)
            if primary_drift_type == DriftType.NONE:
                primary_drift_type = DriftType.DATABASE_CATALOG_CHANGE
            severity = DriftSeverity.INVALIDATING_ERROR
            requires_pool_invalidation = True

        # 4. Peer Certificate Change (mTLS / TLS cert rotation)
        if (
            baseline.tls_peer_cert_sha256
            and current.tls_peer_cert_sha256
            and baseline.tls_peer_cert_sha256 != current.tls_peer_cert_sha256
        ):
            drifted["tls_peer_cert_sha256"] = (baseline.tls_peer_cert_sha256, current.tls_peer_cert_sha256)
            if primary_drift_type == DriftType.NONE:
                primary_drift_type = DriftType.CERTIFICATE_CHANGE
            severity = DriftSeverity.WARNING
            requires_pool_invalidation = True

        # 5. IP Address Mutation (DNS failover or multi-IP rotation)
        if baseline.resolved_ip and current.resolved_ip and baseline.resolved_ip != current.resolved_ip:
            drifted["resolved_ip"] = (baseline.resolved_ip, current.resolved_ip)
            if primary_drift_type == DriftType.NONE:
                primary_drift_type = DriftType.IP_MUTATION
            if severity != DriftSeverity.INVALIDATING_ERROR:
                severity = DriftSeverity.WARNING

        # 6. Capability Hash Change
        if baseline.capability_hash != current.capability_hash:
            drifted["capability_hash"] = (baseline.capability_hash, current.capability_hash)
            if primary_drift_type == DriftType.NONE:
                primary_drift_type = DriftType.CAPABILITY_CHANGE
            severity = DriftSeverity.INVALIDATING_ERROR
            requires_pool_invalidation = True

        # 7. Permission Hash Change
        if baseline.permission_hash != current.permission_hash:
            drifted["permission_hash"] = (baseline.permission_hash, current.permission_hash)
            if primary_drift_type == DriftType.NONE:
                primary_drift_type = DriftType.PERMISSION_REVOCATION
            severity = DriftSeverity.INVALIDATING_ERROR
            requires_pool_invalidation = True

        has_drift = len(drifted) > 0

        return DriftReport(
            has_drift=has_drift,
            drift_type=primary_drift_type,
            severity=severity,
            baseline_fingerprint=baseline_fingerprint or "baseline",
            current_fingerprint=current_fingerprint or "current",
            drifted_fields=drifted,
            requires_pool_invalidation=requires_pool_invalidation,
            details={"drifted_count": len(drifted)},
        )
