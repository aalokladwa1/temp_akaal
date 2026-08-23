"""
akaalEngine.connection.probes.permissions
=========================================
Purpose-specific permission verification probe.
Guarantees fail-closed authorization truth: zero default-true fake privilege assumptions.
"""

from __future__ import annotations

import logging
from typing import Optional

from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog, default_provider_catalog
from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
from akaalEngine.connection.models.capability import PermissionSnapshot
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.session import SessionPurpose, SessionRequest
from akaalEngine.connection.sessions.factory import SessionFactory, default_session_factory

logger = logging.getLogger("akaalEngine.connection.probes.permissions")


class PermissionProbe:
    """
    Probes physical database / endpoint privileges against requested execution purposes.
    """

    def __init__(
        self,
        catalog: Optional[ProviderCatalog] = None,
        factory: Optional[SessionFactory] = None,
    ) -> None:
        self.catalog = catalog or default_provider_catalog
        self.factory = factory or default_session_factory

    def probe_permissions(
        self,
        spec: EndpointSpec,
        purpose: SessionPurpose = SessionPurpose.PERMISSION_PROBE,
    ) -> PermissionSnapshot:
        """
        Connects ephemerally and executes provider-specific permission verification.
        """
        fp = compute_endpoint_fingerprint(spec).fingerprint_sha256
        strategy = self.catalog.get_strategy(spec.provider_id)
        req = SessionRequest(purpose=purpose, endpoint_spec=spec)

        handle, route = self.factory.create_physical_session(req)
        try:
            snapshot = strategy.probe_permissions(handle.physical_connection, spec, purpose)
            return snapshot
        finally:
            strategy.close(handle.physical_connection)
            route.close()
