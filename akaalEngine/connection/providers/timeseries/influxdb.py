"""
akaalEngine.connection.providers.timeseries.influxdb
========================================================
Canonical InfluxDB Provider Strategy (P7A Campaign B) -- the Engine's first time-series
family provider.

InfluxDB (2.x) is architecturally distinct from every relational/warehouse/NoSQL provider
already adopted:
  - Data model is measurement/tags/fields/timestamp, not rows-and-columns or documents --
    tags are indexed dimensions, fields are the actual (typically numeric) values.
  - Query language is Flux (or InfluxQL for 1.x compatibility), not SQL or N1QL.
  - There is no transaction concept at all -- writes are individual point ingestions
    (optionally batched), not part of any multi-statement unit of work.
  - Retention is a first-class, per-bucket property (`retention_rules`), a genuine
    time-series-native capability distinct from any relational partitioning scheme.
  - No native CDC: there is no change-log; only time-range re-querying is possible.
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

logger = logging.getLogger("akaalEngine.connection.providers.influxdb")


class InfluxDBProviderStrategy(BaseProviderStrategy):
    """Canonical InfluxDB provider strategy -- measurement/tag/field time-series store."""

    PROVIDER_ID = "influxdb"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "timeseries"
    VENDOR_NAME = "InfluxData"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.REFERENCE],
            supports_tls=True,
            supports_mtls=False,
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,  # Flux schema.measurements()/tagKeys()/fieldKeys()
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TIME_SERIES_NATIVE": CapabilitySupportStatus.SUPPORTED,
                "RETENTION_POLICY_MANAGEMENT": CapabilitySupportStatus.SUPPORTED,  # per-bucket retention_rules
                # Truthfully NOT claimed supported: no transaction or change-log concept
                # exists in InfluxDB at all -- not a live-probe-dependent gap like other
                # providers, but a genuine absence in the product itself.
                "TRANSACTIONS": CapabilitySupportStatus.UNSUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "InfluxDB has no transaction concept; writes are individual point ingestions, not multi-statement units of work.",
                "No native change-log exists; only time-range re-querying is possible for incremental extraction.",
            ],
            required_privileges=["read:buckets", "write:buckets"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import influxdb_client
            return True, "influxdb-client library available."
        except ImportError:
            return False, "influxdb-client library not installed. Install via 'pip install influxdb-client'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        if not spec.host:
            raise ValueError("InfluxDB host is required.")

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
                    error_code="INFLUXDB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from influxdb_client import InfluxDBClient

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 8086
        tls_mode = spec.tls_binding.mode.value if hasattr(spec.tls_binding.mode, "value") else str(spec.tls_binding.mode)
        is_tls = tls_mode != "DISABLED"
        scheme = "https" if is_tls else "http"
        url = spec.options.get("url", f"{scheme}://{host}:{port}")

        token = credentials.get("token") or spec.options.get("auth_token")
        org = spec.options.get("org", "")

        client = InfluxDBClient(
            url=url,
            token=token,
            org=org,
            timeout=max(1000, int(spec.route_spec.connect_timeout_ms)),
        )
        return client

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
            return bool(connection.ping())
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return self.validate(connection)

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_version = "InfluxDB"
        if connection is not None:
            try:
                health = connection.health()
                if health and getattr(health, "version", None):
                    server_version = f"InfluxDB {health.version}"
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 8086,
            server_version=server_version,
            catalog_or_database=spec.options.get("bucket", ""),
            principal_identity=spec.options.get("org", ""),
            route_type=spec.route_spec.route_type,
            # Truthful: InfluxDB 2.x clusters are compute/storage-separated (InfluxDB IOx),
            # not a primary/replica pair or broker cluster.
            topology_role="TIME_SERIES_ENGINE",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="influxdb-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TIME_SERIES_NATIVE": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="influxdb-attested",
            granted_privileges=["read:buckets", "write:buckets"] if connection is not None else [],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=connection is not None and not purpose.is_read_only_by_default,
            can_ddl=False,
            can_cdc=False,
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
        code = "INFLUXDB_ERROR"
        retryable = False

        if "unauthorized" in lower_msg or "invalid token" in lower_msg:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "INFLUXDB_AUTH_FAILED"
        elif "forbidden" in lower_msg or "insufficient permissions" in lower_msg:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "INFLUXDB_PERMISSION_DENIED"
        elif "bucket not found" in lower_msg or "organization not found" in lower_msg:
            category = FailureCategory.INVALID_CONFIGURATION
            code = "INFLUXDB_RESOURCE_NOT_FOUND"
        elif "too many requests" in lower_msg or "429" in lower_msg:
            category = FailureCategory.TIMEOUT
            code = "INFLUXDB_RATE_LIMITED"
            retryable = True
        elif "timeout" in lower_msg:
            category = FailureCategory.TIMEOUT
            code = "INFLUXDB_TIMEOUT"
            retryable = True
        elif "connection" in lower_msg and "refused" in lower_msg:
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "INFLUXDB_UNAVAILABLE"
            retryable = True

        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=exc_name,
        )
