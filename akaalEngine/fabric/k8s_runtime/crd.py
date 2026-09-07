"""
akaalEngine.fabric.k8s_runtime.crd
======================================
P7B.19 -- AKAAL Kubernetes Operator & CRDs: the smallest CRD schema + reconciliation
logic actually needed, not a full controller-runtime framework (none is installed in
this environment, and none is required to prove the reconciliation DECISION logic, which
is what this module owns).

CRD OWNERSHIP BOUNDARY (absolute, structurally enforced by field absence, not by
convention -- exactly like pod_spec.py's privileged/hostNetwork omission):

    `AkaalWorkerPoolSpec` has NO field for: a Migration, an ExecutionPlan, a plan
    fingerprint, a checkpoint, a CDC offset, a validation result, an approval decision,
    canonical authorization, or any secret/credential value. It is infrastructure-only:
    pool identity, desired replica count, worker image/version, and resource sizing
    references. A caller who wants to bind a worker pool to a specific migration/plan
    does so via `assignment_reference` -- an opaque fingerprint/identity STRING, never an
    embedded copy of plan truth.

RECONCILIATION BOUNDARY: `reconcile_worker_pool` is PURE DECISION LOGIC -- given a
desired spec and the currently-observed WorkerNode set, it computes what SHOULD happen
(scale out N, scale in these worker_ids) and returns that as data. It performs NO I/O,
calls no Kubernetes API, and mutates nothing. A real operator's reconcile loop (out of
this environment's local-proof reach -- no controller-runtime/kopf dependency installed)
would call this function and then act on its output through the real WorkerRegistry
(P7B.22) and k8s_runtime.pod_spec (P7B.18) -- never re-deciding placement/authorization
itself, and never treating "reconciliation ran again" as authorization to replay
physical migration work (idempotent reconciliation is a Kubernetes-infrastructure
concern; migration replay safety remains the canonical runtime's fencing/checkpoint
authority, wholly outside this module).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple

from akaalEngine.fabric.k8s_runtime.pod_spec import ResourceRequirements
from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState


class CRDValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AkaalWorkerPoolSpec:
    """The AKAAL Kubernetes Operator's only CRD spec shape. See module docstring for the
    exact, structurally-enforced ownership boundary."""
    pool_id: str
    site_id: str
    tenant_id: str
    desired_replicas: int
    image: str
    runtime_version: str
    resources: ResourceRequirements
    # Opaque reference/fingerprint only -- never embedded plan/migration truth.
    assignment_reference: Optional[str] = None

    def __post_init__(self) -> None:
        for name in ("pool_id", "site_id", "tenant_id", "image", "runtime_version"):
            if not getattr(self, name) or not getattr(self, name).strip():
                raise CRDValidationError(f"AkaalWorkerPoolSpec.{name} must be non-empty.")
        if self.desired_replicas < 0:
            raise CRDValidationError("AkaalWorkerPoolSpec.desired_replicas must be >= 0.")


@dataclass(frozen=True)
class ReconciliationAction:
    kind: str  # "SCALE_OUT" | "SCALE_IN" | "NOOP"
    worker_ids: Tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class ReconciliationPlan:
    pool_id: str
    actions: Tuple[ReconciliationAction, ...]

    def is_noop(self) -> bool:
        return all(a.kind == "NOOP" for a in self.actions) if self.actions else True


def reconcile_worker_pool(
    desired: AkaalWorkerPoolSpec,
    observed_workers: Sequence[WorkerNode],
) -> ReconciliationPlan:
    """
    Pure diff: desired.desired_replicas vs. count of currently-ACTIVE (IDLE/BUSY/
    DRAINING) observed workers for (desired.tenant_id, desired.site_id). REVOKED/
    UNHEALTHY/STALE workers never count toward "currently satisfies desired replicas" --
    a pool showing N healthy-looking-but-actually-revoked workers must still be
    reconciled as under-provisioned, never silently accepted as satisfied.

    Idempotent: calling this again with the same (desired, observed_workers) always
    produces the same plan (deterministic, no hidden state) -- repeated/duplicate
    reconciliation calls are safe by construction, which is exactly the property that
    stops "operator retried reconciliation" from ever being mistaken for authorization to
    duplicate physical execution (this function has no way to cause physical execution at
    all).
    """
    relevant = [w for w in observed_workers if w.tenant_id == desired.tenant_id and w.site_id == desired.site_id]
    healthy_active = [w for w in relevant if w.is_active() and w.state != WorkerState.STALE]
    current_count = len(healthy_active)

    if current_count == desired.desired_replicas:
        return ReconciliationPlan(pool_id=desired.pool_id, actions=(
            ReconciliationAction(kind="NOOP", worker_ids=(), reason=f"current active worker count {current_count} matches desired {desired.desired_replicas}"),
        ))

    if current_count < desired.desired_replicas:
        deficit = desired.desired_replicas - current_count
        return ReconciliationPlan(pool_id=desired.pool_id, actions=(
            ReconciliationAction(kind="SCALE_OUT", worker_ids=(), reason=f"deficit of {deficit} worker(s) (current {current_count}, desired {desired.desired_replicas})"),
        ))

    surplus = current_count - desired.desired_replicas
    # Deterministic selection: drain the surplus workers with the LOWEST fencing_epoch
    # first (oldest generation), never an arbitrary/unstable order.
    drain_candidates = sorted(healthy_active, key=lambda w: (w.fencing_epoch, w.worker_id))[:surplus]
    return ReconciliationPlan(pool_id=desired.pool_id, actions=(
        ReconciliationAction(
            kind="SCALE_IN", worker_ids=tuple(w.worker_id for w in drain_candidates),
            reason=f"surplus of {surplus} worker(s) (current {current_count}, desired {desired.desired_replicas})",
        ),
    ))
