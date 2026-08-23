"""
akaalEngine.connection.probes.capabilities
==========================================
Live endpoint capability verification probe.
"""

from __future__ import annotations

import logging
from typing import Optional

from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog, default_provider_catalog
from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
from akaalEngine.connection.models.capability import ProbedCapabilitySnapshot
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.session import SessionPurpose, SessionRequest
from akaalEngine.connection.sessions.factory import SessionFactory, default_session_factory

logger = logging.getLogger("akaalEngine.connection.probes.capabilities")


class CapabilityProbe:
    """
    Probes live engine and server features against an active database session.
    """

    def __init__(
        self,
        catalog: Optional[ProviderCatalog] = None,
        factory: Optional[SessionFactory] = None,
    ) -> None:
        self.catalog = catalog or default_provider_catalog
        self.factory = factory or default_session_factory

    def probe_capabilities(self, spec: EndpointSpec) -> ProbedCapabilitySnapshot:
        """
        Connects ephemerally and probes live capability truth.
        """
        fp = compute_endpoint_fingerprint(spec).fingerprint_sha256
        strategy = self.catalog.get_strategy(spec.provider_id)
        req = SessionRequest(purpose=SessionPurpose.DISCOVERY, endpoint_spec=spec)

        handle, route = self.factory.create_physical_session(req)
        try:
            snapshot = strategy.probe_capabilities(handle.physical_connection, spec)
            return snapshot
        finally:
            strategy.close(handle.physical_connection)
            route.close()
