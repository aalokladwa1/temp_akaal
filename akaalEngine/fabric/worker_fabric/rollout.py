"""
akaalEngine.fabric.worker_fabric.rollout
============================================
P7B.23 -- Self-Healing & Rolling Operations: rolling-upgrade BATCH PLANNING.

The replay-safety core of P7B.23 already lives in `worker_fabric.registry` (fencing-epoch
monotonicity via `register`/`replace_worker`, revoked-worker-cannot-heartbeat-back-to-
life) -- this module adds the piece that sits above that: given a pool of workers at an
OLD runtime_version and a target NEW version, compute a rollout batch plan that never
drains more than `max_unavailable` at once, while the registry-level fencing guarantees
below remain what actually PREVENTS unsafe overlap:

    KUBERNETES/PROCESS RESTART != MIGRATION RECOVERY.
    OLD/NEW RUNTIME OVERLAP DURING ROLLOUT IS EXPECTED AND SAFE precisely BECAUSE fencing
    (registry.py) -- not this module -- ensures a stale/old worker can never resume
    authoritative execution beyond what the canonical runtime's checkpoint/fencing state
    allows. This module never itself decides "is it safe for old-version worker X to keep
    running" -- that remains the canonical runtime.

This module is pure planning: it recommends which OLD-version workers to drain in this
batch; it performs no I/O and does not call replace_worker itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence, Tuple

from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState


class RolloutPlanningError(ValueError):
    pass


@dataclass(frozen=True)
class RolloutBatchPlan:
    target_version: str
    drain_worker_ids: Tuple[str, ...]
    remaining_old_version_count: int
    reasons: Tuple[str, ...] = field(default_factory=tuple)

    def is_complete(self) -> bool:
        return self.remaining_old_version_count == 0 and not self.drain_worker_ids


def plan_rollout_batch(
    workers: Sequence[WorkerNode],
    *,
    target_version: str,
    max_unavailable: int,
    min_available: int = 0,
) -> RolloutBatchPlan:
    """
    Selects up to `max_unavailable` OLD-version (runtime_version != target_version)
    ACTIVE workers to drain in this batch, never draining below `min_available` total
    active workers (old + new combined) at once. Deterministic selection: lowest
    fencing_epoch first (oldest generation), same tiebreak discipline as
    `k8s_runtime.crd.reconcile_worker_pool`'s scale-in selection.

    Version mismatch is expected mid-rollout (old and new versions legitimately coexist)
    -- this function's whole purpose is managing that overlap safely, never treating it
    as an error by itself. A caller wanting to BLOCK an incompatible old version from
    receiving new work does so via `akaalEngine.fabric.placement.capability`'s existing
    capability-matching (e.g. requiring the new runtime_version as a capability string),
    not via this module.
    """
    if not target_version or not target_version.strip():
        raise RolloutPlanningError("target_version must be non-empty.")
    if max_unavailable < 1:
        raise RolloutPlanningError("max_unavailable must be >= 1.")
    if min_available < 0:
        raise RolloutPlanningError("min_available must be >= 0.")

    active = [w for w in workers if w.is_active()]
    old_active = [w for w in active if w.runtime_version != target_version]
    total_active = len(active)

    if not old_active:
        return RolloutBatchPlan(target_version=target_version, drain_worker_ids=(), remaining_old_version_count=0,
                                 reasons=("rollout already complete -- no old-version active workers remain",))

    max_drainable_without_breaching_floor = max(0, total_active - min_available)
    batch_size = min(max_unavailable, len(old_active), max_drainable_without_breaching_floor)

    if batch_size == 0:
        return RolloutBatchPlan(target_version=target_version, drain_worker_ids=(), remaining_old_version_count=len(old_active),
                                 reasons=(f"cannot drain any worker without breaching min_available={min_available} "
                                          f"(total_active={total_active})",))

    selected = sorted(old_active, key=lambda w: (w.fencing_epoch, w.worker_id))[:batch_size]
    return RolloutBatchPlan(
        target_version=target_version,
        drain_worker_ids=tuple(w.worker_id for w in selected),
        remaining_old_version_count=len(old_active) - len(selected),
        reasons=(f"draining {len(selected)} of {len(old_active)} old-version worker(s) this batch "
                  f"(max_unavailable={max_unavailable}, min_available={min_available})",),
    )
