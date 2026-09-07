"""akaalPipeline.execution.coordinator
====================================
Canonical durable Plan & DAG Execution Coordinator.
Owns plan execution lifecycle, DAG dependency evaluation, node readiness,
commit-before-dispatch authority, result reconciliation, and whole-plan completion.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, List, Mapping, Optional

from akaalPipeline.capabilities.bindings import BindingRegistry
from akaalPipeline.capabilities.resolver import CapabilityResolver
from akaalPipeline.contracts.enums import (
    CapabilityDimension,
    MigrationLifecycleState,
    MigrationMode,
    NodeExecutionState,
    OperationStatus,
    PlanExecutionStatus,
    SideEffectClassification,
)

from akaalPipeline.contracts.errors import (
    IPCErrorCategory,
    PipelineError,
    PipelineErrorCode,
    StaleResultError,
)
from akaalPipeline.events.audit import AuditTrailService
from akaalPipeline.events.outbox import OutboxService
from akaalPipeline.events.schemas import DomainEvent

from akaalPipeline.execution.result_reconciliation import ResultReconciler
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.service import OperationService
from akaalPipeline.orchestration.plans import (
    ExecutionPlan,
    GraphNode,
    NodeExecutionRecord,
    PlanExecutionRecord,
)
from akaalPipeline.ports.engine import EngineInvocationRequest, ExecutionPort
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork

# --- P7B Group-2 production integration (final blocker closure) ---------------------
# akaalPipeline.execution.coordinator.PlanExecutionCoordinator remains THE canonical,
# single Pipeline orchestration authority -- these imports add an integration seam, not
# a second orchestrator. See akaalPipeline.orchestration.fabric_gate module docstring
# for the applicability/binding-store contract, and
# akaalPipeline.adapters.fabric_engine_gateway for the one new ExecutionPort adapter.
from akaalPipeline.orchestration.fabric_gate import (
    FabricGateDependencies,
    FabricPlacementBinding,
    FabricPlacementBindingStore,
    NoFabricPlacementBindingError,
    fabric_placement_config,
    is_binding_stale,
    plan_requires_fabric_placement,
)


@dataclass(frozen=True)
class ExecutionOutcome:
    is_success: bool
    status: str
    error_category: Optional[IPCErrorCategory] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[Mapping[str, Any]] = None


class PlanExecutionCoordinator:
    """Canonical Pipeline authority owning complete DAG execution, node state progression,

    dependency evaluation, lease/fence authority, and truthful plan completion.
    """

    def __init__(
        self,
        capability_resolver: CapabilityResolver,
        binding_registry: BindingRegistry,
        lease_manager: LeaseManager,
        operation_service: OperationService,
        result_reconciler: ResultReconciler,
        outbox_service: OutboxService,
        audit_service: AuditTrailService,
        repository: SQLiteMigrationRepository,
        keystore: Optional[Any] = None,
        fabric_dependencies: Optional["FabricGateDependencies"] = None,
    ) -> None:
        self.capability_resolver = capability_resolver
        self.binding_registry = binding_registry
        self.lease_manager = lease_manager
        self.operation_service = operation_service
        self.result_reconciler = result_reconciler
        self.outbox_service = outbox_service
        self.audit_service = audit_service
        self.repository = repository
        self.keystore = keystore
        self.minter = None
        if keystore is not None:
            try:
                from akaalPipeline.security.execution_authorization import ExecutionAuthorizationMinter
                self.minter = ExecutionAuthorizationMinter(keystore=keystore)
            except Exception:
                pass

        # P7B Group-2 production integration: OPTIONAL. A coordinator constructed
        # without `fabric_dependencies` behaves EXACTLY as before this change for every
        # plan whose configuration does not mark `fabric_placement.required = True`
        # (every existing local/on-prem/VM/bare-metal non-fabric test and call site is
        # unaffected). A plan that DOES require fabric placement, dispatched through a
        # coordinator with no `fabric_dependencies` configured, fails closed (see
        # materialize_plan_execution) rather than silently skipping Group-2 controls.
        self.fabric_dependencies = fabric_dependencies
        self._fabric_binding_store = (
            fabric_dependencies.binding_store if fabric_dependencies is not None else FabricPlacementBindingStore()
        )
        self._fabric_data_transport_binding = None
        if fabric_dependencies is not None:
            from akaalEngine.fabric.placement.execution import PlacementExecutionError  # noqa: F401 (re-export check)
            from akaalPipeline.adapters.fabric_engine_gateway import FabricPlacementExecutionPort
            from akaalPipeline.capabilities.bindings import EngineBindingDescriptor

            fabric_port = FabricPlacementExecutionPort(
                binding_store=self._fabric_binding_store,
                topology_provider=fabric_dependencies.topology_provider,
                worker_registry=fabric_dependencies.worker_registry,
                control_plane=fabric_dependencies.control_plane,
                site_authorization_callback=fabric_dependencies.site_authorization_callback,
                signing_key=fabric_dependencies.signing_key,
                transport_authority_factory=fabric_dependencies.transport_authority_factory,
                ownership_manager=fabric_dependencies.ownership_manager,
                evidence_authority=fabric_dependencies.evidence_authority,
                telemetry_authority=fabric_dependencies.telemetry_authority,
            )
            self._fabric_data_transport_binding = EngineBindingDescriptor(
                binding_id="fabric_placement_data_transport_binding",
                engine_name="fabric_placement",
                version="1.0.0",
                port_instance=fabric_port,
                supported_capabilities={"data_transport"},
                supported_modes=set(MigrationMode),
            )

    # -------------------------------------------------------------------------
    # 1. Plan Execution Materialization
    # -------------------------------------------------------------------------

    def materialize_plan_execution(
        self,
        plan: ExecutionPlan,
        migration: MigrationAggregate,
        actor: PipelineActorContext,
        initialization_fingerprint: str,
        conn: sqlite3.Connection,
        operation_id: Optional[str] = None,
    ) -> PlanExecutionRecord:
        """Materializes durable plan execution and initial node execution states in DB."""
        # Enforce tenant/workspace/project scoping. TENANT_BOUNDARY_VIOLATION (not
        # POLICY_DENIED) is used deliberately -- see PipelineActorContext.
        # enforce_resource_scope's docstring (akaalPipeline/security/context.py) and
        # PipelineError.to_ipc_error() (akaalPipeline/contracts/errors.py): it maps to
        # the same externally observable response as a genuine NOT_FOUND, so an
        # unauthorized caller cannot learn from the error alone whether this migration
        # exists in another tenant versus not existing at all. The precise reason
        # remains available internally via this exception's own .code/.message.
        if migration.tenant_id != actor.organization_id:
            raise PipelineError(
                PipelineErrorCode.TENANT_BOUNDARY_VIOLATION,
                f"Migration {migration.migration_id!r} tenant mismatch.",
            )
        if actor.workspace_id and migration.workspace_id and actor.workspace_id != migration.workspace_id:
            raise PipelineError(
                PipelineErrorCode.TENANT_BOUNDARY_VIOLATION,
                f"Migration {migration.migration_id!r} workspace mismatch.",
            )
        if actor.project_id and migration.project_id and actor.project_id != migration.project_id:
            raise PipelineError(
                PipelineErrorCode.TENANT_BOUNDARY_VIOLATION,
                f"Migration {migration.migration_id!r} project mismatch.",
            )

        # --- P7B Group-2 mandatory placement gate -----------------------------------
        # Applicability comes ONLY from the plan's own immutable, fingerprinted
        # configuration -- never from a caller/operation_id/payload override (see
        # akaalPipeline.orchestration.fabric_gate module docstring). If this plan
        # requires distributed placement and Group-2 cannot produce a compliant one,
        # this raises HERE -- before the idempotency check below, before execution_id is
        # even generated, before any row is written to plan_executions/node_executions.
        # NO PlanExecutionRecord is created; there is nothing downstream capable of ever
        # dispatching physical work for this attempt.
        fabric_binding = None
        if plan_requires_fabric_placement(plan):
            fabric_binding = self._decide_and_bind_fabric_placement(plan=plan, migration=migration, actor=actor)

        # Check if an active execution already exists for this migration
        cur = conn.execute(
            """
            SELECT execution_id FROM plan_executions
            WHERE migration_id = ? AND status IN ('ACCEPTED', 'RUNNING', 'RECOVERING')
            ORDER BY created_at DESC LIMIT 1
            """,
            (migration.migration_id,),
        )
        row = cur.fetchone()
        if row is not None:
            if operation_id:
                conn.execute(
                    "UPDATE plan_executions SET start_operation_id = ? WHERE execution_id = ? AND (start_operation_id IS NULL OR start_operation_id = '')",
                    (operation_id, row["execution_id"]),
                )
            existing = self.get_plan_execution(row["execution_id"], conn)
            if existing is not None:
                if existing.plan_fingerprint != plan.fingerprint:
                    raise PipelineError(
                        PipelineErrorCode.POLICY_DENIED,
                        f"Active execution {existing.execution_id} plan fingerprint mismatch: expected {existing.plan_fingerprint!r}, got {plan.fingerprint!r}.",
                    )
                if initialization_fingerprint and existing.initialization_fingerprint != initialization_fingerprint:
                    raise PipelineError(
                        PipelineErrorCode.POLICY_DENIED,
                        f"Active execution {existing.execution_id} initialization fingerprint mismatch: expected {existing.initialization_fingerprint!r}, got {initialization_fingerprint!r}.",
                    )
                if fabric_binding is not None and self._fabric_binding_store.try_get(existing.execution_id) is None:
                    # This plan requires fabric placement but the idempotently-reused
                    # execution has no binding recorded (e.g. an in-memory binding
                    # store lost state across a process restart) -- fail closed rather
                    # than silently resuming as if placement were still valid; bind the
                    # freshly-decided placement now so any accompanying advance call
                    # can proceed under fresh, verified placement.
                    self._fabric_binding_store.save(existing.execution_id, fabric_binding)
                return existing


        now_str = datetime.now(timezone.utc).isoformat()
        execution_id = f"pe-{uuid.uuid4().hex}"
        if fabric_binding is not None:
            self._fabric_binding_store.save(execution_id, fabric_binding)

        plan_rec = PlanExecutionRecord(
            execution_id=execution_id,
            migration_id=migration.migration_id,
            plan_id=plan.plan_id,
            plan_fingerprint=plan.fingerprint,
            initialization_fingerprint=initialization_fingerprint,
            tenant_id=migration.tenant_id or actor.organization_id or "default-tenant",
            workspace_id=migration.workspace_id or actor.workspace_id or "default-workspace",
            project_id=migration.project_id or actor.project_id or "default-project",
            status=PlanExecutionStatus.ACCEPTED,
            created_at=now_str,
            updated_at=now_str,
            start_operation_id=operation_id,
        )

        conn.execute(
            """
            INSERT INTO plan_executions (
                execution_id, migration_id, plan_id, plan_fingerprint,
                initialization_fingerprint, tenant_id, workspace_id,
                project_id, status, start_operation_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_rec.execution_id,
                plan_rec.migration_id,
                plan_rec.plan_id,
                plan_rec.plan_fingerprint,
                plan_rec.initialization_fingerprint,
                plan_rec.tenant_id,
                plan_rec.workspace_id,
                plan_rec.project_id,
                plan_rec.status.value,
                plan_rec.start_operation_id,
                plan_rec.created_at,
                plan_rec.updated_at,
            ),
        )

        # Materialize each node execution record
        for node in plan.nodes:
            # Nodes with no unsatisfied dependencies start as READY; others BLOCKED
            init_state = (
                NodeExecutionState.READY
                if len(node.dependencies) == 0
                else NodeExecutionState.BLOCKED
            )
            node_exec_id = f"ne-{uuid.uuid4().hex}"
            conn.execute(
                """
                INSERT INTO node_executions (
                    node_execution_id, execution_id, migration_id, graph_node_id,
                    capability_contract, side_effect, state, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node_exec_id,
                    execution_id,
                    migration.migration_id,
                    node.node_id,
                    node.task.capability_contract,
                    node.task.side_effect.value,
                    init_state.value,
                    now_str,
                    now_str,
                ),
            )

        return plan_rec

    def _decide_and_bind_fabric_placement(
        self,
        *,
        plan: ExecutionPlan,
        migration: MigrationAggregate,
        actor: PipelineActorContext,
    ) -> FabricPlacementBinding:
        """
        Runs the full Campaign C pipeline (topology -> locality -> capability -> policy
        -> residency -> optimization/cost, via the unmodified
        `akaalEngine.fabric.placement.binding.decide_placement`) and Campaign D worker
        binding (`akaalEngine.fabric.placement.execution.bind_worker_for_placement`,
        unmodified) for one plan. Raises `PipelineError(POLICY_DENIED)` -- never falls
        back to the non-fabric execution path -- if Group-2 cannot produce a compliant
        placement, or if this coordinator has no `fabric_dependencies` configured at all
        (a plan declaring `fabric_placement.required=True` against an unconfigured
        coordinator is a deployment/configuration defect, not license to skip Group-2
        controls).

        Trusted tenant/workspace/project context is read EXCLUSIVELY from `actor`
        (the already-verified `PipelineActorContext`) and `migration` -- never from
        `plan.configuration`, which a plan author could otherwise use to smuggle a
        different tenant into a residency/capability decision (this is the same
        discipline `EngineInvocationRequest.tenant_id` already enforces one layer down,
        and the same discipline behind the cross-tenant-locality fix in
        `akaalEngine.fabric.placement.residency`).
        """
        from akaalEngine.fabric.placement.binding import NoCompliantPlacementError, decide_placement
        from akaalEngine.fabric.placement.capability import CapabilityRequirement
        from akaalEngine.fabric.placement.execution import bind_worker_for_placement

        deps = self.fabric_dependencies
        if deps is None:
            raise PipelineError(
                PipelineErrorCode.POLICY_DENIED,
                f"Plan {plan.plan_id!r} declares fabric_placement.required=True but this "
                f"PlanExecutionCoordinator has no fabric_dependencies configured; refusing "
                f"to execute without Group-2 placement controls (never falling back to "
                f"direct/unplaced execution).",
            )
        # P7B Group-3 (P7B.25) MANDATORY-WHEN-APPLICABLE ownership gate: applicability is
        # NOT a second, caller-choosable flag -- it derives from the exact same canonical,
        # plan-embedded `fabric_placement.required` signal that just made Group-2
        # placement mandatory above. A coordinator that has fabric_dependencies configured
        # at all (i.e. genuinely intends to serve fabric-required plans) MUST also have a
        # real OwnershipManager configured; there is no fallback that treats a missing
        # ownership_manager as "ownership not required" for a plan that already requires
        # Group-2 placement (see akaalPipeline.orchestration.fabric_gate.
        # FabricGateDependencies.ownership_manager docstring for the full rationale).
        if deps.ownership_manager is None:
            raise PipelineError(
                PipelineErrorCode.POLICY_DENIED,
                f"Plan {plan.plan_id!r} declares fabric_placement.required=True but this "
                f"PlanExecutionCoordinator's fabric_dependencies has no ownership_manager "
                f"configured; Group-3 distributed ownership is mandatory for fabric-"
                f"required execution, never optional -- refusing to execute.",
            )

        cfg = fabric_placement_config(plan)
        tenant_id = migration.tenant_id or actor.organization_id or "default-tenant"
        workspace_id = migration.workspace_id or actor.workspace_id or "default-workspace"
        project_id = migration.project_id or actor.project_id or "default-project"

        candidates = deps.candidate_provider(actor, plan)
        topology = deps.topology_provider(tenant_id)
        locality_by_site = deps.locality_provider(actor, plan, candidates)
        residency_policies = tuple(
            deps.residency_policy_resolver(policy_id) for policy_id in cfg.get("residency_policy_ids", ())
        )
        capability_requirement = CapabilityRequirement(
            required_capabilities=frozenset(cfg.get("required_capabilities", ())),
            plan_reference=plan.plan_id,
        )
        # Monotonic-enough for this integration seam (nanosecond wall clock); the
        # SiteRegistry/WorkerRegistry fencing-epoch ladders this ultimately feeds are the
        # actual replay-protection authority (P7B.5/P7B.9/P7B.22/P7B.23, unmodified) --
        # a production deployment wanting a stronger monotonic source may inject one via
        # a future FabricGateDependencies field without changing this call shape.
        import time as _time
        fencing_epoch = _time.time_ns()

        try:
            decision = decide_placement(
                tenant_id=tenant_id, workspace_id=workspace_id, project_id=project_id,
                migration_id=migration.migration_id, plan_id=plan.plan_id, plan_revision=getattr(plan, "revision", 1),
                execution_identity_seal_fingerprint=plan.fingerprint, fencing_epoch=fencing_epoch,
                candidates=candidates, capability_requirement=capability_requirement,
                actor_context=actor, authorization_callback=deps.placement_authorization_callback,
                residency_policies=residency_policies, locality_by_site=locality_by_site,
                topology_graph=topology,
            )
        except NoCompliantPlacementError as exc:
            raise PipelineError(
                PipelineErrorCode.POLICY_DENIED,
                f"NO COMPLIANT PLACEMENT for plan {plan.plan_id!r} (migration "
                f"{migration.migration_id!r}): {exc}",
            ) from exc

        site = next((s for s in candidates if s.site_id == decision.selected_site_id), None)
        if site is None:  # pragma: no cover -- decide_placement can only select from candidates
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, "Placement selected an unknown site.")

        worker = bind_worker_for_placement(decision, deps.worker_registry, site, pod_spec_factory=deps.pod_spec_factory)
        return FabricPlacementBinding(decision=decision, site=site, worker=worker)

    def _release_fabric_binding(self, execution_id: str) -> None:
        self._fabric_binding_store.release(execution_id)

    def _acquire_ownership_gate(self, *, decision, worker, capability: str, execution_id: str) -> None:
        """
        P7B Group-3 (P7B.25) UNIVERSAL ownership gate -- called from advance_plan_
        execution's Step A.2 for EVERY physical-effect capability of a fabric-required
        plan (not only data_transport, which additionally does its own richer per-
        live-trust-check renewal inside execute_via_placement). Raises
        `NoFabricPlacementBindingError` (chained from the real `OwnershipError`) on any
        rejection -- reusing the SAME fail-closed path Step A.2 already uses for stale
        placement, rather than a second error shape. Emits P7B.32/P7B.34 telemetry/
        Evidence on both outcomes, purely as an observational side effect: a broken
        telemetry/evidence backend never changes the raised outcome (both wrapped in
        `except Exception: pass`), and neither is emitted if the corresponding dependency
        was never configured.
        """
        from akaalEngine.fabric.explainability import explain_ownership_decision
        from akaalEngine.fabric.group3_evidence import emit_ownership_decision_evidence
        from akaalEngine.fabric.ownership.models import OwnershipError
        from akaalEngine.fabric.placement.execution import acquire_ownership_for_physical_capability
        from akaalEngine.fabric.telemetry_integration import ownership_event

        ownership_key = f"{decision.tenant_id}::{decision.migration_id}::{decision.plan_id}"

        def _emit(*, accepted: bool, fencing_generation, reason: str) -> None:
            if self.fabric_dependencies.evidence_authority is not None:
                try:
                    emit_ownership_decision_evidence(
                        self.fabric_dependencies.evidence_authority, migration_id=decision.migration_id,
                        run_id=execution_id, ownership_key=ownership_key, tenant_id=decision.tenant_id,
                        site_id=decision.selected_site_id, worker_id=worker.worker_id,
                        accepted=accepted, fencing_generation=fencing_generation, reason=reason,
                    )
                except Exception:  # noqa: BLE001 -- evidence never overrides the real outcome
                    pass
            if self.fabric_dependencies.telemetry_authority is not None:
                try:
                    self.fabric_dependencies.telemetry_authority.record_event(ownership_event(
                        event_type="fabric.ownership.acquired" if accepted else "fabric.ownership.conflict_rejected",
                        ownership_key=ownership_key, tenant_id=decision.tenant_id, site_id=decision.selected_site_id,
                        worker_id=worker.worker_id, fencing_generation=fencing_generation if fencing_generation is not None else -1,
                        correlation_id=decision.correlation_id, outcome="ACCEPTED" if accepted else reason,
                    ))
                except Exception:  # noqa: BLE001 -- telemetry never overrides the real outcome
                    pass
            if self.fabric_dependencies.explanation_sink is not None:
                try:
                    self.fabric_dependencies.explanation_sink(explain_ownership_decision(
                        accepted=accepted, ownership_key=ownership_key, tenant_id=decision.tenant_id,
                        site_id=decision.selected_site_id, worker_id=worker.worker_id, capability=capability,
                        fencing_generation=fencing_generation, reason=reason,
                    ))
                except Exception:  # noqa: BLE001 -- explanation never overrides the real outcome
                    pass

        try:
            record = acquire_ownership_for_physical_capability(
                self.fabric_dependencies.ownership_manager, decision, worker,
                capability=capability, execution_id=execution_id,
            )
        except OwnershipError as ownership_exc:
            _emit(accepted=False, fencing_generation=None, reason=str(ownership_exc))
            raise NoFabricPlacementBindingError(
                f"Group-3 ownership refused for capability {capability!r}: {ownership_exc}"
            ) from ownership_exc
        _emit(accepted=True, fencing_generation=record.fencing_generation, reason="")

    # -------------------------------------------------------------------------
    # 2. Querying State
    # -------------------------------------------------------------------------

    def get_plan_execution(self, execution_id: str, conn: sqlite3.Connection) -> Optional[PlanExecutionRecord]:
        cur = conn.execute("SELECT * FROM plan_executions WHERE execution_id = ?", (execution_id,))
        row = cur.fetchone()
        if row is None:
            return None
        start_op = row["start_operation_id"] if "start_operation_id" in row.keys() else None
        cp_id = row["checkpoint_id"] if "checkpoint_id" in row.keys() else None
        return PlanExecutionRecord(
            execution_id=row["execution_id"],
            migration_id=row["migration_id"],
            plan_id=row["plan_id"],
            plan_fingerprint=row["plan_fingerprint"],
            initialization_fingerprint=row["initialization_fingerprint"],
            tenant_id=row["tenant_id"],
            workspace_id=row["workspace_id"],
            project_id=row["project_id"],
            status=PlanExecutionStatus(row["status"]),
            start_operation_id=start_op,
            checkpoint_id=cp_id,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_active_execution_for_migration(
        self,
        migration_id: str,
        conn: sqlite3.Connection,
    ) -> Optional[PlanExecutionRecord]:
        cur = conn.execute(
            """
            SELECT * FROM plan_executions
            WHERE migration_id = ? AND status IN ('ACCEPTED', 'RUNNING')
            ORDER BY created_at DESC LIMIT 1
            """,
            (migration_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        start_op = row["start_operation_id"] if "start_operation_id" in row.keys() else None
        cp_id = row["checkpoint_id"] if "checkpoint_id" in row.keys() else None
        return PlanExecutionRecord(
            execution_id=row["execution_id"],
            migration_id=row["migration_id"],
            plan_id=row["plan_id"],
            plan_fingerprint=row["plan_fingerprint"],
            initialization_fingerprint=row["initialization_fingerprint"],
            tenant_id=row["tenant_id"],
            workspace_id=row["workspace_id"],
            project_id=row["project_id"],
            status=PlanExecutionStatus(row["status"]),
            start_operation_id=start_op,
            checkpoint_id=cp_id,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_node_executions(self, execution_id: str, conn: sqlite3.Connection) -> List[NodeExecutionRecord]:
        cur = conn.execute(
            "SELECT * FROM node_executions WHERE execution_id = ? ORDER BY rowid ASC",
            (execution_id,),
        )
        records: List[NodeExecutionRecord] = []
        for row in cur.fetchall():
            cp_id = row["checkpoint_id"] if "checkpoint_id" in row.keys() else None
            records.append(
                NodeExecutionRecord(
                    node_execution_id=row["node_execution_id"],
                    execution_id=row["execution_id"],
                    migration_id=row["migration_id"],
                    graph_node_id=row["graph_node_id"],
                    capability_contract=row["capability_contract"],
                    side_effect=SideEffectClassification(row["side_effect"]),
                    state=NodeExecutionState(row["state"]),
                    current_attempt_id=row["current_attempt_id"],
                    current_invocation_id=row["current_invocation_id"],
                    binding_id=row["binding_id"],
                    contract_version=row["contract_version"],
                    lease_id=row["lease_id"],
                    fence_epoch=row["fence_epoch"],
                    checkpoint_id=cp_id,
                    result_payload=json.loads(row["result_payload"]) if row["result_payload"] else None,
                    error=json.loads(row["error"]) if row["error"] else None,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return records

    def get_node_execution(
        self,
        execution_id: str,
        graph_node_id: str,
        conn: sqlite3.Connection,
    ) -> Optional[NodeExecutionRecord]:
        cur = conn.execute(
            "SELECT * FROM node_executions WHERE execution_id = ? AND graph_node_id = ?",
            (execution_id, graph_node_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cp_id = row["checkpoint_id"] if "checkpoint_id" in row.keys() else None
        return NodeExecutionRecord(
            node_execution_id=row["node_execution_id"],
            execution_id=row["execution_id"],
            migration_id=row["migration_id"],
            graph_node_id=row["graph_node_id"],
            capability_contract=row["capability_contract"],
            side_effect=SideEffectClassification(row["side_effect"]),
            state=NodeExecutionState(row["state"]),
            current_attempt_id=row["current_attempt_id"],
            current_invocation_id=row["current_invocation_id"],
            binding_id=row["binding_id"],
            contract_version=row["contract_version"],
            lease_id=row["lease_id"],
            fence_epoch=row["fence_epoch"],
            checkpoint_id=cp_id,
            result_payload=json.loads(row["result_payload"]) if row["result_payload"] else None,
            error=json.loads(row["error"]) if row["error"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_ready_nodes(self, execution_id: str, conn: sqlite3.Connection) -> List[NodeExecutionRecord]:
        cur = conn.execute(
            """
            SELECT * FROM node_executions
            WHERE execution_id = ? AND state = 'READY'
            ORDER BY rowid ASC
            """,
            (execution_id,),
        )
        records: List[NodeExecutionRecord] = []
        for row in cur.fetchall():
            cp_id = row["checkpoint_id"] if "checkpoint_id" in row.keys() else None
            records.append(
                NodeExecutionRecord(
                    node_execution_id=row["node_execution_id"],
                    execution_id=row["execution_id"],
                    migration_id=row["migration_id"],
                    graph_node_id=row["graph_node_id"],
                    capability_contract=row["capability_contract"],
                    side_effect=SideEffectClassification(row["side_effect"]),
                    state=NodeExecutionState(row["state"]),
                    current_attempt_id=row["current_attempt_id"],
                    current_invocation_id=row["current_invocation_id"],
                    binding_id=row["binding_id"],
                    contract_version=row["contract_version"],
                    lease_id=row["lease_id"],
                    fence_epoch=row["fence_epoch"],
                    checkpoint_id=cp_id,
                    result_payload=json.loads(row["result_payload"]) if row["result_payload"] else None,
                    error=json.loads(row["error"]) if row["error"] else None,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return records


    # -------------------------------------------------------------------------
    # 3. Synchronous DAG Advancement Engine
    # -------------------------------------------------------------------------

    def advance_plan_execution(
        self,
        execution_id: str,
        plan: ExecutionPlan,
        actor: PipelineActorContext,
        operation_id: str,
        correlation_id: str,
        request_id: str,
        payload: Mapping[str, Any],
        uow_factory: Callable[[], SQLiteUnitOfWork],
    ) -> ExecutionOutcome:
        """Synchronously advances DAG execution through READY nodes, evaluating dependencies

        and activating successors until whole-plan terminal state or blocked.
        """
        while True:
            # Check execution state and get ready nodes
            with uow_factory() as uow_check:
                plan_rec = self.get_plan_execution(execution_id, uow_check.connection)
                if plan_rec is None:
                    return ExecutionOutcome(
                        is_success=False,
                        status="FAILED",
                        error_category=IPCErrorCategory.INTERNAL_ERROR,
                        error_code="PLAN_EXECUTION_NOT_FOUND",
                        error_message=f"Plan execution {execution_id!r} not found.",
                    )

                if plan_rec.plan_fingerprint != plan.fingerprint or plan_rec.plan_id != plan.plan_id:
                    return ExecutionOutcome(
                        is_success=False,
                        status="FAILED",
                        error_category=IPCErrorCategory.FORBIDDEN,
                        error_code="PLAN_FINGERPRINT_MISMATCH",
                        error_message=f"Plan fingerprint mismatch for execution {execution_id!r}: stored {plan_rec.plan_fingerprint!r} != plan {plan.fingerprint!r}.",
                    )



                if plan_rec.status == PlanExecutionStatus.CANCELLED:
                    return ExecutionOutcome(
                        is_success=False,
                        status="CANCELLED",
                        error_category=IPCErrorCategory.CANCELLED,
                        error_code="CANCELLED",
                        error_message="Plan execution has been cancelled.",
                    )
                if plan_rec.status == PlanExecutionStatus.FAILED:
                    return ExecutionOutcome(
                        is_success=False,
                        status="FAILED",
                        error_category=IPCErrorCategory.INTERNAL_ERROR,
                        error_code="FAILED",
                        error_message="Plan execution failed.",
                    )
                if plan_rec.status == PlanExecutionStatus.SUCCEEDED:
                    return ExecutionOutcome(is_success=True, status="SUCCEEDED")

                ready_nodes = self.get_ready_nodes(execution_id, uow_check.connection)

                # If no nodes are READY: evaluate whole-plan terminal state
                if not ready_nodes:
                    all_nodes = self.get_node_executions(execution_id, uow_check.connection)
                    all_succeeded = len(all_nodes) == len(plan.nodes) and all(
                        n.state == NodeExecutionState.SUCCEEDED for n in all_nodes
                    )
                    any_failed = any(n.state == NodeExecutionState.FAILED for n in all_nodes)

                    if all_succeeded:
                        self._mark_plan_succeeded(
                            execution_id=execution_id,
                            plan=plan,
                            actor=actor,
                            operation_id=operation_id,
                            correlation_id=correlation_id,
                            uow=uow_check,
                        )
                        return ExecutionOutcome(is_success=True, status="SUCCEEDED")


                    if any_failed:
                        return ExecutionOutcome(
                            is_success=False,
                            status="FAILED",
                            error_category=IPCErrorCategory.INTERNAL_ERROR,
                            error_code="NODE_FAILED",
                            error_message="One or more plan nodes failed.",
                        )


                    # In-progress / blocked
                    return ExecutionOutcome(is_success=True, status="RUNNING")

            # Dispatch the first available READY node in plan order
            node_to_dispatch = ready_nodes[0]
            target_node_id = node_to_dispatch.graph_node_id
            target_capability = node_to_dispatch.capability_contract

            # Step A: Capability Resolution
            eval_res = self.capability_resolver.evaluate_capability(
                capability_id=target_capability,
                mode=plan.mode,
                contract_version="1.0.0",
            )

            if not eval_res.is_available:
                err_code = (
                    "UNBOUND"
                    if not eval_res.dimension_status.get(CapabilityDimension.BINDING, True)
                    else "UNAVAILABLE"
                )
                err_msg = f"Node {target_node_id!r} capability {target_capability!r} unavailable: {'; '.join(eval_res.blockers)}"
                category = (
                    IPCErrorCategory.UNBOUND
                    if err_code == "UNBOUND"
                    else IPCErrorCategory.UNAVAILABLE
                )

                with uow_factory() as uow_fail:
                    self._mark_node_and_plan_failed(
                        execution_id=execution_id,
                        node_execution_id=node_to_dispatch.node_execution_id,
                        migration_id=plan.migration_id,
                        graph_node_id=target_node_id,
                        operation_id=operation_id,
                        error_code=err_code,
                        error_message=err_msg,
                        actor=actor,
                        conn=uow_fail.connection,
                    )

                return ExecutionOutcome(
                    is_success=False,
                    status="FAILED",
                    error_category=category,
                    error_code=err_code,
                    error_message=err_msg,
                )

            # Step A.1: Enforce M8 Validation-Only Non-Mutation Invariant
            if plan.mode == MigrationMode.M8_VALIDATION_ONLY or (hasattr(plan.mode, "value") and plan.mode.value == "M8_VALIDATION_ONLY") or str(plan.mode) == "M8":
                from akaalPipeline.contracts.enums import SideEffectClassification
                matched_node = next((n for n in plan.nodes if n.node_id == target_node_id), None)
                node_side_effect = getattr(getattr(matched_node, "task", None), "side_effect", None) or getattr(eval_res, "side_effect", None)
                if node_side_effect and node_side_effect != SideEffectClassification.READ_ONLY and target_capability not in ("state_diff", "validation_compare", "package_evidence", "verify_evidence", "schema_extract"):
                    err_code = "M8_MUTATION_PROHIBITED"
                    err_msg = f"Node {target_node_id!r} with capability {target_capability!r} performs mutations and is strictly prohibited in M8 validation-only mode."
                    with uow_factory() as uow_fail:
                        self._mark_node_and_plan_failed(
                            execution_id=execution_id,
                            node_execution_id=node_to_dispatch.node_execution_id,
                            migration_id=plan.migration_id,
                            graph_node_id=target_node_id,
                            operation_id=operation_id,
                            error_code=err_code,
                            error_message=err_msg,
                            actor=actor,
                            conn=uow_fail.connection,
                        )
                    return ExecutionOutcome(
                        is_success=False,
                        status="FAILED",
                        error_category=IPCErrorCategory.FORBIDDEN,
                        error_code=err_code,
                        error_message=err_msg,
                    )

            # Step A.2: Enforce mandatory Group-2 placement for fabric-required plans.
            # Mirrors the Step A.1 M8 gate immediately above in shape: check a plan-level
            # condition, fail the node+plan closed via the SAME `_mark_node_and_plan_failed`
            # path, before any dispatch is attempted. A node with no physical side effect
            # (schema/control-plane read-only steps) is exempt -- only actual physical work
            # requires a live, fresh, valid Group-2 binding to proceed.
            if plan_requires_fabric_placement(plan):
                from akaalPipeline.contracts.enums import SideEffectClassification as _SideEffectClassification
                matched_node_fabric = next((n for n in plan.nodes if n.node_id == target_node_id), None)
                node_side_effect_fabric = getattr(getattr(matched_node_fabric, "task", None), "side_effect", None)
                if node_side_effect_fabric != _SideEffectClassification.READ_ONLY:
                    try:
                        fabric_binding_check = self._fabric_binding_store.require(execution_id)
                        current_topology_check = self.fabric_dependencies.topology_provider(fabric_binding_check.decision.tenant_id)
                        if is_binding_stale(fabric_binding_check, current_topology_check):
                            raise NoFabricPlacementBindingError(
                                f"Placement decision {fabric_binding_check.decision.decision_id!r} is stale."
                            )
                        # P7B Group-3 (P7B.25) UNIVERSAL ownership gate: applies to EVERY
                        # physical-effect capability of a fabric-required plan, not only
                        # data_transport -- closes the gap where CDC/incremental/state-
                        # reconciliation capabilities (dispatched through their own,
                        # non-Fabric-aware ExecutionPort via ordinary capability
                        # resolution, never routed through FabricPlacementExecutionPort)
                        # would otherwise reach physical mutation with zero ownership/
                        # fencing protection merely because they are not shaped like
                        # execute_via_placement's reader/writer/partition contract. See
                        # akaalEngine.fabric.placement.execution.
                        # acquire_ownership_for_physical_capability's docstring for the
                        # full rationale. `self.fabric_dependencies.ownership_manager`
                        # is guaranteed non-None here -- materialize_plan_execution
                        # already refused to create this execution otherwise.
                        self._acquire_ownership_gate(
                            decision=fabric_binding_check.decision, worker=fabric_binding_check.worker,
                            capability=target_capability, execution_id=execution_id,
                        )
                    except NoFabricPlacementBindingError as fabric_exc:
                        err_code = "FABRIC_PLACEMENT_REQUIRED"
                        err_msg = f"Node {target_node_id!r} requires Group-2 fabric placement, which is missing or stale: {fabric_exc}"
                        with uow_factory() as uow_fail:
                            self._mark_node_and_plan_failed(
                                execution_id=execution_id,
                                node_execution_id=node_to_dispatch.node_execution_id,
                                migration_id=plan.migration_id,
                                graph_node_id=target_node_id,
                                operation_id=operation_id,
                                error_code=err_code,
                                error_message=err_msg,
                                actor=actor,
                                conn=uow_fail.connection,
                            )
                        return ExecutionOutcome(
                            is_success=False,
                            status="FAILED",
                            error_category=IPCErrorCategory.FORBIDDEN,
                            error_code=err_code,
                            error_message=err_msg,
                        )

            matching_binding = eval_res.selected_binding
            # Physical bulk data movement in a fabric-required plan MUST route through
            # the Group-2 FabricPlacementExecutionPort (execute_via_placement), never
            # whatever binding capability resolution would otherwise have picked -- this
            # override is the structural "no bypass" enforcement: there is no branch
            # anywhere in this method that dispatches a data_transport node of a
            # fabric-required plan through any OTHER port_instance.
            if plan_requires_fabric_placement(plan) and target_capability == "data_transport":
                if self._fabric_data_transport_binding is None:  # pragma: no cover -- guarded by Step A.2 above
                    raise PipelineError(PipelineErrorCode.POLICY_DENIED, "Fabric placement required but no fabric binding configured.")
                matching_binding = self._fabric_data_transport_binding
            if not matching_binding or not isinstance(matching_binding.port_instance, ExecutionPort):
                err_code = "UNBOUND"
                err_msg = f"No healthy ExecutionPort engine binding registered for capability {target_capability!r} (UNBOUND)."
                with uow_factory() as uow_fail:
                    self._mark_node_and_plan_failed(
                        execution_id=execution_id,
                        node_execution_id=node_to_dispatch.node_execution_id,
                        migration_id=plan.migration_id,
                        graph_node_id=target_node_id,
                        operation_id=operation_id,
                        error_code=err_code,
                        error_message=err_msg,
                        actor=actor,
                        conn=uow_fail.connection,
                    )
                return ExecutionOutcome(
                    is_success=False,
                    status="FAILED",
                    error_category=IPCErrorCategory.UNBOUND,
                    error_code=err_code,
                    error_message=err_msg,
                )

            # Step B: Commit-Before-Dispatch Acceptance in UoW (Atomic Claim)
            has_preassigned_attempt = False
            if node_to_dispatch.current_attempt_id and node_to_dispatch.lease_id:
                with uow_factory() as uow_chk:
                    existing_lease = self.lease_manager.get_lease(node_to_dispatch.current_attempt_id, conn=uow_chk.connection)
                    if existing_lease is not None and not existing_lease.is_expired():
                        attempt_id = node_to_dispatch.current_attempt_id
                        lease_id = existing_lease.lease_id
                        lease = existing_lease
                        has_preassigned_attempt = True

            if not has_preassigned_attempt:
                attempt_id = f"att-{uuid.uuid4().hex}"
                lease_id = f"lease-{uuid.uuid4().hex}"
            inv_id = f"inv-{uuid.uuid4().hex}"
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()
            init_fp = plan_rec.initialization_fingerprint

            with uow_factory() as uow_disp:
                now_str = datetime.now(timezone.utc).isoformat()
                cur_claim = uow_disp.connection.execute(
                    """
                    UPDATE node_executions SET
                        state = ?, current_attempt_id = ?, current_invocation_id = ?,
                        binding_id = ?, contract_version = ?, lease_id = ?,
                        fence_epoch = ?, updated_at = ?
                    WHERE node_execution_id = ? AND state = ?
                    """,
                    (
                        NodeExecutionState.DISPATCHED.value,
                        attempt_id,
                        inv_id,
                        matching_binding.binding_id,
                        "1.0.0",
                        lease_id,
                        1 if not has_preassigned_attempt else lease.fence_epoch,
                        now_str,
                        node_to_dispatch.node_execution_id,
                        NodeExecutionState.READY.value,
                    ),
                )
                if cur_claim.rowcount == 0:
                    # Non-atomic claim race prevented: another worker claimed this READY node!
                    continue

                if not has_preassigned_attempt:
                    lease = self.lease_manager.acquire_lease(
                        lease_id=lease_id,
                        attempt_id=attempt_id,
                        owner_id=actor.actor_id,
                        expires_at=expires_at,
                        initialization_fingerprint=init_fp,
                        conn=uow_disp.connection,
                    )
                uow_disp.connection.execute(
                    """
                    UPDATE node_executions SET
                        lease_id = ?, fence_epoch = ?
                    WHERE node_execution_id = ?
                    """,
                    (
                        lease.lease_id,
                        lease.fence_epoch,
                        node_to_dispatch.node_execution_id,
                    ),
                )

                uow_disp.connection.execute(
                    "UPDATE plan_executions SET status = ?, start_operation_id = COALESCE(start_operation_id, ?), updated_at = ? WHERE execution_id = ?",
                    (PlanExecutionStatus.RUNNING.value, operation_id, now_str, execution_id),
                )
                agg = self.repository.get_by_id(plan.migration_id, connection=uow_disp.connection)
                if agg:
                    agg.active_attempt_id = attempt_id
                    agg.revision += 1
                    self.repository.save(agg, connection=uow_disp.connection)

                evt_node_disp = DomainEvent.create(
                    plan.migration_id,
                    "node.dispatched",
                    {
                        "execution_id": execution_id,
                        "graph_node_id": target_node_id,
                        "capability": target_capability,
                        "attempt_id": attempt_id,
                        "invocation_id": inv_id,
                        "binding_id": matching_binding.binding_id,
                    },
                )
                self.outbox_service.stage_event(evt_node_disp, uow_disp.connection)
                self.audit_service.record_event(
                    actor,
                    "node.dispatched",
                    target_node_id,
                    uow_disp.connection,
                    details={
                        "execution_id": execution_id,
                        "attempt_id": attempt_id,
                        "binding_id": matching_binding.binding_id,
                    },
                )

            # Step C: Physical Dispatch to ExecutionPort
            dispatch_payload = dict(payload) if payload else {}
            dispatch_payload["capability_contract"] = target_capability
            dispatch_payload["capability_id"] = target_capability
            dispatch_payload["graph_node_id"] = target_node_id
            dispatch_payload["migration_id"] = plan.migration_id
            dispatch_payload["execution_id"] = execution_id
            dispatch_payload["mode"] = plan.mode.value
            if hasattr(plan, "configuration") and plan.configuration:
                dispatch_payload["configuration"] = dict(plan.configuration)

            # Propagate output tokens and context from successfully completed predecessor nodes
            cur_preds = uow_disp.connection.execute(
                """
                SELECT ne.graph_node_id, ne.result_payload
                FROM node_executions ne
                WHERE ne.execution_id = ? AND ne.state = 'SUCCEEDED'
                """,
                (execution_id,),
            )
            for pred_row in cur_preds.fetchall():
                if pred_row["result_payload"]:
                    try:
                        p_res = json.loads(pred_row["result_payload"])
                        if isinstance(p_res, dict):
                            for prop_key in ("cdc_stream_handle", "cdc_boundary_token", "boundary_token", "extracted_watermark", "applied_records"):
                                if prop_key in p_res and prop_key not in dispatch_payload:
                                    dispatch_payload[prop_key] = p_res[prop_key]
                    except Exception:
                        pass

            if node_to_dispatch.checkpoint_id:
                dispatch_payload["checkpoint_id"] = node_to_dispatch.checkpoint_id
                cur_cp = uow_disp.connection.execute(
                    "SELECT payload_reference FROM checkpoints WHERE checkpoint_id = ?",
                    (node_to_dispatch.checkpoint_id,),
                )
                cp_row = cur_cp.fetchone()
                if cp_row and cp_row["payload_reference"]:
                    cp_ref = cp_row["payload_reference"]
                    art_cur = uow_disp.connection.execute(
                        "SELECT content FROM immutable_artifacts WHERE artifact_id = ? OR artifact_id = ?",
                        (f"art-{cp_ref}", cp_ref),
                    )
                    art_row = art_cur.fetchone()
                    if art_row:
                        try:
                            cp_data = json.loads(art_row["content"])
                            if isinstance(cp_data, dict):
                                dispatch_payload["checkpoint_data"] = cp_data
                        except Exception:
                            pass
                    elif cp_ref.startswith("{"):
                        try:
                            cp_data = json.loads(cp_ref)
                            if isinstance(cp_data, dict):
                                dispatch_payload["checkpoint_data"] = cp_data
                        except Exception:
                            pass

            authz_token = None
            if hasattr(self, "minter") and self.minter:
                try:
                    from akaalPipeline.security.seal import ExecutionSealBuilder
                    seal = ExecutionSealBuilder.build_seal(
                        tenant_id=actor.organization_id,
                        workspace_id=actor.workspace_id or "default",
                        project_id=actor.project_id or "default",
                        migration_id=plan.migration_id,
                        plan_id=plan.plan_id,
                        plan_revision=getattr(plan, "revision", 1),
                        execution_mode=plan.mode.value if hasattr(plan.mode, "value") else str(plan.mode),
                        source_identity_fingerprint=getattr(plan, "source_identity_fingerprint", "src_fp"),
                        target_identity_fingerprint=getattr(plan, "target_identity_fingerprint", "tgt_fp"),
                        selection_scope_fingerprint=getattr(plan, "selection_scope_fingerprint", "sel_fp"),
                        config_fingerprint=getattr(plan, "config_fingerprint", "cfg_fp"),
                        initialization_fingerprint=init_fp,
                        approval_fingerprint=getattr(plan, "approval_fingerprint", "appr_fp"),
                        fence_epoch=lease.fence_epoch,
                    )
                    authz_token = self.minter.mint_authorization(
                        tenant_id=actor.organization_id,
                        workspace_id=actor.workspace_id or "default",
                        project_id=actor.project_id or "default",
                        migration_id=plan.migration_id,
                        execution_id=execution_id,
                        execution_seal=seal,
                        allowed_operations=["*"],
                        allowed_target_schemas=["*"],
                        security_revision=1,
                    )
                    dispatch_payload["execution_authorization_artifact"] = authz_token
                except Exception as mint_exc:
                    logger.warning("Failed minting execution authorization artifact: %s", mint_exc)

            req = EngineInvocationRequest(
                contract_version="1.0.0",
                binding_id=matching_binding.binding_id,
                correlation_id=correlation_id,
                operation_id=operation_id,
                attempt_id=attempt_id,
                invocation_id=inv_id,
                lease_id=lease.lease_id,
                fence_epoch=lease.fence_epoch,
                graph_node_id=target_node_id,
                initialization_fingerprint=init_fp,
                payload=dispatch_payload,
                checkpoint_id=node_to_dispatch.checkpoint_id,
                execution_authorization_artifact=authz_token,
                tenant_id=actor.organization_id,
                workspace_id=actor.workspace_id,
                project_id=actor.project_id,
            )

            # Captured BEFORE dispatch (not re-fetched in `finally`): a FAILED-plan path
            # below (_mark_node_and_plan_failed) releases the fabric binding from
            # self._fabric_binding_store as part of failing the plan, so re-fetching it
            # afterward in `finally` would find nothing to finalize on exactly the
            # exception path this finalization most needs to cover.
            _worker_to_finalize = None
            if plan_requires_fabric_placement(plan):
                _matched_node_finalize = next((n for n in plan.nodes if n.node_id == target_node_id), None)
                _side_effect_finalize = getattr(getattr(_matched_node_finalize, "task", None), "side_effect", None)
                from akaalPipeline.contracts.enums import SideEffectClassification as _SideEffectClassificationFinalize
                if _side_effect_finalize != _SideEffectClassificationFinalize.READ_ONLY:
                    _binding_finalize = self._fabric_binding_store.try_get(execution_id)
                    if _binding_finalize is not None:
                        _worker_to_finalize = (_binding_finalize.worker, _binding_finalize.decision.tenant_id)

            try:
                engine_res = matching_binding.port_instance.execute_task(req)
                eng_task_id = None
                if isinstance(engine_res.result_payload, dict):
                    rcpt = engine_res.result_payload.get("engine_execution_receipt")
                    if isinstance(rcpt, dict) and rcpt.get("engine_task_id"):
                        eng_task_id = rcpt["engine_task_id"]
                    elif engine_res.result_payload.get("task_id"):
                        eng_task_id = engine_res.result_payload["task_id"]
                    elif engine_res.result_payload.get("runtime_task_id"):
                        eng_task_id = engine_res.result_payload["runtime_task_id"]
                if eng_task_id:
                    with uow_factory() as uow_task:
                        uow_task.connection.execute(
                            "UPDATE node_executions SET current_engine_task_id = ? WHERE node_execution_id = ?",
                            (eng_task_id, node_to_dispatch.node_execution_id)
                        )
            except Exception as dispatch_exc:
                err_code = "ENGINE_DISPATCH_ERROR"
                err_msg = f"Engine port {matching_binding.binding_id!r} failed during task execution: {dispatch_exc}"
                with uow_factory() as uow_crash:
                    self._mark_node_and_plan_failed(
                        execution_id=execution_id,
                        node_execution_id=node_to_dispatch.node_execution_id,
                        migration_id=plan.migration_id,
                        graph_node_id=target_node_id,
                        operation_id=operation_id,
                        error_code=err_code,
                        error_message=err_msg,
                        actor=actor,
                        conn=uow_crash.connection,
                        attempt_id=attempt_id,
                        invocation_id=inv_id,
                    )
                return ExecutionOutcome(
                    is_success=False,
                    status="FAILED",
                    error_category=IPCErrorCategory.UNAVAILABLE,
                    error_code=err_code,
                    error_message=err_msg,
                )
            finally:
                # P7B.35 hostile-review finding: bind_worker_for_placement marks a
                # worker BUSY once per execution, but only execute_via_placement's own
                # internal finally block ever finalized it back -- for every OTHER
                # physical-effect capability (cdc_apply, incremental_apply, etc.,
                # dispatched here through their own independently-resolved
                # ExecutionPort, never through execute_via_placement), the worker leaked
                # BUSY forever. This finalizes it here instead, at the ONE real dispatch
                # call site every capability (data_transport included) passes through --
                # using the SAME canonical finalize_worker_after_dispatch
                # execute_via_placement itself now calls, so there is exactly one
                # worker-lifecycle finalization authority, not two. Calling it a SECOND
                # time for data_transport (once inside execute_via_placement's own
                # finally, once here) is safe and a no-op: finalize_worker_after_dispatch
                # only acts when the worker's CURRENT state is still BUSY, and
                # execute_via_placement's own finally already ran by the time this outer
                # one does (Python unwinds inner finally blocks before outer ones).
                #
                # Uses `_worker_to_finalize`, CAPTURED BEFORE dispatch (see above) --
                # deliberately NOT re-fetched from self._fabric_binding_store here, since
                # a FAILED-plan path above (_mark_node_and_plan_failed) already releases
                # that binding as part of failing the plan; re-fetching here would find
                # nothing to finalize on exactly the exception path this most needs to
                # cover.
                if _worker_to_finalize is not None and self.fabric_dependencies is not None:
                    from akaalEngine.fabric.placement.execution import finalize_worker_after_dispatch
                    _finalize_worker, _finalize_tenant_id = _worker_to_finalize
                    finalize_worker_after_dispatch(self.fabric_dependencies.worker_registry, _finalize_worker, _finalize_tenant_id)

            # Check if task was accepted for asynchronous background completion
            if getattr(engine_res, "is_in_progress", False):
                return ExecutionOutcome(is_success=True, status="RUNNING")

            # Step D: Reconcile Result & Advance Successors
            try:
                with uow_factory() as uow_recon:
                    reconciled = self.result_reconciler.reconcile_result(
                        engine_res,
                        expected_initialization_fingerprint=init_fp,
                        conn=uow_recon.connection,
                        expected_invocation_id=inv_id,
                        expected_attempt_id=attempt_id,
                        expected_lease_id=lease.lease_id,
                        expected_graph_node_id=target_node_id,
                        expected_binding_id=matching_binding.binding_id,
                        expected_contract_version="1.0.0",
                    )

                    now_str = datetime.now(timezone.utc).isoformat()

                    if reconciled.get("status") == "SUCCEEDED":
                        uow_recon.connection.execute(
                            """
                            UPDATE node_executions SET
                                state = ?, result_payload = ?, updated_at = ?
                            WHERE node_execution_id = ?
                            """,
                            (
                                NodeExecutionState.SUCCEEDED.value,
                                json.dumps(reconciled.get("result_payload", {})),
                                now_str,
                                node_to_dispatch.node_execution_id,
                            ),
                        )
                        evt_succ = DomainEvent.create(
                            plan.migration_id,
                            "node.succeeded",
                            {
                                "execution_id": execution_id,
                                "graph_node_id": target_node_id,
                                "attempt_id": attempt_id,
                                "invocation_id": inv_id,
                            },
                        )
                        self.outbox_service.stage_event(evt_succ, uow_recon.connection)
                        self.audit_service.record_event(
                            actor,
                            "node.succeeded",
                            target_node_id,
                            uow_recon.connection,
                            details={"execution_id": execution_id, "attempt_id": attempt_id},
                        )

                        # Evaluate & activate newly ready successors
                        self._evaluate_and_activate_successors(execution_id, plan, actor, uow_recon)

                    else:
                        err_c = reconciled.get("error_code") or "ENGINE_ERROR"
                        err_m = reconciled.get("error_message") or "Physical engine execution failed."
                        self._mark_node_and_plan_failed(
                            execution_id=execution_id,
                            node_execution_id=node_to_dispatch.node_execution_id,
                            migration_id=plan.migration_id,
                            graph_node_id=target_node_id,
                            operation_id=operation_id,
                            error_code=err_c,
                            error_message=err_m,
                            actor=actor,
                            conn=uow_recon.connection,
                            attempt_id=attempt_id,
                            invocation_id=inv_id,
                        )
                        return ExecutionOutcome(
                            is_success=False,
                            status="FAILED",
                            error_category=IPCErrorCategory.INTERNAL_ERROR,
                            error_code=err_c,
                            error_message=err_m,
                        )
            except StaleResultError as stale_exc:
                err_code = "STALE_RESULT"
                err_msg = str(stale_exc)
                with uow_factory() as uow_stale:
                    self._mark_node_and_plan_failed(
                        execution_id=execution_id,
                        node_execution_id=node_to_dispatch.node_execution_id,
                        migration_id=plan.migration_id,
                        graph_node_id=target_node_id,
                        operation_id=operation_id,
                        error_code=err_code,
                        error_message=err_msg,
                        actor=actor,
                        conn=uow_stale.connection,
                        attempt_id=attempt_id,
                        invocation_id=inv_id,
                    )
                return ExecutionOutcome(
                    is_success=False,
                    status="FAILED",
                    error_category=IPCErrorCategory.STALE_RESULT,
                    error_code=err_code,
                    error_message=err_msg,
                )
            except Exception as recon_exc:
                err_code = "RECONCILIATION_ERROR"
                err_msg = f"Result reconciliation failed: {recon_exc}"
                with uow_factory() as uow_err:
                    self._mark_node_and_plan_failed(
                        execution_id=execution_id,
                        node_execution_id=node_to_dispatch.node_execution_id,
                        migration_id=plan.migration_id,
                        graph_node_id=target_node_id,
                        operation_id=operation_id,
                        error_code=err_code,
                        error_message=err_msg,
                        actor=actor,
                        conn=uow_err.connection,
                        attempt_id=attempt_id,
                        invocation_id=inv_id,
                    )
                return ExecutionOutcome(
                    is_success=False,
                    status="FAILED",
                    error_category=IPCErrorCategory.INTERNAL_ERROR,
                    error_code=err_code,
                    error_message=err_msg,
                )

    # -------------------------------------------------------------------------
    # 4. Successor Activation & Terminal Helpers
    # -------------------------------------------------------------------------

    def _evaluate_and_activate_successors(
        self,
        execution_id: str,
        plan: ExecutionPlan,
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> List[str]:
        """Evaluates dependency graph: any BLOCKED node whose dependencies are ALL SUCCEEDED
        transitions to READY.
        """
        all_nodes = self.get_node_executions(execution_id, uow.connection)
        states = {n.graph_node_id: n.state.value for n in all_nodes}

        activated = []
        now_str = datetime.now(timezone.utc).isoformat()
        for node in plan.nodes:
            current_st = states.get(node.node_id)
            if current_st == NodeExecutionState.BLOCKED.value:
                all_deps_succeeded = all(
                    states.get(dep_id) == NodeExecutionState.SUCCEEDED.value
                    for dep_id in node.dependencies
                )
                if all_deps_succeeded:
                    uow.connection.execute(
                        """
                        UPDATE node_executions SET state = ?, updated_at = ?
                        WHERE execution_id = ? AND graph_node_id = ?
                        """,
                        (NodeExecutionState.READY.value, now_str, execution_id, node.node_id),
                    )
                    states[node.node_id] = NodeExecutionState.READY.value
                    activated.append(node.node_id)

                    evt = DomainEvent.create(
                        plan.migration_id,
                        "node.ready",
                        {"execution_id": execution_id, "graph_node_id": node.node_id},
                    )
                    self.outbox_service.stage_event(evt, uow.connection)
                    self.audit_service.record_event(
                        actor,
                        "node.ready",
                        node.node_id,
                        uow.connection,
                        details={"execution_id": execution_id},
                    )
        return activated

    def _mark_plan_succeeded(
        self,
        execution_id: str,
        plan: ExecutionPlan,
        actor: PipelineActorContext,
        operation_id: str,
        correlation_id: str,
        uow: SQLiteUnitOfWork,
    ) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        uow.connection.execute(
            "UPDATE plan_executions SET status = ?, updated_at = ? WHERE execution_id = ?",
            (PlanExecutionStatus.SUCCEEDED.value, now_str, execution_id),
        )
        self.operation_service.update_status(
            operation_id,
            OperationStatus.SUCCEEDED,
            uow.connection,
            result_payload={"plan_id": plan.plan_id, "status": "SUCCEEDED", "execution_id": execution_id},
        )
        agg = self.repository.get_by_id(plan.migration_id, connection=uow.connection)
        if agg:
            finite_modes = {
                MigrationMode.M1_BULK,
                MigrationMode.M4_INCREMENTAL,
                MigrationMode.M5_STATE_SYNC,
                MigrationMode.M6_SCHEMA_ONLY,
                MigrationMode.M7_DATA_ONLY,
                MigrationMode.M8_VALIDATION_ONLY,
            }
            if plan.mode in finite_modes or agg.mode in finite_modes:
                agg.state = MigrationLifecycleState.COMPLETED
            else:
                agg.state = MigrationLifecycleState.ACTIVE
            agg.revision += 1
            self.repository.save(agg, connection=uow.connection)

        evt = DomainEvent.create(
            plan.migration_id,
            "plan.succeeded",
            {"execution_id": execution_id, "plan_id": plan.plan_id, "migration_id": plan.migration_id},
        )
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(
            actor,
            "plan.succeeded",
            plan.plan_id,
            uow.connection,
            details={"execution_id": execution_id},
        )
        self._release_fabric_binding(execution_id)

    def _mark_node_and_plan_failed(
        self,
        execution_id: str,
        node_execution_id: str,
        migration_id: str,
        graph_node_id: str,
        operation_id: str,
        error_code: str,
        error_message: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        attempt_id: Optional[str] = None,
        invocation_id: Optional[str] = None,
    ) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        err_dict = {"code": error_code, "message": error_message}
        conn.execute(
            """
            UPDATE node_executions SET
                state = ?, error = ?, updated_at = ?
            WHERE node_execution_id = ?
            """,
            (
                NodeExecutionState.FAILED.value,
                json.dumps(err_dict),
                now_str,
                node_execution_id,
            ),
        )
        conn.execute(
            "UPDATE plan_executions SET status = ?, updated_at = ? WHERE execution_id = ?",
            (PlanExecutionStatus.FAILED.value, now_str, execution_id),
        )
        self.operation_service.update_status(
            operation_id,
            OperationStatus.FAILED,
            conn,
            error=err_dict,
        )

        evt_node_fail = DomainEvent.create(
            migration_id,
            "node.failed",
            {
                "execution_id": execution_id,
                "graph_node_id": graph_node_id,
                "attempt_id": attempt_id,
                "invocation_id": invocation_id,
                "error_code": error_code,
                "error_message": error_message,
            },
        )
        self.outbox_service.stage_event(evt_node_fail, conn)
        self.audit_service.record_event(
            actor,
            "node.failed",
            graph_node_id,
            conn,
            details={"execution_id": execution_id, "error_code": error_code, "error_message": error_message},
        )

        evt_op_fail = DomainEvent.create(
            migration_id,
            "operation.failed",
            {
                "operation_id": operation_id,
                "attempt_id": attempt_id,
                "invocation_id": invocation_id,
                "error_code": error_code,
                "error_message": error_message,
            },
        )
        self.outbox_service.stage_event(evt_op_fail, conn)
        self.audit_service.record_event(
            actor,
            "operation.failed",
            operation_id,
            conn,
            details={"error_code": error_code, "error_message": error_message},
        )
        self._release_fabric_binding(execution_id)

    # -------------------------------------------------------------------------
    # 5. Cancellation Support
    # -------------------------------------------------------------------------

    def cancel_plan_execution(
        self,
        execution_id: str,
        reason: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> None:
        """Cancels plan execution and marks non-terminal node executions CANCELLED."""
        now_str = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE plan_executions SET status = ?, updated_at = ? WHERE execution_id = ?",
            (PlanExecutionStatus.CANCELLED.value, now_str, execution_id),
        )
        self._release_fabric_binding(execution_id)
        conn.execute(
            """
            UPDATE node_executions SET state = ?, error = ?, updated_at = ?
            WHERE execution_id = ? AND state IN ('BLOCKED', 'READY', 'ACCEPTED', 'DISPATCHED')
            """,
            (
                NodeExecutionState.CANCELLED.value,
                json.dumps({"code": "CANCELLED", "message": reason}),
                now_str,
                execution_id,
            ),
        )

    # -------------------------------------------------------------------------
    # 6. Recovery Support
    # -------------------------------------------------------------------------

    def recover_plan_execution(
        self,
        migration_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        source_attempt_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        replacement_attempt_id: Optional[str] = None,
        replacement_lease_id: Optional[str] = None,
        replacement_fence_epoch: Optional[int] = None,
        recovery_operation_id: Optional[str] = None,
    ) -> Optional[PlanExecutionRecord]:
        """Recovers an interrupted, cancelled, or failed plan execution, preserving already
        SUCCEEDED nodes, resetting incomplete nodes whose dependencies are satisfied to READY,
        and authoritatively binding replacement attempt authority and checkpoint to the active node.
        """
        cur = conn.execute(
            """
            SELECT * FROM plan_executions
            WHERE migration_id = ?
            ORDER BY rowid DESC LIMIT 1
            """,
            (migration_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        execution_id = row["execution_id"]
        now_str = datetime.now(timezone.utc).isoformat()

        # Update plan execution status to ACCEPTED and set start_operation_id and checkpoint_id
        conn.execute(
            """
            UPDATE plan_executions SET
                status = ?, start_operation_id = COALESCE(?, start_operation_id),
                checkpoint_id = COALESCE(?, checkpoint_id), updated_at = ?
            WHERE execution_id = ?
            """,
            (PlanExecutionStatus.ACCEPTED.value, recovery_operation_id, checkpoint_id, now_str, execution_id),
        )

        # Query all node executions for this plan execution
        cur_nodes = conn.execute(
            "SELECT * FROM node_executions WHERE execution_id = ? ORDER BY rowid ASC",
            (execution_id,),
        )
        nodes = cur_nodes.fetchall()
        node_states = {n["graph_node_id"]: n["state"] for n in nodes}

        # Determine specific target node for recovery binding
        target_node_id: Optional[str] = None
        if source_attempt_id:
            for n in nodes:
                if n["current_attempt_id"] == source_attempt_id:
                    target_node_id = n["graph_node_id"]
                    break

        if target_node_id is None and checkpoint_id:
            cp_cur = conn.execute(
                "SELECT graph_node_id, attempt_id, initialization_fingerprint FROM checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            )
            cp_row = cp_cur.fetchone()
            if cp_row is None:
                raise PipelineError(
                    PipelineErrorCode.NOT_FOUND,
                    f"Checkpoint {checkpoint_id!r} not found for recovery.",
                )
            if cp_row["initialization_fingerprint"] and cp_row["initialization_fingerprint"] != row["initialization_fingerprint"]:
                raise PipelineError(
                    PipelineErrorCode.POLICY_DENIED,
                    f"Checkpoint {checkpoint_id!r} initialization fingerprint mismatch: expected {row['initialization_fingerprint']!r}, got {cp_row['initialization_fingerprint']!r}.",
                )
            if cp_row["graph_node_id"]:
                target_node_id = cp_row["graph_node_id"]
            elif cp_row["attempt_id"]:
                for n in nodes:
                    if n["current_attempt_id"] == cp_row["attempt_id"]:
                        target_node_id = n["graph_node_id"]
                        break

        # Load plan artifact to inspect node dependencies
        plan_id = row["plan_id"]
        plan_art_cur = conn.execute(
            "SELECT content, fingerprint FROM immutable_artifacts WHERE artifact_id = ? OR artifact_id = ?",
            (f"art-{plan_id}", plan_id),
        )
        plan_art_row = plan_art_cur.fetchone()

        plan_nodes_deps = {}
        if plan_art_row:
            try:
                plan_data = json.loads(plan_art_row["content"])
                stored_plan_fp = plan_data.get("fingerprint")
                if stored_plan_fp and row["plan_fingerprint"] and stored_plan_fp != row["plan_fingerprint"]:
                    raise PipelineError(
                        PipelineErrorCode.POLICY_DENIED,
                        f"Plan artifact {plan_id!r} fingerprint mismatch: stored {row['plan_fingerprint']!r} != plan {stored_plan_fp!r}.",
                    )
                for nd in plan_data.get("nodes", []):
                    plan_nodes_deps[nd.get("node_id")] = nd.get("dependencies", [])
            except PipelineError:
                raise
            except Exception:
                pass



        bound_target = False
        for n in nodes:
            nid = n["graph_node_id"]
            # PRESERVE SUCCEEDED NODES
            if n["state"] == NodeExecutionState.SUCCEEDED.value:
                continue

            deps = plan_nodes_deps.get(nid, [])
            all_deps_ok = all(node_states.get(d) == NodeExecutionState.SUCCEEDED.value for d in deps)
            if all_deps_ok:
                new_state = NodeExecutionState.READY.value
                # If target_node_id was determined, bind ONLY to target_node_id
                # Otherwise, fall back to binding to the first ready node
                is_recovery_target = False
                if target_node_id is not None:
                    if nid == target_node_id and not bound_target:
                        is_recovery_target = True
                else:
                    if not bound_target:
                        is_recovery_target = True

                if is_recovery_target:
                    att_id = replacement_attempt_id
                    l_id = replacement_lease_id
                    f_ep = replacement_fence_epoch
                    cp_id = checkpoint_id
                    bound_target = True
                else:
                    att_id = None
                    l_id = None
                    f_ep = None
                    cp_id = None

                conn.execute(
                    """
                    UPDATE node_executions SET
                        state = ?, current_attempt_id = ?, lease_id = ?, fence_epoch = ?,
                        checkpoint_id = ?, error = NULL, updated_at = ?
                    WHERE node_execution_id = ?
                    """,
                    (new_state, att_id, l_id, f_ep, cp_id, now_str, n["node_execution_id"]),
                )
            else:
                new_state = NodeExecutionState.BLOCKED.value
                conn.execute(
                    """
                    UPDATE node_executions SET
                        state = ?, current_attempt_id = NULL, lease_id = NULL, fence_epoch = NULL,
                        checkpoint_id = NULL, error = NULL, updated_at = ?
                    WHERE node_execution_id = ?
                    """,
                    (new_state, now_str, n["node_execution_id"]),
                )
            node_states[nid] = new_state


        evt = DomainEvent.create(
            migration_id,
            "plan.recovered",
            {
                "execution_id": execution_id,
                "migration_id": migration_id,
                "source_attempt_id": source_attempt_id,
                "checkpoint_id": checkpoint_id,
                "replacement_attempt_id": replacement_attempt_id,
                "recovery_operation_id": recovery_operation_id,
            },
        )
        self.outbox_service.stage_event(evt, conn)
        self.audit_service.record_event(
            actor,
            "plan.recovered",
            execution_id,
            conn,
            details={
                "migration_id": migration_id,
                "source_attempt_id": source_attempt_id,
                "checkpoint_id": checkpoint_id,
                "replacement_attempt_id": replacement_attempt_id,
            },
        )
        return self.get_plan_execution(execution_id, conn)

    # -------------------------------------------------------------------------
    # 7. Asynchronous Completion Ingress
    # -------------------------------------------------------------------------

    def reconcile_node_completion(
        self,
        result: EngineInvocationResult,
        actor: PipelineActorContext,
        uow_factory: Callable[[], SQLiteUnitOfWork],
    ) -> ExecutionOutcome:
        """Asynchronously reconciles completion posted by an engine worker into the Pipeline DAG

        and autonomously drives DAG execution forward to its next physical state.
        """
        with uow_factory() as uow_find:
            cur = uow_find.connection.execute(
                """
                SELECT ne.*, pe.plan_id, pe.plan_fingerprint, pe.initialization_fingerprint, pe.start_operation_id
                FROM node_executions ne
                JOIN plan_executions pe ON ne.execution_id = pe.execution_id
                WHERE ne.current_attempt_id = ? OR ne.current_invocation_id = ?
                """,
                (result.attempt_id, result.invocation_id),
            )
            row = cur.fetchone()
            if not row:
                return ExecutionOutcome(
                    is_success=False,
                    status="FAILED",
                    error_category=IPCErrorCategory.INVALID_REQUEST,
                    error_code="NODE_NOT_FOUND",
                    error_message=f"No active node execution found for attempt {result.attempt_id!r}.",
                )

            execution_id = row["execution_id"]
            node_exec_id = row["node_execution_id"]
            graph_node_id = row["graph_node_id"]
            init_fp = row["initialization_fingerprint"]
            plan_id = row["plan_id"]
            binding_id = row["binding_id"]
            contract_version = row["contract_version"] or "1.0.0"
            migration_id = row["migration_id"]
            start_op_id = row["start_operation_id"]

            if not start_op_id:
                cur_op = uow_find.connection.execute(
                    "SELECT operation_id FROM operation_journal WHERE status = 'ACCEPTED' ORDER BY rowid DESC LIMIT 1"
                )
                op_row = cur_op.fetchone()
                start_op_id = op_row["operation_id"] if op_row else f"op-start-{execution_id}"

            plan_art_cur = uow_find.connection.execute(
                "SELECT content FROM immutable_artifacts WHERE artifact_id = ? OR artifact_id = ?",
                (f"art-{plan_id}", plan_id),
            )
            plan_row = plan_art_cur.fetchone()
            if not plan_row:
                return ExecutionOutcome(
                    is_success=False,
                    status="FAILED",
                    error_category=IPCErrorCategory.INTERNAL_ERROR,
                    error_code="PLAN_NOT_FOUND",
                    error_message=f"Plan artifact {plan_id!r} not found.",
                )
            plan = ExecutionPlan.from_dict(json.loads(plan_row["content"]))

        try:
            with uow_factory() as uow_recon:
                reconciled = self.result_reconciler.reconcile_result(
                    result,
                    expected_initialization_fingerprint=init_fp,
                    conn=uow_recon.connection,
                    expected_invocation_id=row["current_invocation_id"],
                    expected_attempt_id=row["current_attempt_id"],
                    expected_lease_id=row["lease_id"],
                    expected_graph_node_id=graph_node_id,
                    expected_binding_id=binding_id,
                    expected_contract_version=contract_version,
                )
                now_str = datetime.now(timezone.utc).isoformat()

                if reconciled.get("status") == "SUCCEEDED":
                    uow_recon.connection.execute(
                        """
                        UPDATE node_executions SET
                            state = ?, result_payload = ?, updated_at = ?
                        WHERE node_execution_id = ?
                        """,
                        (
                            NodeExecutionState.SUCCEEDED.value,
                            json.dumps(reconciled.get("result_payload", {})),
                            now_str,
                            node_exec_id,
                        ),
                    )
                    evt_succ = DomainEvent.create(
                        migration_id,
                        "node.succeeded",
                        {
                            "execution_id": execution_id,
                            "graph_node_id": graph_node_id,
                            "attempt_id": result.attempt_id,
                            "invocation_id": result.invocation_id,
                        },
                    )
                    self.outbox_service.stage_event(evt_succ, uow_recon.connection)
                    self.audit_service.record_event(
                        actor,
                        "node.succeeded",
                        graph_node_id,
                        uow_recon.connection,
                        details={"execution_id": execution_id, "attempt_id": result.attempt_id},
                    )

                    # Evaluate & activate newly ready successors
                    self._evaluate_and_activate_successors(execution_id, plan, actor, uow_recon)

                    # Check if all plan nodes are now SUCCEEDED
                    cur_all = uow_recon.connection.execute(
                        "SELECT state FROM node_executions WHERE execution_id = ?",
                        (execution_id,),
                    )
                    all_states = [r["state"] for r in cur_all.fetchall()]
                    if len(all_states) == len(plan.nodes) and all(s == NodeExecutionState.SUCCEEDED.value for s in all_states):
                        self._mark_plan_succeeded(
                            execution_id=execution_id,
                            plan=plan,
                            actor=actor,
                            operation_id=start_op_id,
                            correlation_id=f"corr-term-{uuid.uuid4().hex}",
                            uow=uow_recon,
                        )
                        return ExecutionOutcome(is_success=True, status="SUCCEEDED")

                else:
                    err_c = reconciled.get("error_code") or "ENGINE_ERROR"
                    err_m = reconciled.get("error_message") or "Physical engine execution failed."
                    self._mark_node_and_plan_failed(
                        execution_id=execution_id,
                        node_execution_id=node_exec_id,
                        migration_id=migration_id,
                        graph_node_id=graph_node_id,
                        operation_id=start_op_id,
                        error_code=err_c,
                        error_message=err_m,
                        actor=actor,
                        conn=uow_recon.connection,
                        attempt_id=result.attempt_id,
                        invocation_id=result.invocation_id,
                    )
                    return ExecutionOutcome(
                        is_success=False,
                        status="FAILED",
                        error_category=IPCErrorCategory.INTERNAL_ERROR,
                        error_code=err_c,
                        error_message=err_m,
                    )
        except StaleResultError as stale_exc:
            err_code = "STALE_RESULT"
            err_msg = str(stale_exc)
            with uow_factory() as uow_stale:
                self._mark_node_and_plan_failed(
                    execution_id=execution_id,
                    node_execution_id=node_exec_id,
                    migration_id=migration_id,
                    graph_node_id=graph_node_id,
                    operation_id=start_op_id,
                    error_code=err_code,
                    error_message=err_msg,
                    actor=actor,
                    conn=uow_stale.connection,
                    attempt_id=result.attempt_id,
                    invocation_id=result.invocation_id,
                )
            return ExecutionOutcome(
                is_success=False,
                status="FAILED",
                error_category=IPCErrorCategory.STALE_RESULT,
                error_code=err_code,
                error_message=err_msg,
            )

        # Autonomously advance the DAG forward to dispatch newly ready successor nodes
        advance_outcome = self.advance_plan_execution(
            execution_id=execution_id,
            plan=plan,
            actor=actor,
            operation_id=start_op_id,
            correlation_id=f"corr-async-adv-{uuid.uuid4().hex}",
            request_id=f"req-async-adv-{uuid.uuid4().hex}",
            payload={},
            uow_factory=uow_factory,
        )
        return advance_outcome
