"""
akaalEngine.fabric.worker_fabric.scaling
============================================
P7B.22 -- Elastic Worker Fabric: scale-out/scale-in signal aggregation.

Pure, side-effect-free recommendation logic: given a snapshot of WorkerNode states and a
backlog count, recommends SCALE_OUT / SCALE_IN / HOLD. This module NEVER itself creates
or destroys infrastructure (that is Campaign D's Kubernetes/Terraform layer's job, acting
on this recommendation) and never trusts a single worker's self-reported metrics as
global truth -- the recommendation is always computed from the AGGREGATE of all workers
the caller supplies, and a caller who passes a suspiciously-dominant single worker's
metrics as if they were the whole fleet is a caller bug this module cannot detect (fleet-
membership trust is `WorkerRegistry`'s job, upstream of this module).

SCALING NEVER CHANGES MIGRATION CORRECTNESS. Nothing in this module writes to, reads
from, or has any opinion about checkpoint/CDC/transaction state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence, Tuple

from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState


class ScaleAction(str, Enum):
    SCALE_OUT = "SCALE_OUT"
    SCALE_IN = "SCALE_IN"
    HOLD = "HOLD"


class ScalingPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ScalingRecommendation:
    action: ScaleAction
    reasons: Tuple[str, ...]
    active_worker_count: int
    idle_worker_count: int
    busy_worker_count: int
    backlog: int


def recommend_scale_action(
    workers: Sequence[WorkerNode],
    *,
    queued_assignments: int,
    max_backlog_per_worker: float = 2.0,
    min_idle_workers: int = 1,
    max_idle_workers: int = 5,
    min_worker_floor: int = 0,
) -> ScalingRecommendation:
    if queued_assignments < 0:
        raise ScalingPolicyError("queued_assignments must be >= 0.")
    if max_backlog_per_worker <= 0:
        raise ScalingPolicyError("max_backlog_per_worker must be > 0.")

    active = [w for w in workers if w.is_active()]
    idle = [w for w in active if w.state == WorkerState.IDLE]
    busy = [w for w in active if w.state == WorkerState.BUSY]

    reasons = []
    active_count = len(active)

    if active_count == 0 and queued_assignments > 0:
        reasons.append("zero active workers with a non-empty backlog")
        return ScalingRecommendation(ScaleAction.SCALE_OUT, tuple(reasons), 0, 0, 0, queued_assignments)

    backlog_ratio = (queued_assignments / active_count) if active_count > 0 else float("inf") if queued_assignments > 0 else 0.0

    if backlog_ratio > max_backlog_per_worker:
        reasons.append(f"backlog_ratio {backlog_ratio:.2f} exceeds max_backlog_per_worker {max_backlog_per_worker}")
        return ScalingRecommendation(ScaleAction.SCALE_OUT, tuple(reasons), active_count, len(idle), len(busy), queued_assignments)

    if active_count > 0 and len(idle) < min_idle_workers:
        reasons.append(f"idle_worker_count {len(idle)} below min_idle_workers {min_idle_workers}")
        return ScalingRecommendation(ScaleAction.SCALE_OUT, tuple(reasons), active_count, len(idle), len(busy), queued_assignments)

    if len(idle) > max_idle_workers and (active_count - 1) >= min_worker_floor:
        reasons.append(f"idle_worker_count {len(idle)} exceeds max_idle_workers {max_idle_workers}; safe to drain one")
        return ScalingRecommendation(ScaleAction.SCALE_IN, tuple(reasons), active_count, len(idle), len(busy), queued_assignments)

    reasons.append("within configured backlog/idle thresholds")
    return ScalingRecommendation(ScaleAction.HOLD, tuple(reasons), active_count, len(idle), len(busy), queued_assignments)
