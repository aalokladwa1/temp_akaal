"""
akaalEngine.fabric.telemetry_integration
============================================
P7B.32 -- Fabric Observability.

Builds real, structured telemetry payloads for Group-3 (and composed Group-1/Group-2)
Fabric events, for callers to hand to the EXISTING canonical
akaalEngine.telemetry.api.TelemetryAuthority (record_counter/set_gauge/record_event) --
this module creates NO second telemetry/metrics/event authority, and does not itself hold
a TelemetryAuthority instance (that remains the caller's/production wiring's
responsibility, exactly like akaalEngine.fabric.evidence does for Evidence #12).

TELEMETRY != EXECUTION TRUTH (P7B Group-3 law): every function here is a pure builder; it
performs no I/O, and nothing in this module's own correctness gates any Fabric decision --
a caller who never calls TelemetryAuthority at all still gets fully correct site
coordination/ownership/failover/fleet behavior. Proven structurally in
tests/unit/engine_fabric/test_p7b32_fabric_observability.py::
test_no_decision_module_imports_telemetry_integration: none of the P7B.24-31 decision
modules import this one.

Correlation dimensions carried here (Tenant/Site/Worker/Lease/Fencing generation/
Correlation ID, per Section 32/16 of the directive) are exactly that -- correlation, never
identity or authorization (P7B Group-3 law: "Correlation != identity"). Nothing here
accepts or emits secret/token/credential material -- every parameter is an
identifier/enum-string/count/reason, enforced structurally by the function signatures
themselves (see the hostile test verifying this).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple


def site_coordination_labels(site_id: str, tenant_id: str, coordination_view: str) -> Dict[str, str]:
    return {"site_id": site_id, "tenant_id": tenant_id, "coordination_view": coordination_view}


def heartbeat_outcome_event(*, site_id: str, accepted: bool, view: Optional[str], reason: Optional[str]) -> Dict[str, Any]:
    return {
        "event_type": "fabric.site_coordination.heartbeat",
        "site_id": site_id, "accepted": accepted, "coordination_view": view, "reason": reason,
    }


def ownership_event(
    *, event_type: str, ownership_key: str, tenant_id: str, site_id: str, worker_id: str,
    fencing_generation: int, correlation_id: str, outcome: str,
) -> Dict[str, Any]:
    """
    `event_type` is one of: 'fabric.ownership.acquired', 'fabric.ownership.renewed',
    'fabric.ownership.expired', 'fabric.ownership.transferred', 'fabric.ownership.fenced',
    'fabric.ownership.released', 'fabric.ownership.conflict_rejected'.
    """
    return {
        "event_type": event_type, "ownership_key": ownership_key, "tenant_id": tenant_id,
        "site_id": site_id, "worker_id": worker_id, "fencing_generation": fencing_generation,
        "correlation_id": correlation_id, "outcome": outcome,
    }


def failover_event(
    *, outcome: str, old_ownership_key: str, old_site_id: Optional[str],
    new_site_id: Optional[str], reasons: Tuple[str, ...],
) -> Dict[str, Any]:
    return {
        "event_type": "fabric.failover.attempted", "outcome": outcome,
        "old_ownership_key": old_ownership_key, "old_site_id": old_site_id,
        "new_site_id": new_site_id, "reasons": list(reasons),
    }


def region_health_labels(region: str, state: str) -> Dict[str, str]:
    return {"region": region, "state": state}


def cloud_health_labels(environment_type: str, state: str) -> Dict[str, str]:
    return {"environment_type": environment_type, "state": state}


def fleet_reconciliation_event(*, revision_id: str, state: str, active_worker_count: int) -> Dict[str, Any]:
    return {
        "event_type": "fabric.gitops.reconciliation", "revision_id": revision_id,
        "state": state, "active_worker_count": active_worker_count,
    }


def fleet_rollout_event(*, target_version: str, drained_worker_ids: Tuple[str, ...], remaining_old_version_count: int) -> Dict[str, Any]:
    return {
        "event_type": "fabric.fleet.rollout_batch", "target_version": target_version,
        "drained_worker_count": len(drained_worker_ids), "remaining_old_version_count": remaining_old_version_count,
    }
