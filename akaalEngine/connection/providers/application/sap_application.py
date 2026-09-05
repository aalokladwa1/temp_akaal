"""
akaalEngine.connection.providers.application.sap_application
================================================================
Canonical SAP Application Ecosystem Provider Strategy (P7A Campaign B, provider #47).

Owner-resolved scope (2026-09-05): ONE canonical provider family, architecturally
distinct from SAP HANA (the database engine, provider #41), supporting
capability-driven RFC/BAPI, IDoc, and OData interface MODES selected via
`spec.options["interface_mode"]` -- never three separate provider identities.

- OData: connects a real `requests.Session` against an SAP Gateway OData service base
  URL -- no proprietary SDK required, fully locally provable.
- RFC/BAPI and IDoc: connect via the proprietary `pyrfc` SDK (requires SAP's NetWeaver
  RFC SDK C library). Genuinely dependency-gated: `is_dependency_available()` truthfully
  reports pyrfc's absence, and `connect()` fails closed with `DependencyMissingError`
  rather than fabricating a connection.
"""

from __future__ import annotations

import logging
import ssl
from typing import Any, Dict, Mapping, Optional, Tuple

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

logger = logging.getLogger("akaalEngine.connection.providers.sap_application")

_VALID_MODES = ("odata", "rfc_bapi", "idoc")


class SAPApplicationProviderStrategy(BaseProviderStrategy):
    """Canonical SAP Application Ecosystem provider strategy -- capability-driven
    RFC/BAPI, IDoc, and OData interface modes under one provider identity."""

    PROVIDER_ID = "sap_application"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "application"
    VENDOR_NAME = "SAP SE"

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
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,  # OData $metadata / RFC_READ_TABLE field catalog
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,  # bounded $skip/$top or ROWSKIPS/ROWCOUNT pagination
                "BULK_WRITE": CapabilitySupportStatus.UNSUPPORTED,  # per-record OData/BAPI/IDoc calls only, no batch API used here
                "TRANSACTIONS": CapabilitySupportStatus.UNSUPPORTED,  # no ambient multi-record SAP LUW spanned by this Engine
                "FOREIGN_KEYS": CapabilitySupportStatus.UNSUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,  # no capture module implemented
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "interface_mode='odata' is locally provable without proprietary dependencies.",
                "interface_mode in {'rfc_bapi','idoc'} requires the proprietary 'pyrfc' SDK "
                "(SAP NetWeaver RFC SDK C library) and fails closed (DependencyMissingError) "
                "when it is not installed -- never silently degrades to OData or a fake success.",
                "Writes are per-record OData PUT/POST, BAPI calls, or IDoc inbound posts -- "
                "not a native SAP batch-input/LSMW/bulk executor.",
            ],
            required_privileges=["S_RFC", "S_TABU_DIS"],
        )

    def _mode(self, spec: EndpointSpec) -> str:
        mode = (spec.options.get("interface_mode") or "odata").strip().lower()
        if mode not in _VALID_MODES:
            raise ConfigurationError(
                ConnectionFailure(
                    error_code="SAP_APPLICATION_INVALID_INTERFACE_MODE",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message=f"Unknown interface_mode '{mode}'. Valid modes: {_VALID_MODES}",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )
        return mode

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import requests  # noqa: F401
        except ImportError:
            return False, "'requests' library not installed. Install via 'pip install requests'."
        try:
            import pyrfc  # noqa: F401
            return True, "requests (OData) and pyrfc (RFC/BAPI, IDoc) both available."
        except ImportError:
            return True, (
                "requests (OData mode) available; 'pyrfc' (RFC/BAPI and IDoc modes) is NOT "
                "installed -- those two interface modes will fail closed with "
                "DependencyMissingError until the proprietary SAP NetWeaver RFC SDK is provisioned."
            )

    def connect(
        self,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
        credentials: Mapping[str, Any],
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> Any:
        mode = self._mode(spec)

        if mode == "odata":
            try:
                import requests
            except ImportError:
                raise DependencyMissingError(
                    ConnectionFailure(
                        error_code="SAP_APPLICATION_DEPENDENCY_MISSING",
                        category=FailureCategory.DEPENDENCY_MISSING,
                        message="'requests' library not installed. Install via 'pip install requests'.",
                        retryable=False,
                        provider_id=self.PROVIDER_ID,
                    )
                )
            instance = spec.host
            base_url = instance if (instance and instance.startswith("http")) else f"https://{instance}"
            session = requests.Session()
            session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
            username = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
            password = credentials.get("password")
            if username and password:
                session.auth = (username, password)
            session.base_url = base_url + (spec.options.get("service_path") or "")
            return session

        # rfc_bapi / idoc
        try:
            import pyrfc
        except ImportError:
            raise DependencyMissingError(
                ConnectionFailure(
                    error_code="SAP_APPLICATION_PYRFC_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=(
                        "SAP Application Ecosystem RFC/BAPI and IDoc interface modes require the "
                        "proprietary 'pyrfc' SDK (SAP NetWeaver RFC SDK C library). Install via the "
                        "SAP-provided instructions after provisioning the NW RFC SDK; not available "
                        "on PyPI as a self-contained package."
                    ),
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )
        conn_params: Dict[str, Any] = {
            "ashost": spec.host,
            "sysnr": spec.options.get("system_number", "00"),
            "client": spec.options.get("client", "100"),
            "user": credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None),
            "passwd": credentials.get("password"),
        }
        return pyrfc.Connection(**conn_params)

    def close(self, connection: Any) -> None:
        if connection is None:
            return
        try:
            if hasattr(connection, "close"):
                connection.close()
        except Exception:
            pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            if hasattr(connection, "get") and hasattr(connection, "base_url"):
                resp = connection.get(f"{connection.base_url}/$metadata")
                return bool(resp is not None and getattr(resp, "status_code", 500) < 400)
            if hasattr(connection, "alive"):
                return bool(connection.alive)
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return True  # both OData (stateless HTTP) and RFC (stateless call-based) have nothing session-local to reset

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        mode = self._mode(spec)
        host = getattr(connection, "base_url", None) or spec.host or "sap-application.internal"
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443 if mode == "odata" else 3300,
            server_version=f"SAP Application Ecosystem ({mode})",
            catalog_or_database=spec.options.get("client") if mode != "odata" else None,
            route_type=spec.route_spec.route_type,
            topology_role="MANAGED_SAAS_PLATFORM" if mode == "odata" else "SAP_APPLICATION_SERVER",
        )

    def probe_capabilities(self, connection: Any, spec: EndpointSpec) -> ProbedCapabilitySnapshot:
        mode = self._mode(spec)
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint=f"sap-application-{mode}-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(self, connection: Any, spec: EndpointSpec, purpose: SessionPurpose) -> PermissionSnapshot:
        granted: list[str] = []
        if connection is not None and self.validate(connection):
            granted = ["read"]
            if not purpose.is_read_only_by_default:
                granted.append("write")
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="sap-application-attested",
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
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "SAP_APPLICATION_ERROR"
        retryable = False
        lower = msg.lower()
        status_code = getattr(exc, "response", None)
        status_code = getattr(status_code, "status_code", None) if status_code is not None else None
        if status_code == 401 or "logon" in lower or "authenticat" in lower:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "SAP_APPLICATION_AUTH_FAILED"
        elif status_code == 403 or "not authorized" in lower:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "SAP_APPLICATION_PERMISSION_DENIED"
        elif "timeout" in lower or "connection" in lower or "unreachable" in lower:
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "SAP_APPLICATION_UNAVAILABLE"
            retryable = True
        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
