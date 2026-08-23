"""
akaalEngine.connection.identity.attestation
==========================================
Physical endpoint identity attestation engine.
Gathers verifiable runtime facts from live database handshakes, server metadata, and TLS peer info.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.identity.attestation")


class IdentityAttestor:
    """
    Constructs and attests PhysicalEndpointIdentity from verified endpoint facts and provider strategy inspection.
    """

    @classmethod
    def create_attested_identity(
        cls,
        spec: EndpointSpec,
        provider_version: str,
        resolved_ip: Optional[str] = None,
        server_version: Optional[str] = None,
        server_cluster_name: Optional[str] = None,
        catalog_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        principal_identity: Optional[str] = None,
        tls_cipher: Optional[str] = None,
        tls_peer_cert_sha256: Optional[str] = None,
        topology_role: Optional[str] = "PRIMARY",
        topology_generation: int = 1,
        capability_hash: Optional[str] = None,
        permission_hash: Optional[str] = None,
    ) -> PhysicalEndpointIdentity:
        """
        Creates an immutable PhysicalEndpointIdentity snapshot.
        """
        resolved_host = spec.host or "localhost"
        resolved_port = spec.port

        principal = principal_identity or (spec.auth_spec.username if spec.auth_spec else "anonymous")
        db_name = catalog_name or spec.database_name
        current_schema = schema_name or spec.schema_name

        # Calculate default capability/permission hash if not supplied
        if not capability_hash:
            cap_input = f"{spec.provider_id}:{server_version or 'unknown'}"
            capability_hash = hashlib.sha256(cap_input.encode("utf-8")).hexdigest()[:16]

        if not permission_hash:
            perm_input = f"{principal}:{db_name or 'default'}:{spec.role.value}"
            permission_hash = hashlib.sha256(perm_input.encode("utf-8")).hexdigest()[:16]

        return PhysicalEndpointIdentity(
            provider_id=spec.provider_id,
            provider_version=provider_version,
            role=spec.role,
            resolved_host=resolved_host,
            resolved_ip=resolved_ip,
            resolved_port=resolved_port,
            server_version=server_version,
            server_cluster_name=server_cluster_name,
            catalog_or_database=db_name,
            schema_name=current_schema,
            principal_identity=principal,
            cloud_resource_id=spec.cloud_resource_id,
            cloud_region=spec.region,
            cloud_account_id=spec.account_id,
            route_type=spec.route_spec.route_type,
            tls_cipher=tls_cipher,
            tls_peer_cert_sha256=tls_peer_cert_sha256,
            capability_hash=capability_hash,
            permission_hash=permission_hash,
            topology_role=topology_role,
            topology_generation=topology_generation,
        )
