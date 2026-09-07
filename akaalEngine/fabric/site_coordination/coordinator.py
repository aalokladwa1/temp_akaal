"""
akaalEngine.fabric.site_coordination.coordinator
====================================================
P7B.24 -- Distributed Site Coordination.

SiteCoordinator adds heartbeat/liveness tracking and a truthful, multi-valued
coordination view ON TOP OF the existing P7B.5 SiteRegistry. It introduces NO new trust,
tenant-binding, or fencing decision authority: every trust/tenant/fencing question is
delegated to SiteRegistry, the identical composition discipline
akaalEngine.fabric.remote_execution.control_plane.RemoteExecutionControlPlane already
uses for assignment issuance.

Permanent invariants enforced here (P7B Group-3 laws, restated at the point they are
mechanically enforced):
    * Heartbeat != ownership -- record_heartbeat NEVER mutates SiteRegistry's
      trust_state, tenant_binding, or fencing epoch.
    * A revoked site cannot heartbeat itself back into trust.
    * A stale/superseded site generation cannot regain liveness credit merely by
      resending a heartbeat carrying an old fencing epoch.
    * Unknown != available, unknown != authorized -- PARTITIONED_UNCERTAIN and
      UNAVAILABLE_STALE are never coerced into AVAILABLE.

Heartbeat liveness state is intentionally NOT durably persisted: it is naturally
re-established by the next heartbeat after any restart, and nothing safety-relevant is
lost by that -- the only state that MUST survive restart (trust/tenant/fencing epoch)
already does, via SiteRegistry/FabricDurabilityStore (P7B Group-1, unmodified here). See
tests/unit/engine_fabric/test_p7b24_site_coordination.py::
test_restart_reconstructs_registry_without_resurrecting_stale_epoch for the proof this
composition is safe across a fresh-process boundary.

Site disappearance handling (P7B.24 Section 8 / P7B.29): `stale_site_ids` is PURE
DETECTION. It never itself revokes, reassigns, or fences a site -- callers (the
forthcoming P7B.25 ownership layer and P7B.28 failure/recovery pathway) must resolve
ownership/lease/fencing state before issuing any replacement work. This module has no
opinion on what should happen to a stale site's work, only on whether the site itself is
currently answerable.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from akaalEngine.fabric.execution_site.models import SiteHealthState, SiteLifecycleState, SiteTrustState
from akaalEngine.fabric.execution_site.registry import SiteRegistry
from akaalEngine.fabric.site_coordination.models import (
    CoordinationView,
    HeartbeatRejectedError,
    SiteCoordinationSnapshot,
    SiteHeartbeat,
)


class _LivenessRecord:
    __slots__ = ("last_sequence", "last_monotonic", "last_fencing_epoch_seen", "last_health")

    def __init__(self) -> None:
        self.last_sequence: int = -1
        self.last_monotonic: float = 0.0
        self.last_fencing_epoch_seen: int = 0
        self.last_health: Optional[SiteHealthState] = None


class SiteCoordinator:
    def __init__(self, site_registry: SiteRegistry, staleness_threshold_seconds: float = 45.0) -> None:
        if staleness_threshold_seconds <= 0:
            raise ValueError("staleness_threshold_seconds must be > 0.")
        self.site_registry = site_registry
        self.staleness_threshold_seconds = staleness_threshold_seconds
        self._lock = threading.RLock()
        self._liveness: Dict[str, _LivenessRecord] = {}

    # ------------------------------------------------------------------
    # Heartbeat ingestion -- liveness bookkeeping only, never a trust/ownership grant
    # ------------------------------------------------------------------

    def record_heartbeat(self, heartbeat: SiteHeartbeat) -> SiteCoordinationSnapshot:
        with self._lock:
            site = self.site_registry.get(heartbeat.site_id)  # UnknownSiteError propagates -- fail safe, never fabricates a site

            if site.trust_state == SiteTrustState.REVOKED:
                raise HeartbeatRejectedError(
                    f"Site {heartbeat.site_id!r} is REVOKED; a revoked site cannot "
                    f"heartbeat itself back into trust."
                )

            current_epoch = self.site_registry.current_fencing_epoch(heartbeat.site_id)
            if heartbeat.fencing_epoch_seen and heartbeat.fencing_epoch_seen < current_epoch:
                raise HeartbeatRejectedError(
                    f"Heartbeat from site {heartbeat.site_id!r} carries "
                    f"fencing_epoch_seen={heartbeat.fencing_epoch_seen}, below the current "
                    f"fencing epoch {current_epoch}; refusing to record liveness for a "
                    f"superseded site generation (old site returning after replacement)."
                )

            record = self._liveness.setdefault(heartbeat.site_id, _LivenessRecord())
            if heartbeat.sequence <= record.last_sequence:
                raise HeartbeatRejectedError(
                    f"Heartbeat sequence {heartbeat.sequence} for site "
                    f"{heartbeat.site_id!r} does not exceed last recorded sequence "
                    f"{record.last_sequence}; refusing replayed/out-of-order heartbeat."
                )

            record.last_sequence = heartbeat.sequence
            record.last_monotonic = time.monotonic()
            record.last_fencing_epoch_seen = heartbeat.fencing_epoch_seen
            record.last_health = heartbeat.reported_health

            return self._snapshot(heartbeat.site_id)

    # ------------------------------------------------------------------
    # Read-only views
    # ------------------------------------------------------------------

    def snapshot(self, site_id: str) -> SiteCoordinationSnapshot:
        with self._lock:
            return self._snapshot(site_id)

    def _snapshot(self, site_id: str) -> SiteCoordinationSnapshot:
        site = self.site_registry.get(site_id)
        record = self._liveness.get(site_id)
        current_epoch = self.site_registry.current_fencing_epoch(site_id)
        reasons: List[str] = []

        if site.trust_state == SiteTrustState.REVOKED:
            view = CoordinationView.REVOKED
            reasons.append("trust_state=REVOKED")
        elif site.lifecycle_state == SiteLifecycleState.DRAINING:
            view = CoordinationView.DRAINING
            reasons.append("lifecycle_state=DRAINING")
        elif record is None:
            if site.trust_state == SiteTrustState.TRUSTED:
                view = CoordinationView.TRUSTED_PENDING_CONTACT
                reasons.append("trusted but no heartbeat has ever been received")
            else:
                view = CoordinationView.REGISTERED
                reasons.append(f"trust_state={site.trust_state.value}, no heartbeat received")
        else:
            age = time.monotonic() - record.last_monotonic
            if age > self.staleness_threshold_seconds:
                view = CoordinationView.UNAVAILABLE_STALE
                reasons.append(
                    f"last heartbeat age {age:.1f}s exceeds staleness threshold "
                    f"{self.staleness_threshold_seconds}s"
                )
            elif site.trust_state != SiteTrustState.TRUSTED or site.tenant_binding is None:
                view = CoordinationView.PARTITIONED_UNCERTAIN
                reasons.append(
                    f"heartbeat is fresh but trust_state={site.trust_state.value}/"
                    f"tenant_binding={site.tenant_binding!r} is not execution-ready; "
                    f"a fresh heartbeat from an unauthorized site is never upgraded to AVAILABLE"
                )
            elif record.last_health in (SiteHealthState.DEGRADED, SiteHealthState.UNREACHABLE):
                view = CoordinationView.DEGRADED
                reasons.append(f"reported_health={record.last_health.value}")
            else:
                view = CoordinationView.AVAILABLE
                reasons.append("fresh heartbeat, trusted, tenant-bound, active, healthy")

        return SiteCoordinationSnapshot(
            site_id=site_id,
            trust_state=site.trust_state,
            lifecycle_state=site.lifecycle_state,
            tenant_binding=site.tenant_binding,
            last_heartbeat_sequence=(record.last_sequence if record and record.last_sequence >= 0 else None),
            last_heartbeat_age_seconds=(time.monotonic() - record.last_monotonic) if record else None,
            last_reported_health=(record.last_health if record else None),
            current_fencing_epoch=current_epoch,
            view=view,
            reasons=tuple(reasons),
        )

    def stale_site_ids(self) -> List[str]:
        """
        Pure detection -- returns site_ids whose current CoordinationView is
        UNAVAILABLE_STALE or PARTITIONED_UNCERTAIN. Callers (P7B.28/29 failure handling)
        MUST still resolve ownership/lease/fencing state before issuing any replacement
        work; this method never itself triggers failover.
        """
        with self._lock:
            result: List[str] = []
            for site in self.site_registry.list_sites():
                snap = self._snapshot(site.site_id)
                if snap.view in (CoordinationView.UNAVAILABLE_STALE, CoordinationView.PARTITIONED_UNCERTAIN):
                    result.append(site.site_id)
            return result

    def forget_liveness(self, site_id: str) -> None:
        """
        Explicit, caller-driven liveness reset (e.g. after a confirmed site replacement)
        -- distinct from a heartbeat, and distinct from any trust/tenant mutation. Does
        NOT touch SiteRegistry. Safe to call even if no liveness record exists.
        """
        with self._lock:
            self._liveness.pop(site_id, None)
