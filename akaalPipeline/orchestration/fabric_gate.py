"""
akaalPipeline.orchestration.fabric_gate
===========================================
The ONLY integration seam connecting `akaalPipeline.execution.coordinator.
PlanExecutionCoordinator` (the canonical, existing, single Pipeline orchestration
authority -- unchanged in identity, still authoritative) to P7B Group-2 (Campaign C/D)
distributed placement. This module is NOT a second Pipeline, planner, ExecutionPlan,
runtime, executor, scheduler, or lifecycle authority -- it is pure applicability-
determination + a small binding store, called from exactly two points inside
`PlanExecutionCoordinator` (`materialize_plan_execution`, `advance_plan_execution`).

APPLICABILITY LAW (the caller cannot decide this): whether a plan requires distributed
Group-2 placement is read from `ExecutionPlan.configuration["fabric_placement"]["required"]`
-- part of the plan's OWN immutable, canonically-fingerprinted `configuration` mapping
(`akaalPipeline.orchestration.plans.ExecutionPlan.fingerprint`, computed once at
`ExecutionPlan.create()` and never mutable afterward). This is deliberately NOT a runtime
parameter any caller of `materialize_plan_execution`/`advance_plan_execution` can pass or
override -- by the time either method runs, the plan (and therefore its fabric
applicability) was already fixed, tamper-evident, and unrelated to whatever a dispatch-
time caller might prefer. There is no existing dormant flag anywhere in akaalPipeline for
this (confirmed by forensic search across the whole package); this is the smallest new,
explicit, canonical signal -- carried on the plan itself, not invented as a side channel.

FAIL-CLOSED LAW: `FabricPlacementBindingStore` never fabricates a default binding for an
execution_id it doesn't have one for -- `require()` always raises. There is no code path
in this module that treats "no binding found" as "fabric placement not required" for a
plan that IS marked as requiring it.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, List, Mapping, Optional

from akaalEngine.fabric.execution_site.models import ExecutionSite
from akaalEngine.fabric.execution_site.registry import SiteAuthorizationCallback, SiteRegistry
from akaalEngine.fabric.locality.models import LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.ownership.manager import OwnershipManager
from akaalEngine.fabric.placement.binding import PlacementDecision
from akaalEngine.fabric.placement.policy import PlacementAuthorizationCallback
from akaalEngine.fabric.placement.residency import ResidencyPolicy
from akaalEngine.fabric.remote_execution.control_plane import RemoteExecutionControlPlane
from akaalEngine.fabric.topology.graph import TopologyGraph
from akaalEngine.fabric.worker_fabric.models import WorkerNode
from akaalEngine.fabric.worker_fabric.registry import WorkerRegistry

FABRIC_PLACEMENT_CONFIG_KEY = "fabric_placement"


class FabricGateError(RuntimeError):
    pass


class NoFabricPlacementBindingError(FabricGateError):
    """Raised when a plan requires fabric placement but no binding has been established
    for this execution_id (never fabricated). Reaching this means either the caller
    bypassed `materialize_plan_execution`'s gate entirely (a defect this module's own
    tests attempt to prove impossible through the coordinator's own public surface), or
    an in-memory `FabricPlacementBindingStore` lost state across a process restart -- in
    either case, fail closed and require a fresh placement cycle, never continue
    unprotected."""


def plan_requires_fabric_placement(plan: Any) -> bool:
    """Reads the trusted, plan-embedded (never dispatch-time-overridable) applicability
    signal. Returns False for any plan whose `configuration` does not declare it -- the
    default is "does not require Group-2 placement", preserving every existing non-
    fabric (local/on-prem/VM/bare-metal) execution path exactly as it already works."""
    cfg = plan.configuration.get(FABRIC_PLACEMENT_CONFIG_KEY) if hasattr(plan, "configuration") else None
    if not isinstance(cfg, Mapping):
        return False
    return bool(cfg.get("required", False))


def fabric_placement_config(plan: Any) -> Mapping[str, Any]:
    cfg = plan.configuration.get(FABRIC_PLACEMENT_CONFIG_KEY) if hasattr(plan, "configuration") else None
    return cfg if isinstance(cfg, Mapping) else {}


@dataclass(frozen=True)
class FabricPlacementBinding:
    """Immutable record of exactly what Group-2 decided for one plan execution, plus the
    worker reserved for it -- kept together so both remain consistently revalidatable."""
    decision: PlacementDecision
    site: ExecutionSite
    worker: WorkerNode


class FabricPlacementBindingStore:
    """Thread-safe store of `execution_id -> FabricPlacementBinding`. Bookkeeping only --
    exactly like every other fabric registry in this codebase, storing this binding never
    itself grants trust or authorization; `PlacementDecision`/`WorkerNode` validity is
    always re-verified live (topology freshness, worker state/fencing) at the point of
    use, never assumed still-true merely because a binding is present here."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bindings: dict[str, FabricPlacementBinding] = {}

    def save(self, execution_id: str, binding: FabricPlacementBinding) -> None:
        if not execution_id or not execution_id.strip():
            raise FabricGateError("FabricPlacementBindingStore.save requires a non-empty execution_id.")
        with self._lock:
            self._bindings[execution_id] = binding

    def try_get(self, execution_id: str) -> Optional[FabricPlacementBinding]:
        with self._lock:
            return self._bindings.get(execution_id)

    def require(self, execution_id: str) -> FabricPlacementBinding:
        binding = self.try_get(execution_id)
        if binding is None:
            raise NoFabricPlacementBindingError(
                f"No FabricPlacementBinding for execution_id {execution_id!r}; this plan "
                f"requires Group-2 placement and none is bound -- refusing to dispatch."
            )
        return binding

    def release(self, execution_id: str) -> None:
        with self._lock:
            self._bindings.pop(execution_id, None)


