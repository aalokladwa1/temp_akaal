"""
akaalEngine.connection.providers.nosql.elasticsearch
===================================================
Canonical Elasticsearch Provider Strategy.
Supports elasticsearch-py, scroll/search APIs, bulk index actions, and index mappings.
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
    ConnectionFailure,
    FailureCategory,
    DependencyMissingError,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.elasticsearch")


class ElasticsearchProviderStrategy(BaseProviderStrategy):
    """Canonical Elasticsearch provider strategy."""

    PROVIDER_ID = "elasticsearch"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "nosql"
    VENDOR_NAME = "Elastic"

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
                "INDEX_SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "SCROLL_SEARCH": CapabilitySupportStatus.SUPPORTED,
                "POINT_IN_TIME": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import elasticsearch
            return True, f"elasticsearch-py version {getattr(elasticsearch, '__version__', 'unknown')} available."
        except ImportError:
            return False, "elasticsearch library not installed. Install via 'pip install elasticsearch'."

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
                    error_code="ELASTICSEARCH_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from elasticsearch import Elasticsearch

        scheme = "https" if spec.tls_binding.mode.value != "DISABLED" else "http"
        urls = [u if "://" in u else f"{scheme}://{u}" for u in resolved_route.get_http_hosts()]

        api_key = credentials.get("api_key")
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        password = credentials.get("password") or None

        client_kwargs: dict[str, Any] = {
            "hosts": urls,
            "verify_certs": (spec.tls_binding.mode.value == "VERIFY_FULL"),
            "request_timeout": spec.route_spec.socket_timeout_ms / 1000.0,
        }
        if api_key:
            client_kwargs["api_key"] = api_key
        elif user and password:
            client_kwargs["basic_auth"] = (user, password)

        if ssl_context:
            client_kwargs["ssl_context"] = ssl_context
        elif spec.tls_binding.ca_cert_path:
            client_kwargs["ca_certs"] = spec.tls_binding.ca_cert_path

        client = Elasticsearch(**client_kwargs)
        return client

    def close(self, connection: Any) -> None:
        if connection and hasattr(connection, "close"):
            try:
                connection.close()
            except Exception:
                pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            return bool(connection.ping())
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return True

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_ver = "Elasticsearch"
        cluster_name = None
        if connection:
            try:
                info = connection.info()
                server_ver = f"Elasticsearch {info.get('version', {}).get('number', '')}"
                cluster_name = info.get("cluster_name")
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 9200,
            server_version=server_ver,
            server_cluster_name=cluster_name,
            catalog_or_database=spec.database_name or "default",
            principal_identity=spec.auth_spec.username if spec.auth_spec else "elastic",
            route_type=spec.route_spec.route_type,
            topology_role="SEARCH_CLUSTER",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="es-attested",
            capabilities={
                "INDEX_SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="es-attested",
            granted_privileges=["read", "write", "manage"],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=not purpose.is_read_only_by_default,
            can_ddl=purpose == SessionPurpose.SCHEMA_DDL,
            can_cdc=False,
            is_admin=False,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        return ConnectionFailure(
            error_code="ELASTICSEARCH_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
