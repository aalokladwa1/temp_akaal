"""
akaalEngine.fabric.site_coordination.models
==============================================
P7B.24 -- Distributed Site Coordination data model.

Composes over the existing P7B.5 SiteRegistry trust ladder (SiteTrustState) and
ExecutionSite's own health_state/lifecycle_state axes rather than introducing a fourth,
competing state machine. `CoordinationView` here is always a COMPUTED, read-only VIEW
derived from:
    * SiteRegistry's authoritative trust_state / tenant_binding / lifecycle_state
      (unmodified, P7B Group-1 frozen)
    * this module's own heartbeat freshness bookkeeping (liveness only -- never trust)

Heartbeat freshness is measured using time.monotonic() at the RECEIVING process, never
the site-supplied wall-clock timestamp carried in `sent_at` -- a compromised or
clock-skewed site must not be able to manufacture freshness merely by lying about when
it says it sent the heartbeat (P7B.24 Section 6 time-semantics discipline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Optional, Tuple

from akaalEngine.fabric.execution_site.models import (
    SiteHealthState,
    SiteLifecycleState,
    SiteTrustState,
)


class SiteCoordinationError(RuntimeError):
    pass


class HeartbeatRejectedError(SiteCoordinationError):
    """Raised when a heartbeat is refused outright (revoked site, replayed/out-of-order
    sequence, or a stale fencing generation attempting to resurrect liveness). A rejected
    heartbeat NEVER mutates liveness bookkeeping -- rejection is all-or-nothing."""


class CoordinationView(str, Enum):
    """
    A truthful, multi-valued distributed-membership classification -- deliberately NOT a
    single healthy/unhealthy boolean (P7B.24 requirement). Ordering below is documentation
    only; no numeric rank is implied or relied upon anywhere in this module.
    """

    REGISTERED = "REGISTERED"
    TRUSTED_PENDING_CONTACT = "TRUSTED_PENDING_CONTACT"
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    DRAINING = "DRAINING"
    UNAVAILABLE_STALE = "UNAVAILABLE_STALE"
    PARTITIONED_UNCERTAIN = "PARTITIONED_UNCERTAIN"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class SiteHeartbeat:
    """
    One liveness signal from a site. `fencing_epoch_seen` is the site's own last-known
    fencing epoch (e.g. from its most recent SiteAssignment) -- carried so a heartbeat
    from a REPLACED, superseded site generation can be detected and rejected ("old site
    returns" / ABA protection) without ever granting that heartbeat any ownership
    authority: heartbeats never grant ownership, regardless of the epoch they carry
    (P7B Group-3 permanent law).
    """

    site_id: str
    sequence: int
    reported_health: SiteHealthState
    sent_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    fencing_epoch_seen: int = 0
    reported_capacity: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))
    runtime_version: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.site_id or not self.site_id.strip():
            raise SiteCoordinationError("SiteHeartbeat.site_id must be non-empty.")
        if self.sequence < 0:
            raise SiteCoordinationError("SiteHeartbeat.sequence must be >= 0.")
        if self.fencing_epoch_seen < 0:
            raise SiteCoordinationError("SiteHeartbeat.fencing_epoch_seen must be >= 0.")
        if not isinstance(self.reported_capacity, MappingProxyType):
            object.__setattr__(self, "reported_capacity", MappingProxyType(dict(self.reported_capacity)))


@dataclass(frozen=True)
class SiteCoordinationSnapshot:
    """
    Explainable coordination snapshot -- every field is traceable directly to either
    SiteRegistry state or this module's own heartbeat bookkeeping (`reasons` names which);
    never a fabricated narrative (P7B.33 discipline applied here at the source).
    """

    site_id: str
    trust_state: SiteTrustState
    lifecycle_state: SiteLifecycleState
    tenant_binding: Optional[str]
    last_heartbeat_sequence: Optional[int]
    last_heartbeat_age_seconds: Optional[float]
    last_reported_health: Optional[SiteHealthState]
    current_fencing_epoch: int
    view: CoordinationView
    reasons: Tuple[str, ...] = field(default_factory=tuple)