def is_binding_stale(binding: FabricPlacementBinding, current_topology: TopologyGraph) -> bool:
    """Shared staleness check -- reuses PlacementDecision.is_stale exactly as
    `akaalEngine.fabric.placement.execution.execute_via_placement` already does, never a
    second staleness scheme."""
    return binding.decision.is_stale(current_topology_fingerprint=current_topology.fingerprint())


@dataclass
class FabricGateDependencies:
    """
    Everything `akaalPipeline.execution.coordinator.PlanExecutionCoordinator` needs to
    honor a plan's `fabric_placement.required = True` declaration. Constructed once by
    whoever wires up the coordinator (in production, `akaalPipeline.application.
    unified_caller.PipelineUnifiedCaller`) and passed in as a single, optional
    constructor argument -- NOT scattered across a dozen new coordinator constructor
    parameters, keeping the coordinator's own signature change minimal.

    Every callable here receives the trusted `PipelineActorContext` the coordinator
    already has (never re-derives tenant/workspace/project from anything else) and the
    `ExecutionPlan` itself (its `configuration["fabric_placement"]` sub-mapping carries
    the plan's own declared capability/residency requirements) -- this dataclass carries
    no tenant/plan data of its own, only the resolution functions and shared registries.

    `ownership_manager` (P7B Group-3, P7B.25) is declared here, not as a separate
    constructor argument on `PlanExecutionCoordinator` and not behind a second,
    caller-choosable "require_ownership" flag -- applicability is derived from the SAME
    canonical, plan-embedded `fabric_placement.required` signal `plan_requires_fabric_
    placement` already reads (see `PlanExecutionCoordinator._decide_and_bind_fabric_
    placement`, which raises `PipelineError(POLICY_DENIED)` if a fabric-required plan
    reaches it with `ownership_manager is None` on a coordinator that HAS
    `fabric_dependencies` configured at all -- there is no code path that silently treats
    a missing ownership_manager as "ownership not required" for a plan that already
    requires Group-2 placement). Defaults to `None` here purely so existing/unrelated
    (non-fabric, or fabric-Group-2-only test/tooling) construction of
    `FabricGateDependencies` is not forced to supply one; a REAL production deployment
    serving fabric-required plans must supply a real `OwnershipManager` or dispatch fails
    closed, deterministically, before any physical effect.
    """
    binding_store: FabricPlacementBindingStore
    topology_provider: Callable[[str], TopologyGraph]  # (tenant_id) -> TopologyGraph snapshot
    candidate_provider: Callable[[Any, Any], List[ExecutionSite]]  # (actor, plan) -> candidates
    locality_provider: Callable[[Any, Any, List[ExecutionSite]], Mapping[str, Mapping[LocalitySubjectRole, LocalityRecord]]]
    residency_policy_resolver: Callable[[str], ResidencyPolicy]  # policy_id -> ResidencyPolicy
    placement_authorization_callback: PlacementAuthorizationCallback
    worker_registry: WorkerRegistry
    site_registry: SiteRegistry
    site_authorization_callback: SiteAuthorizationCallback
    control_plane: RemoteExecutionControlPlane
    signing_key: bytes
    transport_authority_factory: Callable[[], Any]
    pod_spec_factory: Optional[Callable[[WorkerNode], Mapping[str, Any]]] = None
    ownership_manager: Optional[OwnershipManager] = None
    # P7B.34 -- optional real akaalEngine.evidence.api.EvidenceAuthority. Purely additive
    # (Evidence != authorization, P7B Group-3 law): omitting this changes nothing about
    # whether execution is permitted; it only means Group-1/Group-3 Evidence #12 artifacts
    # for this coordinator's fabric-placed dispatches are not recorded.
    evidence_authority: Optional[Any] = None
    # P7B.32 -- optional real akaalEngine.telemetry.api.TelemetryAuthority. Purely
    # additive (Telemetry != execution truth, P7B Group-3 law): omitting this changes
    # nothing about whether execution is permitted.
    telemetry_authority: Optional[Any] = None
    # P7B.33 -- optional sink receiving the real, deterministic explanation dict
    # (akaalEngine.fabric.explainability.explain_ownership_decision) for every ownership
    # decision at the production gate. EXPLANATION != AUTHORITY (P7B Group-3 law):
    # omitting this, or a raising sink, changes nothing about whether execution proceeds.
    explanation_sink: Optional[Callable[[Mapping[str, Any]], None]] = None
