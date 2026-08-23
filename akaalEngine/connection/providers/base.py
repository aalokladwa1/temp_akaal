"""
akaalEngine.connection.providers.base
====================================
Canonical BaseProviderStrategy interface (SPI) for Connection Authority.
All database, warehouse, nosql, streaming, and storage provider strategies implement this contract.
"""

from __future__ import annotations

import logging
import ssl
from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Tuple

from akaalEngine.connection.models.capability import (
    CapabilitySupportStatus,
    PermissionSnapshot,
    ProbedCapabilitySnapshot,
    ProofLevel,
    StaticCapabilityManifest,
)
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.base")


class BaseProviderStrategy(ABC):
    """
    Abstract internal strategy interface implemented by all physical connector providers.
    Consumed exclusively by Connection Authority.
    """

    PROVIDER_ID: str = "generic"
    PROVIDER_VERSION: str = "1.0.0"
    FAMILY: str = "generic"
    VENDOR_NAME: str = "Generic"

    @abstractmethod
    def get_static_manifest(self) -> StaticCapabilityManifest:
        """Returns the authoritative static capability manifest."""
        raise NotImplementedError

    @abstractmethod
    def is_dependency_available(self) -> Tuple[bool, str]:
        """
        Returns (is_available, diagnostic_message).
        Must NOT raise ImportError; must return truthful status.
        """
        raise NotImplementedError

    def validate_configuration(self, spec: EndpointSpec) -> None:
        """Validates configuration parameters before connection attempt."""
        if not spec.provider_id:
            raise ValueError("EndpointSpec provider_id is required.")

    @abstractmethod
    def connect(
        self,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
        credentials: Mapping[str, Any],
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> Any:
        """
        Establishes physical connection to the endpoint using native driver / SDK client.
        Must use resolved_route.effective_host and effective_port.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self, connection: Any) -> None:
        """Closes the physical connection cleanly."""
        raise NotImplementedError

    @abstractmethod
    def validate(self, connection: Any) -> bool:
        """Validates whether an existing physical connection is active and healthy (e.g. SELECT 1 / PING)."""
        raise NotImplementedError

    @abstractmethod
    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        """
        Rolls back uncommitted transactions, restores autocommit/isolation, and resets session state.
        Returns True if session is clean and reusable, False if it must be destroyed.
        """
        raise NotImplementedError

    @abstractmethod
    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        """Attests live server version, cluster name, catalog, and peer identity facts."""
        raise NotImplementedError

    @abstractmethod
    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        """Probes live engine capabilities against the connected database."""
        raise NotImplementedError

    @abstractmethod
    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        """Probes live privileges for the authenticated user."""
        raise NotImplementedError

    @abstractmethod
    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        """Maps driver-specific exception into canonical ConnectionFailure with secret redaction."""
        raise NotImplementedError

    def get_health_facts(self, connection: Any) -> dict[str, Any]:
        """Gathers provider-specific runtime health telemetry."""
        return {"provider_id": self.PROVIDER_ID, "is_active": True}

    def get_fastpath_hints(self) -> dict[str, Any]:
        """Returns native optimization fast-path hints (e.g., binary copy, chunk sizes, array bindings)."""
        return {}

    def is_thread_safe(self) -> bool:
        """Declares whether connections from this provider are safely shareable across threads."""
        return False
