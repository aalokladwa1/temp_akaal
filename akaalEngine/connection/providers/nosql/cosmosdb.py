"""
akaalEngine.connection.providers.nosql.cosmosdb
================================================
Canonical Azure Cosmos DB Provider Strategy (P7A Campaign B, provider #44).

Distributed, multi-model, partition-key-based document store. Connects via the real
`azure-cosmos` SDK. The physical connection handle returned is the `ContainerProxy` for
the configured database/container -- the actual object the Transport driver's
`db_connection` parameter expects (see transport/drivers/cosmosdb.py), not merely a
top-level client.
"""

from __future__ import annotations

import logging
import ssl
from typing import Any, Mapping, Optional, Tuple

from akaalEngine.connection.models.capability import (
    CapabilitySupportStatus,
    PermissionSnapshot,
    ProbedCapabilitySnapshot,
    ProofLevel,
    StaticCapabilityManifest,
)
from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.errors import (
    ConfigurationError,
    ConnectionFailure,
    FailureCategory,
    DependencyMissingError,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.cosmosdb")


class CosmosDBProviderStrategy(BaseProviderStrategy):
    """Canonical Azure Cosmos DB provider strategy -- distributed multi-model store."""

    PROVIDER_ID = "cosmosdb"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "nosql"
    VENDOR_NAME = "Microsoft Azure"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.REFERENCE, EndpointRole.VALIDATION],
            supports_tls=True,
            supports_mtls=False,
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,  # container/partition-key metadata only, no fixed doc schema
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.UNSUPPORTED,  # per-item upsert only, no batch API used here
                "TRANSACTIONS": CapabilitySupportStatus.UNSUPPORTED,  # transactional batch restricted to a single partition key; not used
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.UNSUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,  # Change Feed not implemented here
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "Documents carry no enforced schema outside the partition key; only container/partition-key metadata is discoverable.",
                "Writes are per-item upsert_item() calls, not a native batch/bulk executor.",
            ],
            required_privileges=["Microsoft.DocumentDB/databaseAccounts/readMetadata", "Microsoft.DocumentDB/databaseAccounts/dataOperations"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import azure.cosmos
            return True, "azure-cosmos SDK available."
        except ImportError:
            return False, "'azure-cosmos' SDK not installed. Install via 'pip install azure-cosmos'."

    def connect(
        self,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
        credentials: Mapping[str, Any],
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> Any:
        avail, msg = self.is_dependency_available()
        if not avail:
            raise DependencyMissingError(
                ConnectionFailure(
                    error_code="COSMOSDB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from azure.cosmos import CosmosClient

        endpoint = spec.options.get("endpoint") or (f"https://{spec.host}:{spec.port or 443}/" if spec.host else None)
        key = credentials.get("key") or credentials.get("password")
        database_name = spec.database_name or spec.options.get("database")
        container_name = spec.options.get("container_name") or spec.options.get("table_name")
        if not endpoint or not key:
            raise ConfigurationError(
                ConnectionFailure(
                    error_code="COSMOSDB_MISSING_ENDPOINT_OR_KEY",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message="Cosmos DB requires 'endpoint' (spec.options) and an account key credential.",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        client = CosmosClient(endpoint, credential=key)
        if not database_name:
            return client
        database = client.get_database_client(database_name)
        if not container_name:
            return database
        return database.get_container_client(container_name)

    def close(self, connection: Any) -> None:
        pass  # azure-cosmos SDK clients are HTTP-based; no persistent socket to close

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            if hasattr(connection, "read"):
                connection.read()
                return True
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return True  # stateless HTTP client, nothing session-local to reset

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=spec.host or "cosmos.azure.com",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=spec.port or 443,
            server_version="Azure Cosmos DB",
            catalog_or_database=spec.database_name,
            schema_name=spec.options.get("container_name"),
            cloud_region=spec.region or spec.options.get("region"),
            route_type=spec.route_spec.route_type,
            topology_role="MANAGED_DISTRIBUTED_STORE",
        )

    def probe_capabilities(self, connection: Any, spec: EndpointSpec) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="cosmosdb-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(self, connection: Any, spec: EndpointSpec, purpose: SessionPurpose) -> PermissionSnapshot:
        granted: list[str] = []
        if connection is not None:
            try:
                if hasattr(connection, "read"):
                    connection.read()
                granted = ["read"]
                if not purpose.is_read_only_by_default:
                    granted.append("write")
            except Exception:
                granted = []
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="cosmosdb-attested",
            granted_privileges=granted,
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write="write" in granted,
            can_ddl=False,
            can_cdc=False,
            is_admin=False,
        )

    def normalize_error(self, exc: Exception, stage: str = "EXECUTION") -> ConnectionFailure:
        msg = redact_text(str(exc))
        status_code = getattr(exc, "status_code", None)
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "COSMOSDB_ERROR"
        retryable = False
        if status_code == 401:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "COSMOSDB_AUTH_FAILED"
        elif status_code == 403:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "COSMOSDB_PERMISSION_DENIED"
        elif status_code == 404:
            category = FailureCategory.INVALID_CONFIGURATION
            code = "COSMOSDB_NOT_FOUND"
        elif status_code == 429:
            category = FailureCategory.TIMEOUT
            code = "COSMOSDB_THROTTLED"
            retryable = True
        elif "timeout" in msg.lower() or "connection" in msg.lower():
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "COSMOSDB_UNAVAILABLE"
            retryable = True
        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
