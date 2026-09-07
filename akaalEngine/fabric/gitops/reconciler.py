"""
akaalEngine.fabric.gitops.reconciler
========================================
P7B.30 -- GitOps & Fleet Lifecycle reconciliation.

Compares a `FleetDesiredState` (P7B.30) against ACTUAL fleet state read from the
UNMODIFIED P7B.22 `WorkerRegistry` -- this module makes no placement, ownership, or
migration-lifecycle decision, and it never writes anything back into WorkerRegistry
itself (applying a reconciliation plan, e.g. via `akaalEngine.fabric.worker_fabric.rollout.
plan_rollout_batch`, remains the caller's explicit, separate action). `reconcile_fleet_state`
only ever ANSWERS "what is the current relationship between desired and actual", never
"make it so".

Version/plugin compatibility is judged EXCLUSIVELY by the caller-supplied
`compatibility_callback` (in production, backed by P7A's real connector/plugin
certification truth) -- this module never itself declares a runtime version compatible
merely because a `FleetDesiredState` requests it (P7B.30 law: "fleet management cannot
declare a plugin capable merely because it is installed").
"""

from __future__ import annotations

from typing import Callable, List, Optional

from akaalEngine.fabric.gitops.models import FleetDesiredState, ReconciliationReport, ReconciliationState
from akaalEngine.fabric.worker_fabric.models import WorkerNode


def reconcile_fleet_state(
    desired: FleetDesiredState,
    actual_workers: List[WorkerNode],
    *,
    compatibility_callback: Optional[Callable[[str], bool]] = None,
) -> ReconciliationReport:
    if compatibility_callback is not None and not compatibility_callback(desired.target_runtime_version):
        return ReconciliationReport(
            revision_id=desired.revision_id, state=ReconciliationState.INCOMPATIBLE,
            active_worker_count=len(actual_workers), at_target_version_count=0, other_version_count=0,
            reasons=(f"target_runtime_version {desired.target_runtime_version!r} rejected by "
                     f"compatibility_callback; refusing to plan any reconciliation toward it",),
        )

    active = [w for w in actual_workers if w.is_active()]
    at_target = [w for w in active if w.runtime_version == desired.target_runtime_version]
    other = [w for w in active if w.runtime_version != desired.target_runtime_version]

    reasons = [
        f"active={len(active)}, at_target_version={len(at_target)}, other_version={len(other)}, "
        f"target_pool_size={desired.target_worker_pool_size}"
    ]

    if not active:
        state = ReconciliationState.PENDING if desired.target_worker_pool_size > 0 else ReconciliationState.IN_SYNC
        reasons.append("no active workers registered yet" if state == ReconciliationState.PENDING else "target pool size is zero and no active workers exist")
    elif at_target and other:
        state = ReconciliationState.PARTIALLY_APPLIED
        reasons.append("mixed old/new runtime_version workers -- rollout in progress, not itself a failure")
    elif other and not at_target:
        state = ReconciliationState.DRIFTED
        reasons.append("zero workers at target_runtime_version; rollout has not begun or has stalled")
    elif len(active) != desired.target_worker_pool_size:
        state = ReconciliationState.DRIFTED
        reasons.append(f"active worker count {len(active)} does not match target_worker_pool_size {desired.target_worker_pool_size}")
    else:
        state = ReconciliationState.IN_SYNC

    return ReconciliationReport(
        revision_id=desired.revision_id, state=state,
        active_worker_count=len(active), at_target_version_count=len(at_target), other_version_count=len(other),
        reasons=tuple(reasons),
    )
