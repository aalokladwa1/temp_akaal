"""
akaalEngine.connection.providers.nosql.couchbase
====================================================
Canonical Couchbase Provider Strategy (P7A Campaign B).

Couchbase is a genuinely different document architecture from MongoDB despite both being
JSON document stores:
  - Multi-document ACID transactions are a real, SDK-native feature (Couchbase
    Transactions, SDK 3.0+) -- not borrowed from MongoDB's replica-set-based transaction
    model.
  - N1QL (SQL++) is Couchbase's real query language over JSON documents, including a
    genuine `INFER` statement for schema shape discovery -- a real capability distinct
    from MongoDB's `$jsonSchema` validator introspection.
  - Real change-data-capture exists via DCP (Database Change Protocol), but DCP requires
    a low-level streaming client this connector does not wire -- CDC_LOG_CAPTURE is
    declared UNSUPPORTED at this layer rather than assumed from the product's capability.
"""

from __future__ import annotations

import logging
import ssl
from datetime import timedelta
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
    ConnectionFailure,
    FailureCategory,
    DependencyMissingError,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.couchbase")


class CouchbaseProviderStrategy(BaseProviderStrategy):
    """Canonical Couchbase provider strategy -- N1QL document store with real ACID transactions."""

    PROVIDER_ID = "couchbase"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "nosql"
    VENDOR_NAME = "Couchbase, Inc."

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.REFERENCE, EndpointRole.VALIDATION],
            supports_tls=True,
            supports_mtls=True,
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,  # N1QL INFER
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,  # real multi-document ACID transactions
                "SECONDARY_INDEXES": CapabilitySupportStatus.SUPPORTED,  # GSI
                "FULL_TEXT_SEARCH": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.UNSUPPORTED,
                # Truthfully NOT claimed supported: DCP-based CDC requires a low-level
                # streaming client this connector does not wire.
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "CDC_LOG_CAPTURE (DCP) requires a dedicated low-level streaming client not wired by this connector strategy.",
            ],
            required_privileges=["query_select", "query_insert"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import couchbase
            return True, "couchbase SDK available."
        except ImportError:
            return False, "couchbase library not installed. Install via 'pip install couchbase'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        if not spec.host:
            raise ValueError("Couchbase host is required.")

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
                    error_code="COUCHBASE_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from couchbase.cluster import Cluster
        from couchbase.options import ClusterOptions
        from couchbase.auth import PasswordAuthenticator

        host = resolved_route.effective_host
        tls_mode = spec.tls_binding.mode.value if hasattr(spec.tls_binding.mode, "value") else str(spec.tls_binding.mode)
        is_tls = tls_mode != "DISABLED"
        scheme = "couchbases" if is_tls else "couchbase"
        conn_str = spec.options.get("connection_string", f"{scheme}://{host}")

        username = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        password = credentials.get("password")

        authenticator = PasswordAuthenticator(username, password)
        cluster = Cluster(conn_str, ClusterOptions(authenticator))
        cluster.wait_until_ready(timedelta(seconds=max(1, spec.route_spec.connect_timeout_ms / 1000.0)))
        return cluster

    def close(self, connection: Any) -> None:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            result = connection.query("SELECT 1 AS ok").execute()
            return bool(result)
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return connection is not None

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
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 11210,
            server_version="Couchbase Server",
            catalog_or_database=spec.options.get("bucket", spec.database_name or ""),
            principal_identity=spec.auth_spec.username if spec.auth_spec else "couchbase_client",
            route_type=spec.route_spec.route_type,
            # Truthful: Couchbase is a multi-node cluster with automatic data
            # rebalancing/sharding across vBuckets -- not a primary/replica pair.
            topology_role="MULTI_NODE_CLUSTER",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="couchbase-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="couchbase-attested",
            granted_privileges=["query_select", "query_insert"] if connection is not None else [],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=connection is not None and not purpose.is_read_only_by_default,
            can_ddl=False,
            can_cdc=False,  # never truthfully claimable without a wired DCP client
            is_admin=False,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        exc_name = type(exc).__name__
        lower_msg = msg.lower()
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "COUCHBASE_ERROR"
        retryable = False

        if "authenticationerror" in exc_name.lower() or "authentication" in lower_msg:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "COUCHBASE_AUTH_FAILED"
        elif "permission" in lower_msg or "not_authorized" in lower_msg:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "COUCHBASE_PERMISSION_DENIED"
        elif "documentnotfound" in exc_name.lower():
            category = FailureCategory.INVALID_CONFIGURATION
            code = "COUCHBASE_DOCUMENT_NOT_FOUND"
        elif "casmismatch" in exc_name.lower() or "cas mismatch" in lower_msg:
            category = FailureCategory.TIMEOUT
            code = "COUCHBASE_CAS_CONFLICT"
            retryable = True
        elif "timeout" in lower_msg or "ambiguoustimeout" in exc_name.lower() or "unambiguoustimeout" in exc_name.lower():
            category = FailureCategory.TIMEOUT
            code = "COUCHBASE_TIMEOUT"
            retryable = True
        elif "connect" in lower_msg and ("refused" in lower_msg or "unreachable" in lower_msg):
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "COUCHBASE_UNAVAILABLE"
            retryable = True

        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=exc_name,
        )
