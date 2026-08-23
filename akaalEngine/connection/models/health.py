"""
akaalEngine.connection.models.health
====================================
Canonical connection health, test results, pressure telemetry, and pool snapshot models.
Provides sanitized measured performance facts for future runtime scheduling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional

from akaalEngine.connection.models.errors import ConnectionFailure
from akaalEngine.connection.security.redaction import SafeReprMixin


class HealthState(str, Enum):
    """Overall operational health state of an endpoint."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ConnectionTestResult(SafeReprMixin):
    """
    Measured results of end-to-end connection testing across all network and protocol stages.
    """
    is_successful: bool
    provider_id: str
    endpoint_fingerprint: str
    dns_latency_ms: float = 0.0
    tcp_latency_ms: float = 0.0
    tls_latency_ms: float = 0.0
    auth_latency_ms: float = 0.0
    total_handshake_ms: float = 0.0
    server_version: Optional[str] = None
    tls_cipher: Optional[str] = None
    failure: Optional[ConnectionFailure] = None
    tested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_successful": self.is_successful,
            "provider_id": self.provider_id,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "dns_latency_ms": round(self.dns_latency_ms, 2),
            "tcp_latency_ms": round(self.tcp_latency_ms, 2),
            "tls_latency_ms": round(self.tls_latency_ms, 2),
            "auth_latency_ms": round(self.auth_latency_ms, 2),
            "total_handshake_ms": round(self.total_handshake_ms, 2),
            "server_version": self.server_version,
            "tls_cipher": self.tls_cipher,
            "failure": self.failure.to_dict() if self.failure else None,
            "tested_at": self.tested_at,
        }


@dataclass(frozen=True)
class ConnectionHealthSnapshot(SafeReprMixin):
    """
    Periodic or on-demand health snapshot of an active physical endpoint connection.
    """
    provider_id: str
    endpoint_fingerprint: str
    state: HealthState
    rtt_ms: float = 0.0
    last_successful_ping: Optional[str] = None
    consecutive_failures: int = 0
    error_rate_percentage: float = 0.0
    server_load_indicator: Optional[str] = None
    active_sessions_count: int = 0
    details: Mapping[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "state": self.state.value,
            "rtt_ms": round(self.rtt_ms, 2),
            "last_successful_ping": self.last_successful_ping,
            "consecutive_failures": self.consecutive_failures,
            "error_rate_percentage": round(self.error_rate_percentage, 2),
            "server_load_indicator": self.server_load_indicator,
            "active_sessions_count": self.active_sessions_count,
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class ConnectionPressureSnapshot(SafeReprMixin):
    """
    Real-time measurement of pool saturation, checkout queue pressure, and concurrency limits.
    Used by Runtime and Transport to adapt batch sizes and worker concurrency.
    """
    endpoint_fingerprint: str
    provider_id: str
    active_leases_count: int
    idle_pool_count: int
    pending_waiters_count: int
    pool_utilization_ratio: float               # active / (active + idle)
    is_saturated: bool
    avg_checkout_wait_ms: float = 0.0
    max_checkout_wait_ms: float = 0.0
    recommended_concurrency_ceiling: int = 32
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "provider_id": self.provider_id,
            "active_leases_count": self.active_leases_count,
            "idle_pool_count": self.idle_pool_count,
            "pending_waiters_count": self.pending_waiters_count,
            "pool_utilization_ratio": round(self.pool_utilization_ratio, 3),
            "is_saturated": self.is_saturated,
            "avg_checkout_wait_ms": round(self.avg_checkout_wait_ms, 2),
            "max_checkout_wait_ms": round(self.max_checkout_wait_ms, 2),
            "recommended_concurrency_ceiling": self.recommended_concurrency_ceiling,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class PoolSnapshot(SafeReprMixin):
    """
    Snapshot of physical connection pool statistics for an endpoint.
    """
    pool_id: str
    endpoint_fingerprint: str
    provider_id: str
    purpose: Optional[str]
    total_allocated: int
    active_count: int
    idle_count: int
    min_size: int
    max_size: int
    checkout_count: int = 0
    eviction_count: int = 0
    leaks_detected: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_pruned_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "provider_id": self.provider_id,
            "purpose": self.purpose,
            "total_allocated": self.total_allocated,
            "active_count": self.active_count,
            "idle_count": self.idle_count,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "checkout_count": self.checkout_count,
            "eviction_count": self.eviction_count,
            "leaks_detected": self.leaks_detected,
            "created_at": self.created_at,
            "last_pruned_at": self.last_pruned_at,
        }
