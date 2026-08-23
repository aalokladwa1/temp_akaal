"""
akaalEngine.connection.probes.pressure
======================================
Connection pressure and pool saturation telemetry probe.
"""

from __future__ import annotations

import logging
from typing import Optional

from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.health import ConnectionPressureSnapshot
from akaalEngine.connection.pooling.manager import PoolManager, default_pool_manager

logger = logging.getLogger("akaalEngine.connection.probes.pressure")


class PressureProbe:
    """
    Measures real-time pool checkout wait, utilization, active counts, and saturation ceilings.
    """

    def __init__(self, pool_manager: Optional[PoolManager] = None) -> None:
        self.pool_manager = pool_manager or default_pool_manager

    def get_pressure(self, spec: EndpointSpec) -> ConnectionPressureSnapshot:
        """
        Retrieves real-time saturation and queue telemetry for an endpoint.
        """
        fp = compute_endpoint_fingerprint(spec).fingerprint_sha256
        snapshot = self.pool_manager.get_pressure_snapshot(fp)
        if snapshot:
            return snapshot

        # Default empty pressure snapshot if no active pool currently initialized
        return ConnectionPressureSnapshot(
            endpoint_fingerprint=fp,
            provider_id=spec.provider_id,
            active_leases_count=0,
            idle_pool_count=0,
            pending_waiters_count=0,
            pool_utilization_ratio=0.0,
            is_saturated=False,
            avg_checkout_wait_ms=0.0,
            max_checkout_wait_ms=0.0,
            recommended_concurrency_ceiling=16,
        )
