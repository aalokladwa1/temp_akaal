"""
akaalEngine.connection.pooling.policy
=====================================
Pool configuration policies, capacity boundaries, idle timeouts, and budget limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from akaalEngine.connection.models.endpoint import EndpointRole
from akaalEngine.connection.security.redaction import SafeReprMixin


@dataclass(frozen=True)
class PoolPolicy(SafeReprMixin):
    """
    Immutable policy controlling pool bounds, lifecycle timeouts, wait queues, and warm-up.
    """
    min_size: int = 1
    max_size: int = 10
    idle_timeout_seconds: float = 60.0
    max_lifetime_seconds: float = 1800.0
    acquisition_timeout_seconds: float = 10.0
    validate_on_checkout: bool = True
    validation_interval_seconds: float = 30.0
    max_waiters: int = 100
    enable_prewarm: bool = False
    prewarm_size: int = 1
    asymmetric_budget_role: Optional[EndpointRole] = None

    @classmethod
    def default_for_role(cls, role: EndpointRole) -> PoolPolicy:
        """Produces role-appropriate default pool policies."""
        if role == EndpointRole.TARGET:
            # Targets need higher concurrency for bulk writers
            return cls(min_size=2, max_size=16, idle_timeout_seconds=120.0, asymmetric_budget_role=role)
        elif role == EndpointRole.SOURCE:
            # Sources typically balance snapshot reading and partition slicing
            return cls(min_size=1, max_size=8, idle_timeout_seconds=60.0, asymmetric_budget_role=role)
        elif role == EndpointRole.CDC_LOG:
            # CDC capture requires dedicated long-lived low-churn connection
            return cls(min_size=1, max_size=2, idle_timeout_seconds=3600.0, max_lifetime_seconds=86400.0, asymmetric_budget_role=role)
        elif role in (EndpointRole.METADATA, EndpointRole.VALIDATION):
            return cls(min_size=1, max_size=4, idle_timeout_seconds=30.0, asymmetric_budget_role=role)
        return cls()
