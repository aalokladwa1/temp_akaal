"""
akaalEngine.connection.probes.health
====================================
Real-time endpoint health probe and latency monitoring.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog, default_provider_catalog
from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.health import ConnectionHealthSnapshot, HealthState
from akaalEngine.connection.models.session import SessionPurpose, SessionRequest
from akaalEngine.connection.sessions.factory import SessionFactory, default_session_factory

logger = logging.getLogger("akaalEngine.connection.probes.health")


class HealthProbe:
    """
    Checks real-time health, round-trip ping time, and operational readiness of an endpoint.
    """

    def __init__(
        self,
        catalog: Optional[ProviderCatalog] = None,
        factory: Optional[SessionFactory] = None,
    ) -> None:
        self.catalog = catalog or default_provider_catalog
        self.factory = factory or default_session_factory

    def check_health(self, spec: EndpointSpec) -> ConnectionHealthSnapshot:
        """
        Executes a live health ping against the endpoint.
        """
        fp = compute_endpoint_fingerprint(spec).fingerprint_sha256
        strategy = self.catalog.get_strategy(spec.provider_id)
        req = SessionRequest(purpose=SessionPurpose.HEALTH_PROBE, endpoint_spec=spec)

        t0 = time.perf_counter()
        try:
            handle, route = self.factory.create_physical_session(req)
            try:
                is_valid = strategy.validate(handle.physical_connection)
                rtt_ms = (time.perf_counter() - t0) * 1000.0
                state = HealthState.HEALTHY if is_valid else HealthState.DEGRADED
                facts = strategy.get_health_facts(handle.physical_connection)

                return ConnectionHealthSnapshot(
                    provider_id=spec.provider_id,
                    endpoint_fingerprint=fp,
                    state=state,
                    rtt_ms=rtt_ms,
                    last_successful_ping=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    consecutive_failures=0 if is_valid else 1,
                    error_rate_percentage=0.0 if is_valid else 100.0,
                    details=facts,
                )
            finally:
                strategy.close(handle.physical_connection)
                route.close()

        except Exception as exc:
            rtt_ms = (time.perf_counter() - t0) * 1000.0
            return ConnectionHealthSnapshot(
                provider_id=spec.provider_id,
                endpoint_fingerprint=fp,
                state=HealthState.UNHEALTHY,
                rtt_ms=rtt_ms,
                consecutive_failures=1,
                error_rate_percentage=100.0,
                details={"error": str(exc)},
            )
