"""
akaalEngine.connection.providers.cloud.aws_profiles
===================================================
AWS Managed Database Profile Resolvers (RDS, Aurora PostgreSQL, Aurora MySQL, RDS Oracle, RDS SQL Server).
Resolves cloud management-plane topology and reader/writer endpoints into canonical database endpoint specifications.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import SafeReprMixin

logger = logging.getLogger("akaalEngine.connection.providers.cloud.aws")


class AWSManagedProfileResolver(SafeReprMixin):
    """
    Resolves AWS RDS / Aurora managed platform profiles to canonical database specs.
    """

    @classmethod
    def resolve_aurora_endpoint(
        cls,
        cluster_identifier: str,
        role: EndpointRole,
        engine_type: str = "postgresql",
        region: str = "us-east-1",
        account_id: Optional[str] = None,
    ) -> EndpointSpec:
        """
        Translates Aurora cluster identifier and role into Writer or Reader endpoint.
        """
        is_writer = (role == EndpointRole.TARGET or role == EndpointRole.SOURCE)
        suffix = "cluster" if is_writer else "cluster-ro"
        host = f"{cluster_identifier}.{suffix}.{region}.rds.amazonaws.com"
        port = 5432 if "postgres" in engine_type.lower() else 3306
        canonical_provider = "postgresql" if "postgres" in engine_type.lower() else "mysql"

        return EndpointSpec(
            provider_id=canonical_provider,
            host=host,
            port=port,
            role=role,
            cloud_resource_id=f"arn:aws:rds:{region}:{account_id or '123456789012'}:cluster:{cluster_identifier}",
            region=region,
            account_id=account_id,
            options={"aws_aurora_cluster": cluster_identifier, "aws_role": "WRITER" if is_writer else "READER"},
        )

    @classmethod
    def enrich_identity_with_aws_topology(
        cls,
        identity: PhysicalEndpointIdentity,
        spec: EndpointSpec,
    ) -> PhysicalEndpointIdentity:
        """Enriches an attested identity with AWS RDS / Aurora metadata."""
        cluster_id = spec.options.get("aws_aurora_cluster") or spec.cloud_resource_id
        return PhysicalEndpointIdentity(
            provider_id=identity.provider_id,
            provider_version=identity.provider_version,
            role=identity.role,
            resolved_host=identity.resolved_host,
            resolved_ip=identity.resolved_ip,
            resolved_port=identity.resolved_port,
            server_version=identity.server_version,
            server_cluster_name=cluster_id,
            catalog_or_database=identity.catalog_or_database,
            schema_name=identity.schema_name,
            principal_identity=identity.principal_identity,
            cloud_resource_id=spec.cloud_resource_id,
            cloud_region=spec.region,
            cloud_account_id=spec.account_id,
            route_type=identity.route_type,
            tls_cipher=identity.tls_cipher,
            tls_peer_cert_sha256=identity.tls_peer_cert_sha256,
            capability_hash=identity.capability_hash,
            permission_hash=identity.permission_hash,
            topology_role=spec.options.get("aws_role", identity.topology_role),
            topology_generation=identity.topology_generation,
            attestation_timestamp=identity.attestation_timestamp,
        )
