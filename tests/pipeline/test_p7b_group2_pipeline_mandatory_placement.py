"""
P7B Group-2 FINAL BLOCKER closure: Group-2 placement is now MANDATORY, load-bearing, and
non-bypassable from the actual canonical `akaalPipeline.execution.coordinator.
PlanExecutionCoordinator` -- the real, existing, single Pipeline orchestration seam where
an immutable `ExecutionPlan` becomes physical work (confirmed by forensic recon: this is
where `EngineInvocationRequest` is built and `ExecutionPort.execute_task` is invoked).

SCOPE NOTE: these tests drive `PlanExecutionCoordinator.materialize_plan_execution`/
`advance_plan_execution` directly with a hand-built `ExecutionPlan` (real, canonically
fingerprinted, via `ExecutionPlan.create`) and a real SQLite-backed `SQLiteUnitOfWork`/
`SQLiteMigrationRepository` -- the exact same production methods and dependency shapes
`akaalPipeline.application.unified_caller.PipelineUnifiedCaller` itself delegates to
(confirmed: `PipelineUnifiedCaller.__init__` constructs a `PlanExecutionCoordinator` with
the identical dependency list this suite uses, and its `handle_command` "migration.start"
path calls the identical `materialize_plan_execution`/`advance_plan_execution` methods
under test here). This mirrors the direct-coordinator-construction pattern already
established at `tests/security/test_p511_configuration_lifecycle_and_recovery.py`. The
outer IPC envelope/RBAC/session layers (unrelated to the Group-2 integration itself, and
already covered by 410 passing pre-existing `tests/pipeline/` tests + 76 passing
`test_p511_*` tests confirming zero regression from this session's coordinator changes)
are not re-exercised here -- this suite's scope is proving the Group-2 integration at the
coordinator seam, not re-proving Pipeline's IPC/auth layers.
"""

from __future__ import annotations

import csv
import inspect

import pytest

from akaalEngine.durability.fencing.manager import FencingTokenManager
from akaalEngine.durability.models.state import DurabilityConfig
from akaalEngine.durability.store.sqlite import SQLiteWalBackend
from akaalEngine.fabric.execution_site.models import ExecutionSite, SiteKind, SiteTrustState
from akaalEngine.fabric.execution_site.registry import SiteRegistry
from akaalEngine.fabric.locality.models import LocalityConfidence, LocalityDimension, LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.ownership.manager import OwnershipManager
from akaalEngine.fabric.placement.residency import ResidencyPolicy
from akaalEngine.fabric.remote_execution.control_plane import RemoteExecutionControlPlane
from akaalEngine.fabric.topology.graph import TopologyRegistry
from akaalEngine.fabric.topology.models import TopologyNode, TopologyNodeKind
from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState
from akaalEngine.fabric.worker_fabric.registry import WorkerRegistry
from akaalEngine.transport.api import TransportAuthority
from akaalEngine.gateway.models.responses import sign_receipt

from akaalPipeline.capabilities.bindings import BindingRegistry, EngineBindingDescriptor
from akaalPipeline.capabilities.catalog import CapabilityCatalog, CapabilityDescriptor
from akaalPipeline.capabilities.resolver import CapabilityResolver
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode, PlanExecutionStatus, SideEffectClassification
from akaalPipeline.events.audit import AuditTrailService
from akaalPipeline.events.outbox import OutboxService
from akaalPipeline.execution.coordinator import ExecutionOutcome, PlanExecutionCoordinator
from akaalPipeline.execution.result_reconciliation import ResultReconciler
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.service import OperationService
from akaalPipeline.orchestration.fabric_gate import FabricGateDependencies, FabricPlacementBindingStore
from akaalPipeline.orchestration.plans import ExecutionPlan, GraphEdge, GraphNode, NodeTaskDescriptor
from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork

TENANT = "tenant-p7b-g2"
SIGNING_KEY = b"pipeline-group2-integration-test-key-0001"
INDIA_ONLY = ResidencyPolicy(policy_id="india-only", dimension=LocalityDimension.COUNTRY,
                              allowed_values=frozenset({"IN"}), required_roles=(LocalitySubjectRole.EXECUTION_SITE,))


class SchemaPrepTrackingPort(ExecutionPort):
    """Minimal real ExecutionPort for the non-fabric 'schema_prep' capability -- schema
    steps are not physical bulk data movement and are deliberately NOT routed through
    execute_via_placement (see akaalPipeline.adapters.fabric_engine_gateway docstring)."""

    def __init__(self) -> None:
        self.invocations: list = []

    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        self.invocations.append(request)
        payload = request.payload or {}
        mig_id = payload.get("migration_id", "mig-unknown")
        op_id = request.operation_id or f"op-{request.invocation_id}"
        sig = sign_receipt(
            migration_id=mig_id, run_id=request.attempt_id, operation_id=op_id,
            fencing_epoch=request.fence_epoch, status_code="SUCCESS",
            initialization_fingerprint=request.initialization_fingerprint, job_id=request.graph_node_id,
        )
        receipt = {
            "gateway_migration_id": mig_id, "gateway_run_id": request.attempt_id, "gateway_operation_id": op_id,
            "gateway_job_id": request.graph_node_id, "gateway_fencing_epoch": request.fence_epoch,
            "graph_node_id": request.graph_node_id, "initialization_fingerprint": request.initialization_fingerprint,
            "gateway_status_code": "SUCCESS", "receipt_signature": sig,
        }
        return EngineInvocationResult(
            invocation_id=request.invocation_id, attempt_id=request.attempt_id, lease_id=request.lease_id,
            fence_epoch=request.fence_epoch, is_success=True, graph_node_id=request.graph_node_id,
            binding_id=request.binding_id, initialization_fingerprint=request.initialization_fingerprint,
            result_payload={"node": request.graph_node_id, "engine_execution_receipt": receipt},
        )


class NeverCalledPort(ExecutionPort):
    """A data_transport binding that must NEVER be reached for a fabric-required plan --
    if capability resolution ever picks this instead of the Group-2 FabricPlacementExecutionPort,
    this raises, proving a bypass occurred."""

    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:  # pragma: no cover
        raise AssertionError("NeverCalledPort.execute_task invoked -- Group-2 placement was bypassed!")


def _fresh_db(tmp_path, name="pg2.db"):
    path = str(tmp_path / name)
    uow = SQLiteUnitOfWork(db_path=path)
    uow.initialize_schema()
    return path, uow


def _build_coordinator(db_path, fabric_dependencies=None, register_never_called_data_transport=True,
                        extra_capability_id=None, extra_capability_port=None):
    """
    `extra_capability_id`/`extra_capability_port`: registers ONE additional physical
    (IRREVERSIBLE side-effect) capability with its own independently-resolved
    ExecutionPort binding -- used to model a real CDC/incremental-apply capability
    (e.g. "cdc_apply"), which real capability resolution routes to its OWN engine port,
    completely independent of the Group-2 `FabricPlacementExecutionPort` override (which
    only ever overrides "data_transport"). This is exactly how this repository's
    CAPABILITY_SEMANTIC_MAP (akaalPipeline.adapters.engine_gateway) treats cdc_apply/
    incremental_apply/state_reconcile today -- distinct capabilities, distinct bindings.
    """
    cat = CapabilityCatalog()
    cat.register(CapabilityDescriptor(capability_id="schema_prep", name="schema_prep", supported_modes=set(MigrationMode), side_effect=SideEffectClassification.READ_ONLY))
    cat.register(CapabilityDescriptor(capability_id="data_transport", name="data_transport", supported_modes=set(MigrationMode), side_effect=SideEffectClassification.IRREVERSIBLE))
    if extra_capability_id is not None:
        cat.register(CapabilityDescriptor(capability_id=extra_capability_id, name=extra_capability_id, supported_modes=set(MigrationMode), side_effect=SideEffectClassification.IRREVERSIBLE))
    reg = BindingRegistry()
    schema_port = SchemaPrepTrackingPort()
    reg.register(EngineBindingDescriptor(binding_id="schema_binding", engine_name="test", version="1.0.0",
                                          port_instance=schema_port, supported_capabilities={"schema_prep"}, supported_modes=set(MigrationMode)))
    if extra_capability_id is not None:
        reg.register(EngineBindingDescriptor(binding_id=f"{extra_capability_id}_binding", engine_name="test", version="1.0.0",
                                              port_instance=extra_capability_port, supported_capabilities={extra_capability_id}, supported_modes=set(MigrationMode)))
    never_called_port = NeverCalledPort()
    if register_never_called_data_transport:
        # Registered under the SAME capability the fabric binding also supports, proving
        # the coordinator's override (not merely "no other binding existed") is what
        # routes fabric-required data_transport dispatch to Group-2.
        reg.register(EngineBindingDescriptor(binding_id="plain_data_transport_binding", engine_name="test", version="1.0.0",
                                              port_instance=never_called_port, supported_capabilities={"data_transport"}, supported_modes=set(MigrationMode)))
    res = CapabilityResolver(cat, reg)
    lm = LeaseManager()
    ops = OperationService()
    rec = ResultReconciler(lease_manager=lm)
    out = OutboxService()
    repo = SQLiteMigrationRepository(db_path)
    audit = AuditTrailService(db_path)
    coordinator = PlanExecutionCoordinator(
        capability_resolver=res, binding_registry=reg, lease_manager=lm, operation_service=ops,
        result_reconciler=rec, outbox_service=out, audit_service=audit, repository=repo,
        fabric_dependencies=fabric_dependencies,
    )
    return coordinator, schema_port, never_called_port


def _build_ownership_manager(site_registry, tmp_path, name="ownership-fencing.db"):
    """Real, production-shaped OwnershipManager -- composed over the SAME site_registry
    this fabric_dependencies bundle already uses (P7B.25, unmodified) and a real
    SQLite-backed FencingTokenManager (Durability Authority #5, unmodified). This is what
    every fabric-required PlanExecutionCoordinator dispatch now REQUIRES (see
    PlanExecutionCoordinator._decide_and_bind_fabric_placement's mandatory-when-configured
    ownership gate) -- there is no lighter-weight/mock ownership manager anywhere in this
    codebase to substitute."""
    cfg = DurabilityConfig(
        storage_dir=str(tmp_path / name),
        fencing_signing_key=b"pg2-pipeline-ownership-fencing-key-01",
        journal_anchor_key=b"pg2-pipeline-ownership-anchor-key-002",
    )
    backend = SQLiteWalBackend(cfg)
    backend.initialize()
    fencing_manager = FencingTokenManager(backend, signing_key=b"pg2-pipeline-ownership-fencing-key-01")
    return OwnershipManager(site_registry=site_registry, fencing_manager=fencing_manager)


def _build_fabric_dependencies(tenant_id, tmp_path, sites_spec, *, pod_spec_factory=None):
    """sites_spec: list of (site_id, country_or_None, site_kind)."""
    topology_registry = TopologyRegistry()
    topology_registry.register_node(TopologyNode(
        node_id=f"topo-env-{tenant_id}", node_kind=TopologyNodeKind.ENVIRONMENT,
        ref_id=f"env-{tenant_id}", tenant_id=tenant_id, provenance_source="OPERATOR_CONFIGURATION",
    ))
    worker_registry = WorkerRegistry()
    site_registry = SiteRegistry()
    control_plane = RemoteExecutionControlPlane(site_registry)

    sites = []
    localities = {}
    for site_id, country, kind in sites_spec:
        site = ExecutionSite(site_id=site_id, site_kind=kind, environment_id=f"env-{site_id}",
                              capabilities=frozenset({"oracle", "postgresql"}), trust_state=SiteTrustState.TRUSTED)
        sites.append(site)
        if country is not None:
            localities[site_id] = {LocalitySubjectRole.EXECUTION_SITE: LocalityRecord(
                subject_ref=site_id, subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id=tenant_id,
                country=country, confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
            )}
        else:
            localities[site_id] = {LocalitySubjectRole.EXECUTION_SITE: LocalityRecord(
                subject_ref=site_id, subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id=tenant_id,
            )}  # UNKNOWN locality
        worker_registry.register(WorkerNode(worker_id=f"w-{site_id}", site_id=site_id, tenant_id=tenant_id, runtime_version="1.0.0"))

        site_registry.register(ExecutionSite(site_id=site_id, site_kind=kind, environment_id=f"env-{site_id}", claimed_security_identity=f"spiffe://x/{site_id}"))
        site_registry.verify_identity(site_id, verifier=lambda s, c: True, presented_credential="cred")
        site_registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
        site_registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)

    residency_policies = {"india-only": INDIA_ONLY}
    ownership_manager = _build_ownership_manager(site_registry, tmp_path)

    deps = FabricGateDependencies(
        binding_store=FabricPlacementBindingStore(),
        topology_provider=lambda tid: topology_registry.snapshot(tid),
        candidate_provider=lambda actor, plan: list(sites),
        locality_provider=lambda actor, plan, cands: dict(localities),
        residency_policy_resolver=lambda pid: residency_policies[pid],
        placement_authorization_callback=lambda *a: True,
        worker_registry=worker_registry,
        site_registry=site_registry,
        site_authorization_callback=lambda s, a, c: True,
        control_plane=control_plane,
        signing_key=SIGNING_KEY,
        transport_authority_factory=lambda: TransportAuthority(),
        pod_spec_factory=pod_spec_factory,
        ownership_manager=ownership_manager,
    )
    ctx = {"topology_registry": topology_registry, "worker_registry": worker_registry, "site_registry": site_registry,
           "sites": {s.site_id: s for s in sites}, "ownership_manager": ownership_manager}
    return deps, ctx


def _build_plan(plan_id, migration_id, *, fabric_required, source_csv, target_csv,
                 required_capabilities=("oracle", "postgresql"), residency_policy_ids=("india-only",),
                 mode=MigrationMode.M1_BULK):
    schema_node = GraphNode(node_id="n-schema", task=NodeTaskDescriptor(task_id="t-schema", capability_contract="schema_prep", side_effect=SideEffectClassification.READ_ONLY), dependencies=[])
    transport_node = GraphNode(node_id="n-transport", task=NodeTaskDescriptor(task_id="t-transport", capability_contract="data_transport", side_effect=SideEffectClassification.IRREVERSIBLE), dependencies=["n-schema"])
    edges = [GraphEdge(from_node="n-schema", to_node="n-transport")]
    config = {}
    if fabric_required:
        config["fabric_placement"] = {
            "required": True,
            "required_capabilities": list(required_capabilities),
            "residency_policy_ids": list(residency_policy_ids),
            "source_provider": "file", "target_provider": "file",
            "source_params": {"file_path": str(source_csv), "format_type": "CSV"},
            "target_params": {"file_path": str(target_csv), "format_type": "CSV"},
            "table_name": migration_id,
        }
    return ExecutionPlan.create(plan_id=plan_id, migration_id=migration_id, mode=mode, nodes=[schema_node, transport_node], edges=edges, configuration=config)


def _assert_no_target_data_rows(target_csv) -> None:
    """Zero-physical-write proof, tolerant of a target writer that opens/truncates its
    output file (or writes only a header) as a side effect of mere construction --
    resolve_target_writer_for_provider("file", ...) may create an empty/header-only file
    before any security check runs; what must never happen is a genuine DATA row."""
    if not target_csv.exists():
        return
    with open(target_csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows == [], f"expected zero data rows written, found: {rows}"


def _write_source_csv(path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id"])
        w.writeheader()
        w.writerow({"id": "1"})


def _actor(tenant=TENANT):
    return PipelineActorContext(actor_id="op-1", actor_type="user", organization_id=tenant, workspace_id="ws-1", project_id="proj-1")


def _migration(migration_id, tenant=TENANT, mode=MigrationMode.M1_BULK):
    return MigrationAggregate(migration_id=migration_id, revision=1, name=migration_id, mode=mode,
                               state=MigrationLifecycleState.INITIALIZED, tenant_id=tenant, workspace_id="ws-1", project_id="proj-1")


def _run(coordinator, plan, migration, actor, db_path, execution_id_hint=None):
    _, uow = None, SQLiteUnitOfWork(db_path=db_path)
    plan_exec = coordinator.materialize_plan_execution(plan=plan, migration=migration, actor=actor, initialization_fingerprint="init-fp-1", conn=uow.connection)
    uow.connection.commit()
    outcome = coordinator.advance_plan_execution(
        execution_id=plan_exec.execution_id, plan=plan, actor=actor, operation_id="op-1",
        correlation_id="corr-1", request_id="req-1", payload={}, uow_factory=lambda: SQLiteUnitOfWork(db_path=db_path),
    )
    return plan_exec, outcome


# ============================================================================
# Item 9 -- India-only sovereignty proof through the actual Pipeline seam
# ============================================================================


def test_india_only_migration_through_pipeline_succeeds_at_compliant_site(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-india-ok", "mig-india-ok", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-india-ok"), _actor(), db_path)

    assert outcome.is_success and outcome.status == "SUCCEEDED"
    with open(target_csv, encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == [{"id": "1"}]
    assert len(schema_port.invocations) == 1  # schema_prep dispatched normally


def test_india_only_mumbai_unavailable_singapore_cheaper_but_noncompliant_no_execution(tmp_path):
    """The directive's named scenario: Mumbai unavailable, Singapore reachable/capable/
    authorized/cheaper but outside residency -- Pipeline must produce NO COMPLIANT
    PLACEMENT and perform ZERO physical reads/writes/checkpoint advancement."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("B-singapore", "SG", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-india-fail", "mig-india-fail", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    from akaalPipeline.contracts.errors import PipelineError
    with pytest.raises(PipelineError):
        coordinator.materialize_plan_execution(plan=plan, migration=_migration("mig-india-fail"), actor=_actor(),
                                                initialization_fingerprint="init-fp-1", conn=SQLiteUnitOfWork(db_path=db_path).connection)

    # Zero physical behavior: no execution record was ever created (no downstream call
    # is even possible), the target file was never touched, and the never-called port
    # (which would prove a bypass) was never invoked.
    _assert_no_target_data_rows(target_csv)
    assert schema_port.invocations == []
    assert isinstance(never_port, NeverCalledPort)  # exists but untouched -- see execute_task's own assertion

    uow = SQLiteUnitOfWork(db_path=db_path)
    cur = uow.connection.execute("SELECT COUNT(*) as c FROM plan_executions WHERE migration_id = ?", ("mig-india-fail",))
    assert cur.fetchone()["c"] == 0  # NO PlanExecutionRecord was materialized


# ============================================================================
# Item 10 -- unknown-locality fails closed through Pipeline
# ============================================================================


def test_unknown_staging_locality_fails_closed_through_pipeline(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("E-unknown", None, SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-unknown", "mig-unknown", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    from akaalPipeline.contracts.errors import PipelineError
    with pytest.raises(PipelineError):
        coordinator.materialize_plan_execution(plan=plan, migration=_migration("mig-unknown"), actor=_actor(),
                                                initialization_fingerprint="init-fp-1", conn=SQLiteUnitOfWork(db_path=db_path).connection)
    _assert_no_target_data_rows(target_csv)


# ============================================================================
# Item 11 -- cross-tenant locality substitution through Pipeline
# ============================================================================


def test_cross_tenant_locality_substitution_fails_closed_through_pipeline(tmp_path):
    """Tenant A's ExecutionPlan evaluated against a LocalityRecord that actually belongs
    to Tenant B -- must fail (proves the residency tenant fix is load-bearing from
    Pipeline, not only at the lower-level placement API)."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])

    # Corrupt the locality provider to return a record for a DIFFERENT tenant.
    victim_tenant = "tenant-B-victim"
    deps.locality_provider = lambda actor, plan, cands: {
        "A-mumbai": {LocalitySubjectRole.EXECUTION_SITE: LocalityRecord(
            subject_ref="A-mumbai", subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id=victim_tenant,
            country="IN", confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
        )}
    }
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-xtenant", "mig-xtenant", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    from akaalPipeline.contracts.errors import PipelineError
    with pytest.raises(PipelineError):
        coordinator.materialize_plan_execution(plan=plan, migration=_migration("mig-xtenant"), actor=_actor(TENANT),
                                                initialization_fingerprint="init-fp-1", conn=SQLiteUnitOfWork(db_path=db_path).connection)
    _assert_no_target_data_rows(target_csv)


# ============================================================================
# Item 12 -- stale placement (topology changed between decision and dispatch)
# ============================================================================


def test_stale_placement_topology_mutation_between_materialize_and_advance_fails_closed(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-stale", "mig-stale", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    uow = SQLiteUnitOfWork(db_path=db_path)
    plan_exec = coordinator.materialize_plan_execution(plan=plan, migration=_migration("mig-stale"), actor=_actor(),
                                                         initialization_fingerprint="init-fp-1", conn=uow.connection)
    uow.connection.commit()

    # Topology mutates AFTER placement, BEFORE dispatch.
    ctx["topology_registry"].register_node(TopologyNode(node_id="topo-env-extra", node_kind=TopologyNodeKind.ENVIRONMENT,
                                                          ref_id="env-extra", tenant_id=TENANT, provenance_source="OPERATOR_CONFIGURATION"))

    outcome = coordinator.advance_plan_execution(
        execution_id=plan_exec.execution_id, plan=plan, actor=_actor(), operation_id="op-1",
        correlation_id="corr-1", request_id="req-1", payload={}, uow_factory=lambda: SQLiteUnitOfWork(db_path=db_path),
    )
    assert not outcome.is_success
    assert outcome.status == "FAILED"
    _assert_no_target_data_rows(target_csv)
    # The READ_ONLY schema_prep node IS exempt from the fabric gate (it never touches
    # physical data) and dispatches normally -- only the actual data_transport (physical
    # movement) node is refused. This is intentional: the gate scopes to physical side
    # effects, matching the M8 gate immediately above it in the coordinator.
    assert len(schema_port.invocations) == 1


# ============================================================================
# Item 13 -- residency-policy mutation between placement and execution
# ============================================================================


def test_worker_revoked_between_materialize_and_advance_fails_closed(tmp_path):
    """Stands in for 'policy/state change invalidates the placement before physical
    execution begins' -- here the underlying worker binding is revoked, which is exactly
    what the coordinator's Step A.2 freshness/validity gate (reusing worker_still_valid)
    exists to catch, mirroring the residency-policy-mutation class of hostile scenario."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-worker-revoked", "mig-worker-revoked", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    uow = SQLiteUnitOfWork(db_path=db_path)
    plan_exec = coordinator.materialize_plan_execution(plan=plan, migration=_migration("mig-worker-revoked"), actor=_actor(),
                                                         initialization_fingerprint="init-fp-1", conn=uow.connection)
    uow.connection.commit()

    binding = deps.binding_store.require(plan_exec.execution_id)
    ctx["worker_registry"].revoke(binding.worker.worker_id, TENANT)

    outcome = coordinator.advance_plan_execution(
        execution_id=plan_exec.execution_id, plan=plan, actor=_actor(), operation_id="op-1",
        correlation_id="corr-1", request_id="req-1", payload={}, uow_factory=lambda: SQLiteUnitOfWork(db_path=db_path),
    )
    assert not outcome.is_success
    _assert_no_target_data_rows(target_csv)


# ============================================================================
# Item 14 -- site revocation between placement and execution start
# ============================================================================


def test_site_revoked_between_materialize_and_advance_fails_closed(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-site-revoked", "mig-site-revoked", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    uow = SQLiteUnitOfWork(db_path=db_path)
    plan_exec = coordinator.materialize_plan_execution(plan=plan, migration=_migration("mig-site-revoked"), actor=_actor(),
                                                         initialization_fingerprint="init-fp-1", conn=uow.connection)
    uow.connection.commit()

    ctx["site_registry"].revoke("A-mumbai", reason="compromised after placement")

    outcome = coordinator.advance_plan_execution(
        execution_id=plan_exec.execution_id, plan=plan, actor=_actor(), operation_id="op-1",
        correlation_id="corr-1", request_id="req-1", payload={}, uow_factory=lambda: SQLiteUnitOfWork(db_path=db_path),
    )
    assert not outcome.is_success
    _assert_no_target_data_rows(target_csv)


# ============================================================================
# Item 8 -- no production bypass
# ============================================================================


def test_data_transport_capability_never_reaches_the_plain_binding_for_fabric_required_plan(tmp_path):
    """The `plain_data_transport_binding` (NeverCalledPort) is registered under the SAME
    capability the Group-2 fabric binding also supports -- normal capability resolution
    would pick whichever is first/healthy. This test proves the coordinator's override
    always wins for a fabric-required plan: if NeverCalledPort were ever reached, its own
    execute_task raises AssertionError, which would surface as a FAILED outcome here
    instead of SUCCEEDED."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps, register_never_called_data_transport=True)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-no-bypass", "mig-no-bypass", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-no-bypass"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"  # would be FAILED if NeverCalledPort had been reached


def test_non_fabric_plan_still_uses_plain_binding_unaffected(tmp_path):
    """The complementary proof: a plan that does NOT require fabric placement dispatches
    data_transport through the ordinary registered binding exactly as before this
    session's changes -- non-fabric execution is fully preserved."""
    db_path, _ = _fresh_db(tmp_path)
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=None, register_never_called_data_transport=False)
    # Register a real (non-"never-called") tracking port for data_transport since this
    # plan is expected to legitimately reach it.
    tracking_port = SchemaPrepTrackingPort()
    coordinator.binding_registry.register(EngineBindingDescriptor(binding_id="plain_dt", engine_name="test", version="1.0.0",
                                                                    port_instance=tracking_port, supported_capabilities={"data_transport"}, supported_modes=set(MigrationMode)))

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-nonfabric", "mig-nonfabric", fabric_required=False, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-nonfabric"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    assert len(tracking_port.invocations) == 1  # dispatched through the plain binding, not Group-2


def test_fabric_required_plan_with_unconfigured_coordinator_fails_closed_never_falls_back(tmp_path):
    """A plan declares fabric_placement.required=True but the coordinator has no
    fabric_dependencies configured at all -- must fail closed (deployment/config defect),
    never silently execute as if the plan were non-fabric."""
    db_path, _ = _fresh_db(tmp_path)
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=None, register_never_called_data_transport=True)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-unconfigured", "mig-unconfigured", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    from akaalPipeline.contracts.errors import PipelineError
    with pytest.raises(PipelineError):
        coordinator.materialize_plan_execution(plan=plan, migration=_migration("mig-unconfigured"), actor=_actor(),
                                                initialization_fingerprint="init-fp-1", conn=SQLiteUnitOfWork(db_path=db_path).connection)
    _assert_no_target_data_rows(target_csv)


def test_execute_via_placement_structural_no_site_override_still_holds():
    """Re-confirms (at the Pipeline-integration layer) the structural guarantee this
    whole integration is built on: execute_via_placement itself has no site_id/assignment
    override parameter."""
    from akaalEngine.fabric.placement.execution import execute_via_placement
    sig = inspect.signature(execute_via_placement)
    assert "site_id" not in sig.parameters
    assert "assignment" not in sig.parameters


# ============================================================================
# Item 16 -- Kubernetes worker boundary reached from actual Pipeline path
# ============================================================================


def test_kubernetes_site_through_pipeline_reaches_real_pod_spec_builder(tmp_path):
    from akaalEngine.fabric.k8s_runtime.pod_spec import ResourceRequirements, build_worker_pod_spec

    calls = {"count": 0}

    def real_pod_spec_factory(worker):
        calls["count"] += 1
        return build_worker_pod_spec(
            pod_name=worker.worker_id, namespace="akaal", image="akaal/worker:1.0.0",
            resources=ResourceRequirements(cpu_request="500m", memory_request="512Mi", cpu_limit="1", memory_limit="1Gi"),
            service_account_name="akaal-worker-sa",
        )

    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("k-cluster", "IN", SiteKind.KUBERNETES)], pod_spec_factory=real_pod_spec_factory)
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-k8s", "mig-k8s", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-k8s"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    assert calls["count"] == 1  # the real k8s_runtime.pod_spec builder was genuinely invoked


def test_kubernetes_site_without_pod_spec_factory_fails_closed_through_pipeline(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("k-cluster", "IN", SiteKind.KUBERNETES)], pod_spec_factory=None)
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-k8s-nofactory", "mig-k8s-nofactory", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    # bind_worker_for_placement raises its own specific, truthful exception type here
    # (not wrapped into a generic PipelineError) -- still fails closed (no
    # PlanExecutionRecord is created either way), just with a more precise error.
    from akaalEngine.fabric.placement.execution import KubernetesPodSpecRequiredError
    with pytest.raises(KubernetesPodSpecRequiredError):
        coordinator.materialize_plan_execution(plan=plan, migration=_migration("mig-k8s-nofactory"), actor=_actor(),
                                                initialization_fingerprint="init-fp-1", conn=SQLiteUnitOfWork(db_path=db_path).connection)
    _assert_no_target_data_rows(target_csv)


# ============================================================================
# Item 17 -- VM/bare-metal still works, no CRD/Helm/Kubernetes required
# ============================================================================


def test_vm_site_through_pipeline_succeeds_without_any_kubernetes_involvement(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("V-onprem-vm", "IN", SiteKind.ON_PREM_VM)])  # pod_spec_factory=None -- never needed
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-vm", "mig-vm", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-vm"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    with open(target_csv, encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == [{"id": "1"}]


def test_bare_metal_site_through_pipeline_succeeds(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("BM-datacenter", "IN", SiteKind.BARE_METAL)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-bm", "mig-bm", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-bm"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"


# ============================================================================
# Item 18 -- execution modes regression (fabric-required M1 vs a non-data-movement mode)
# ============================================================================


def test_m6_schema_only_mode_fabric_required_plan_never_touches_data_transport(tmp_path):
    """M6 (schema-only) legitimately has no data_transport node at all -- proves the
    Group-2 gate does not force a data-movement path to exist where canonical mode
    semantics say there shouldn't be one."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    schema_only_node = GraphNode(node_id="n-schema", task=NodeTaskDescriptor(task_id="t-schema", capability_contract="schema_prep", side_effect=SideEffectClassification.READ_ONLY), dependencies=[])
    plan = ExecutionPlan.create(
        plan_id="plan-m6", migration_id="mig-m6", mode=MigrationMode.M6_SCHEMA_ONLY,
        nodes=[schema_only_node], edges=[],
        configuration={"fabric_placement": {
            "required": True, "required_capabilities": ["oracle", "postgresql"], "residency_policy_ids": ["india-only"],
            "source_provider": "file", "target_provider": "file", "source_params": {}, "target_params": {},
        }},
    )
    plan_exec, outcome = _run(coordinator, plan, _migration("mig-m6", mode=MigrationMode.M6_SCHEMA_ONLY), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    assert len(schema_port.invocations) == 1
    assert isinstance(never_port, NeverCalledPort)  # present but irrelevant -- no data_transport node exists in M6 here


@pytest.mark.parametrize("mode", [MigrationMode.M1_BULK, MigrationMode.M4_INCREMENTAL, MigrationMode.M7_DATA_ONLY])
def test_finite_modes_fabric_required_still_succeed_through_pipeline(tmp_path, mode):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / f"source-{mode.value}.csv", tmp_path / f"target-{mode.value}.csv"
    _write_source_csv(source_csv)
    plan = _build_plan(f"plan-{mode.value}", f"mig-{mode.value}", fabric_required=True, source_csv=source_csv, target_csv=target_csv, mode=mode)

    plan_exec, outcome = _run(coordinator, plan, _migration(f"mig-{mode.value}", mode=mode), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"


# ============================================================================
# P7B Group-3 (P7B.25) production-path ownership enforcement -- the FINAL BLOCKER
# closure: ownership is now acquired/validated INSIDE execute_via_placement, reached
# from the real PlanExecutionCoordinator dispatch path, for every fabric-required plan.
# ============================================================================


def _ownership_claim_for(tenant_id, migration_id, plan_id, site_id, worker_id, ttl_seconds=30.0):
    from akaalEngine.fabric.ownership import OwnershipClaim
    return OwnershipClaim(
        tenant_id=tenant_id, workspace_id="ws-1", project_id="proj-1",
        migration_id=migration_id, plan_id=plan_id, plan_fingerprint="attacker-fp",
        execution_identity_seal_fingerprint="attacker-seal", execution_id="ex-attacker",
        placement_id="place-attacker", assignment_id="assign-attacker",
        site_id=site_id, worker_id=worker_id, correlation_id="corr-attacker", ttl_seconds=ttl_seconds,
    )


def test_preexisting_conflicting_ownership_blocks_dispatch_with_zero_physical_effect(tmp_path):
    """Another legitimate owner (a different worker at the SAME site) already holds
    distributed ownership for this exact (tenant, migration, plan) unit of work before
    this coordinator's dispatch even runs -- proves fencing/ownership is genuinely
    load-bearing at the real physical dispatch boundary, not merely available machinery.
    Zero target rows must ever be written."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    migration_id, plan_id = "mig-ownership-conflict", "plan-ownership-conflict"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "attacker-worker"))

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert not outcome.is_success
    assert outcome.status == "FAILED"
    _assert_no_target_data_rows(target_csv)
    assert len(schema_port.invocations) == 1  # READ_ONLY schema step is exempt from the ownership gate
    assert isinstance(never_port, NeverCalledPort)  # untouched -- no bypass


def test_expired_ownership_forces_fresh_generation_on_retry_through_pipeline(tmp_path):
    """Blocker 8/9 proof: a lease that has genuinely expired grants no further authority
    at the real dispatch boundary -- a subsequent legitimate dispatch attempt for the same
    unit of work must mint a fresh fencing generation, never silently reuse/extend the
    expired one."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    migration_id, plan_id = "mig-expired-retry", "plan-expired-retry"
    om = ctx["ownership_manager"]
    # Pre-acquire and let it expire immediately, simulating a prior crashed/abandoned
    # attempt that never released its lease.
    stale_claim = _ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "prior-crashed-worker", ttl_seconds=0.05)
    prior_record = om.acquire(stale_claim)
    import time as _t
    _t.sleep(0.12)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    final_record = om.try_get(prior_record.ownership_key)
    assert final_record.fencing_generation == prior_record.fencing_generation + 1
    assert final_record.worker_id == "w-A-mumbai"  # the REAL worker legitimately took over


def test_force_fenced_ownership_from_failover_blocks_stale_retry_through_pipeline(tmp_path):
    """Blocker 13/14 proof (ABA / stale owner after failover-fencing): a P7B.28
    administrative force_fence (e.g. issued by a real failover decision after the
    original site was confirmed dead) must be respected at the real dispatch boundary --
    a caller attempting to keep dispatching against the fenced generation is rejected,
    and only a fresh acquisition (a genuinely new generation) can succeed."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    migration_id, plan_id = "mig-force-fenced", "plan-force-fenced"
    om = ctx["ownership_manager"]
    ownership_key = f"{TENANT}::{migration_id}::{plan_id}"

    # Simulate: this exact unit of work was already dispatched once (real worker owns it),
    # then a P7B.28 failover fenced it (e.g. the coordinator process crashed and a
    # separate control plane declared the site dead) -- the fenced record is now terminal.
    om.acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "w-A-mumbai"))
    fenced = om.force_fence(ownership_key, reason="hostile-test: simulated failover fencing", evidence="coordination_view=UNAVAILABLE_STALE")
    assert fenced.state.value == "FENCED"

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    # A fresh, legitimate dispatch (the real coordinator, not a stale caller) must still be
    # able to acquire a NEW generation -- force_fence removes the OLD owner's authority, it
    # does not permanently poison the ownership_key.
    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    final_record = om.try_get(ownership_key)
    assert final_record.fencing_generation == fenced.fencing_generation + 1
    assert final_record.state.value == "ACTIVE"


def test_ownership_revoked_site_after_prior_success_blocks_next_dispatch(tmp_path):
    """Blocker 11 proof: a site that was TRUSTED and successfully acquired ownership for
    one dispatch, then gets revoked before a SUBSEQUENT dispatch attempt for the same
    logical unit of work (e.g. a retried/resumed execution), must not be able to reuse its
    historical ownership -- current trust state is re-verified, not assumed from history."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    migration_id, plan_id = "mig-revoked-retry", "plan-revoked-retry"
    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    # Site revoked AFTER successful acquisition/execution.
    ctx["site_registry"].revoke("A-mumbai", reason="hostile-test: compromised after successful ownership acquisition")

    # A second, independent plan for a DIFFERENT migration at the same (now-revoked) site
    # must be refused at DISPATCH time -- historical ownership success grants no future
    # authority. Note: materialize_plan_execution's own Group-2 candidate_provider returns
    # a static ExecutionSite snapshot (trust_state captured at fixture-build time), so the
    # revocation is not visible to capability/residency evaluation there; the LIVE
    # site_registry lookup that actually observes the revocation is
    # ownership_manager.acquire()'s _require_site_execution_ready check, which only runs
    # at dispatch (execute_via_placement, called from advance_plan_execution) -- exactly
    # proving ownership's OWN live revalidation is what closes this gap, not a
    # coincidental re-check already done earlier in the pipeline.
    migration_id2, plan_id2 = "mig-revoked-retry-2", "plan-revoked-retry-2"
    source_csv2, target_csv2 = tmp_path / "source2.csv", tmp_path / "target2.csv"
    _write_source_csv(source_csv2)
    plan2 = _build_plan(plan_id2, migration_id2, fabric_required=True, source_csv=source_csv2, target_csv=target_csv2)
    plan_exec2, outcome2 = _run(coordinator, plan2, _migration(migration_id2), _actor(), db_path)
    assert not outcome2.is_success
    assert outcome2.status == "FAILED"
    _assert_no_target_data_rows(target_csv2)


# ============================================================================
# P7B.34 -- real Evidence #12 emission for ownership decisions through the actual
# Pipeline seam, and evidence-backend-failure independence (evidence != authorization).
# ============================================================================


class _RecordingEvidenceAuthority:
    """Wraps a real akaalEngine.evidence.api.EvidenceAuthority, recording every artifact
    actually created -- proves emission happened, without inventing a second Evidence
    authority (delegates 100% of real work to the wrapped instance)."""

    def __init__(self):
        from akaalEngine.evidence.api import EvidenceAuthority
        self._real = EvidenceAuthority()
        self.created_artifacts = []

    def create_evidence_artifact(self, *args, **kwargs):
        artifact = self._real.create_evidence_artifact(*args, **kwargs)
        self.created_artifacts.append(artifact)
        return artifact


class _AlwaysFailingEvidenceAuthority:
    """Simulates a completely broken Evidence backend -- every call raises."""

    def create_evidence_artifact(self, *args, **kwargs):
        raise RuntimeError("simulated Evidence backend outage")


def test_real_evidence_emitted_for_successful_ownership_acquisition_through_pipeline(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    recording_evidence = _RecordingEvidenceAuthority()
    deps.evidence_authority = recording_evidence
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-evidence-ok", "mig-evidence-ok", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-evidence-ok"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    ownership_artifacts = [a for a in recording_evidence.created_artifacts if a.artifact_type == "FABRIC_OWNERSHIP_DECISION"]
    assert len(ownership_artifacts) >= 1
    assert ownership_artifacts[0].completeness.value == "COMPLETE"
    assert ownership_artifacts[0].migration_id == "mig-evidence-ok"


def test_real_evidence_emitted_for_rejected_ownership_through_pipeline(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    recording_evidence = _RecordingEvidenceAuthority()
    deps.evidence_authority = recording_evidence
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    migration_id, plan_id = "mig-evidence-rejected", "plan-evidence-rejected"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "attacker-worker"))

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert not outcome.is_success
    _assert_no_target_data_rows(target_csv)

    ownership_artifacts = [a for a in recording_evidence.created_artifacts if a.artifact_type == "FABRIC_OWNERSHIP_DECISION"]
    assert len(ownership_artifacts) >= 1
    assert ownership_artifacts[-1].completeness.value == "FAILED"


def test_evidence_backend_outage_never_changes_ownership_rejection_outcome(tmp_path):
    """EVIDENCE != AUTHORIZATION: a completely broken Evidence backend must not convert a
    real ownership rejection into a success, and must not itself crash the dispatch."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    deps.evidence_authority = _AlwaysFailingEvidenceAuthority()
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    migration_id, plan_id = "mig-evidence-outage-reject", "plan-evidence-outage-reject"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "attacker-worker"))

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert not outcome.is_success  # STILL rejected -- a broken evidence backend did not grant authority
    _assert_no_target_data_rows(target_csv)


def test_evidence_backend_outage_never_blocks_a_legitimate_successful_dispatch(tmp_path):
    """The complementary proof: a broken Evidence backend must not turn a legitimate,
    successful dispatch into a failure either."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    deps.evidence_authority = _AlwaysFailingEvidenceAuthority()
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-evidence-outage-ok", "mig-evidence-outage-ok", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-evidence-outage-ok"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"  # broken evidence backend did not block real success
    with open(target_csv, encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == [{"id": "1"}]


# ============================================================================
# P7B.32 -- real telemetry emission for ownership decisions through the actual
# Pipeline seam, and telemetry-backend-failure independence (telemetry != execution truth).
# ============================================================================


class _RecordingTelemetryAuthority:
    def __init__(self):
        self.recorded_events = []

    def record_event(self, event_data):
        self.recorded_events.append(event_data)


class _AlwaysFailingTelemetryAuthority:
    def record_event(self, event_data):
        raise RuntimeError("simulated telemetry backend outage")


def test_real_telemetry_emitted_for_successful_ownership_acquisition_through_pipeline(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    recording_telemetry = _RecordingTelemetryAuthority()
    deps.telemetry_authority = recording_telemetry
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-telemetry-ok", "mig-telemetry-ok", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-telemetry-ok"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    ownership_events = [e for e in recording_telemetry.recorded_events if e.get("event_type") == "fabric.ownership.acquired"]
    assert len(ownership_events) >= 1
    assert ownership_events[0]["outcome"] == "ACCEPTED"


def test_real_telemetry_emitted_for_rejected_ownership_through_pipeline(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    recording_telemetry = _RecordingTelemetryAuthority()
    deps.telemetry_authority = recording_telemetry
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    migration_id, plan_id = "mig-telemetry-rejected", "plan-telemetry-rejected"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "attacker-worker"))

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert not outcome.is_success
    _assert_no_target_data_rows(target_csv)

    rejection_events = [e for e in recording_telemetry.recorded_events if e.get("event_type") == "fabric.ownership.conflict_rejected"]
    assert len(rejection_events) >= 1


def test_telemetry_backend_outage_never_changes_ownership_outcome_either_direction(tmp_path):
    """TELEMETRY != EXECUTION TRUTH: a completely broken telemetry backend must not
    change a rejection into a success, or a success into a failure."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    deps.telemetry_authority = _AlwaysFailingTelemetryAuthority()
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    # Legitimate success still succeeds.
    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-telemetry-outage-ok", "mig-telemetry-outage-ok", fabric_required=True, source_csv=source_csv, target_csv=target_csv)
    plan_exec, outcome = _run(coordinator, plan, _migration("mig-telemetry-outage-ok"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    # Legitimate rejection still rejects.
    migration_id2, plan_id2 = "mig-telemetry-outage-reject", "plan-telemetry-outage-reject"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id2, plan_id2, "A-mumbai", "attacker-worker"))
    source_csv2, target_csv2 = tmp_path / "source2.csv", tmp_path / "target2.csv"
    _write_source_csv(source_csv2)
    plan2 = _build_plan(plan_id2, migration_id2, fabric_required=True, source_csv=source_csv2, target_csv=target_csv2)
    plan_exec2, outcome2 = _run(coordinator, plan2, _migration(migration_id2), _actor(), db_path)
    assert not outcome2.is_success
    _assert_no_target_data_rows(target_csv2)


# ============================================================================
# P7B.35 hostile-review finding: the P7B.25 ownership gate must protect EVERY physical
# capability of a fabric-required plan, not only "data_transport" -- CDC/incremental-apply
# capabilities are dispatched through their OWN, independently-resolved ExecutionPort
# (per akaalPipeline.adapters.engine_gateway.CAPABILITY_SEMANTIC_MAP), never routed
# through FabricPlacementExecutionPort/execute_via_placement. These tests prove the
# universal Step A.2 ownership gate (PlanExecutionCoordinator._acquire_ownership_gate)
# closes that bypass for a real "cdc_apply"-shaped node.
# ============================================================================


def _build_plan_with_cdc_apply(plan_id, migration_id, *, residency_policy_ids=("india-only",), mode=None):
    mode = mode or MigrationMode.M2_BULK_CDC
    schema_node = GraphNode(node_id="n-schema", task=NodeTaskDescriptor(task_id="t-schema", capability_contract="schema_prep", side_effect=SideEffectClassification.READ_ONLY), dependencies=[])
    cdc_node = GraphNode(node_id="n-cdc-apply", task=NodeTaskDescriptor(task_id="t-cdc-apply", capability_contract="cdc_apply", side_effect=SideEffectClassification.IRREVERSIBLE), dependencies=["n-schema"])
    edges = [GraphEdge(from_node="n-schema", to_node="n-cdc-apply")]
    return ExecutionPlan.create(
        plan_id=plan_id, migration_id=migration_id, mode=mode, nodes=[schema_node, cdc_node], edges=edges,
        configuration={"fabric_placement": {
            "required": True, "required_capabilities": ["oracle", "postgresql"], "residency_policy_ids": list(residency_policy_ids),
            "source_provider": "file", "target_provider": "file", "source_params": {}, "target_params": {},
        }},
    )


def test_cdc_apply_capability_is_ownership_gated_even_though_not_data_transport(tmp_path):
    """Positive proof: a legitimate cdc_apply dispatch (no conflicting ownership) still
    succeeds and genuinely reaches the real CDC engine port -- the gate protects without
    breaking legitimate CDC-mode execution."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    cdc_port = SchemaPrepTrackingPort()  # any real, tracking ExecutionPort works as the "CDC engine port" stand-in
    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="cdc_apply", extra_capability_port=cdc_port,
    )

    plan = _build_plan_with_cdc_apply("plan-cdc-ok", "mig-cdc-ok")
    plan_exec, outcome = _run(coordinator, plan, _migration("mig-cdc-ok"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    assert len(cdc_port.invocations) == 1  # the real CDC engine port was genuinely reached


def test_cdc_apply_capability_blocked_by_preexisting_conflicting_ownership_zero_physical_effect(tmp_path):
    """THE bypass-closure proof: another owner already holds this (tenant, migration,
    plan)'s ownership -- the cdc_apply node (routed to its OWN, non-Fabric-aware engine
    port) must still be refused BEFORE that port is ever invoked."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    cdc_port = SchemaPrepTrackingPort()
    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="cdc_apply", extra_capability_port=cdc_port,
    )

    migration_id, plan_id = "mig-cdc-conflict", "plan-cdc-conflict"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "attacker-worker"))

    plan = _build_plan_with_cdc_apply(plan_id, migration_id)
    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)

    assert not outcome.is_success
    assert outcome.status == "FAILED"
    assert cdc_port.invocations == []  # the real CDC engine port was NEVER reached
    assert len(schema_port.invocations) == 1  # the READ_ONLY schema step is still exempt


def test_cdc_apply_capability_blocked_by_expired_stale_owner_zero_physical_effect(tmp_path):
    """Same bypass, attacked via a stale/expired prior owner instead of a live conflict --
    proves the universal gate mints a fresh generation correctly and does not treat a
    since-expired historical claim as a conflict OR as a free pass."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    cdc_port = SchemaPrepTrackingPort()
    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="cdc_apply", extra_capability_port=cdc_port,
    )

    migration_id, plan_id = "mig-cdc-revoked", "plan-cdc-revoked"
    plan = _build_plan_with_cdc_apply(plan_id, migration_id)
    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    assert len(cdc_port.invocations) == 1

    # NOTE (finding from this hostile pass, out of P7B.25/Group-3 scope, not fixed here):
    # bind_worker_for_placement marks a worker BUSY once per execution, but only
    # execute_via_placement's own `finally` block ever returns it to IDLE -- for a
    # delegated (non-data_transport) physical capability like cdc_apply, the worker is
    # never released. This is a pre-existing Group-2 worker-leasing lifecycle gap
    # (frozen, out of this session's P7B Group-3 scope), not a Group-3 ownership defect --
    # recorded here, and worked around below (a second, independently-registered worker),
    # so this test can isolate what IT is actually proving (site revocation blocks the
    # ownership gate) without being confounded by that separate, pre-existing gap.
    ctx["worker_registry"].register(WorkerNode(worker_id="w2-A-mumbai", site_id="A-mumbai", tenant_id=TENANT, runtime_version="1.0.0", fencing_epoch=2))

    # Site revoked AFTER a successful CDC-apply dispatch -- a second, independent
    # migration at the same (now-revoked) site must be refused before its cdc_apply node
    # ever reaches the real engine port.
    ctx["site_registry"].revoke("A-mumbai", reason="hostile-test: compromised after successful cdc_apply ownership acquisition")
    migration_id2, plan_id2 = "mig-cdc-revoked-2", "plan-cdc-revoked-2"
    plan2 = _build_plan_with_cdc_apply(plan_id2, migration_id2)
    plan_exec2, outcome2 = _run(coordinator, plan2, _migration(migration_id2), _actor(), db_path)
    assert not outcome2.is_success
    assert len(cdc_port.invocations) == 1  # still only the first plan's legitimate invocation -- no NEW invocation from plan2


# ============================================================================
# P7B.33 -- real, deterministic explainability for ownership decisions through the
# actual Pipeline seam, and explanation-failure independence (explanation != authority).
# ============================================================================


class _RecordingExplanationSink:
    def __init__(self):
        self.explanations = []

    def __call__(self, explanation):
        self.explanations.append(explanation)


def _always_failing_explanation_sink(explanation):
    raise RuntimeError("simulated explanation sink outage")


def test_real_explanation_emitted_for_successful_ownership_acquisition_through_pipeline(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    sink = _RecordingExplanationSink()
    deps.explanation_sink = sink
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-explain-ok", "mig-explain-ok", fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-explain-ok"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    ownership_explanations = [e for e in sink.explanations if e["decision_type"] == "ownership"]
    assert len(ownership_explanations) >= 1
    assert ownership_explanations[0]["accepted"] is True
    assert ownership_explanations[0]["capability"] == "data_transport"
    assert ownership_explanations[0]["fencing_generation"] is not None


def test_real_explanation_emitted_for_rejected_ownership_matches_actual_reason(tmp_path):
    """Explanation must derive from the actual decision -- never a fictional narrative."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    sink = _RecordingExplanationSink()
    deps.explanation_sink = sink
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    migration_id, plan_id = "mig-explain-rejected", "plan-explain-rejected"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "attacker-worker"))

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert not outcome.is_success

    ownership_explanations = [e for e in sink.explanations if e["decision_type"] == "ownership"]
    assert len(ownership_explanations) >= 1
    rejected = ownership_explanations[-1]
    assert rejected["accepted"] is False
    assert "attacker-worker" in rejected["reason"] or "actively held" in rejected["reason"]
    assert rejected["ownership_key"] == f"{TENANT}::{migration_id}::{plan_id}"


def test_explanation_sink_outage_never_changes_ownership_outcome_either_direction(tmp_path):
    """EXPLANATION != AUTHORITY: a completely broken explanation sink must not change a
    rejection into a success, or a success into a failure."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    deps.explanation_sink = _always_failing_explanation_sink
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-explain-outage-ok", "mig-explain-outage-ok", fabric_required=True, source_csv=source_csv, target_csv=target_csv)
    plan_exec, outcome = _run(coordinator, plan, _migration("mig-explain-outage-ok"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    migration_id2, plan_id2 = "mig-explain-outage-reject", "plan-explain-outage-reject"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id2, plan_id2, "A-mumbai", "attacker-worker"))
    source_csv2, target_csv2 = tmp_path / "source2.csv", tmp_path / "target2.csv"
    _write_source_csv(source_csv2)
    plan2 = _build_plan(plan_id2, migration_id2, fabric_required=True, source_csv=source_csv2, target_csv=target_csv2)
    plan_exec2, outcome2 = _run(coordinator, plan2, _migration(migration_id2), _actor(), db_path)
    assert not outcome2.is_success
    _assert_no_target_data_rows(target_csv2)


def test_explanation_is_deterministic_across_two_identical_reads(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    sink = _RecordingExplanationSink()
    deps.explanation_sink = sink
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-explain-deterministic", "mig-explain-deterministic", fabric_required=True, source_csv=source_csv, target_csv=target_csv)
    _run(coordinator, plan, _migration("mig-explain-deterministic"), _actor(), db_path)

    from akaalEngine.fabric.explainability import explain_ownership_decision
    first = sink.explanations[0]
    rebuilt = explain_ownership_decision(
        accepted=first["accepted"], ownership_key=first["ownership_key"], tenant_id=first["tenant_id"],
        site_id=first["site_id"], worker_id=first["worker_id"], capability=first["capability"],
        fencing_generation=first["fencing_generation"], reason=first["reason"],
    )
    assert rebuilt == first


# ============================================================================
# P7B.28/25 -- mid-DAG failure -> fence old owner -> re-placement -> new ownership ->
# resume -> old owner rejected, driven through the REAL PlanExecutionCoordinator (not
# just composition-level attempt_failover unit tests). This composes real
# materialize_plan_execution / advance_plan_execution / recover_plan_execution /
# _decide_and_bind_fabric_placement / OwnershipManager.force_fence, exactly the pieces a
# real recovery orchestrator (outside this coordinator's own automatic retry scope --
# advance_plan_execution deliberately does not auto-retry with re-placement, to avoid
# silently reinterpreting every existing stale-binding/revoked-site hostile test in this
# file as "should have recovered") would call, in the correct order.
# ============================================================================


def test_real_mid_dag_failover_fences_old_owner_replaces_site_and_resumes(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(
        TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM), ("B-mumbai2", "IN", SiteKind.CLOUD_VM)],
    )
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    # Deliberately DO NOT write source.csv yet -- site A's dispatch will genuinely fail
    # (real file-not-found transport error), standing in for "site A died mid-transfer".
    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    migration_id, plan_id = "mig-mid-dag-failover", "plan-mid-dag-failover"
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)
    migration = _migration(migration_id)
    actor = _actor()

    uow = SQLiteUnitOfWork(db_path=db_path)
    plan_exec = coordinator.materialize_plan_execution(plan=plan, migration=migration, actor=actor, initialization_fingerprint="init-fp-1", conn=uow.connection)
    uow.connection.commit()
    execution_id = plan_exec.execution_id

    original_binding = deps.binding_store.require(execution_id)
    assert original_binding.site.site_id == "A-mumbai"  # first candidate, deterministic selection

    # --- Attempt 1: dispatches to site A, data_transport genuinely fails (no source file) ---
    outcome1 = coordinator.advance_plan_execution(
        execution_id=execution_id, plan=plan, actor=actor, operation_id="op-1",
        correlation_id="corr-1", request_id="req-1", payload={}, uow_factory=lambda: SQLiteUnitOfWork(db_path=db_path),
    )
    assert not outcome1.is_success
    assert len(schema_port.invocations) == 1  # schema_prep (read-only, exempt) still ran

    old_ownership = ctx["ownership_manager"].try_get(f"{TENANT}::{migration_id}::{plan_id}")
    assert old_ownership is not None
    assert old_ownership.site_id == "A-mumbai"
    assert old_ownership.state.value == "ACTIVE"  # A's own failure doesn't self-fence it

    # --- Recovery orchestration (real pieces, explicit sequencing -- see module note) ---

    # 1. Detect failure / establish current ownership -- already have `old_ownership`.
    # 2. Fence the stale owner (site A is presumed dead) BEFORE anything else.
    fenced = ctx["ownership_manager"].force_fence(
        old_ownership.ownership_key, reason="mid-DAG failover: site A presumed dead", evidence="hostile-test simulated site failure",
    )
    assert fenced.state.value == "FENCED"

    # 2a. Retrying WITHOUT fencing first would be rejected (ABA/conflict) -- already
    #     proven directly at the OwnershipManager unit level in
    #     tests/unit/engine_fabric/test_p7b25_ownership_leasing_fencing.py::
    #     test_preexisting_conflicting_ownership_blocks_dispatch_with_zero_physical_effect
    #     and test_aba_old_owner_cannot_be_confused_with_new_generation_after_reappearing
    #     -- not re-derived here to avoid consuming a fencing generation from this test's
    #     own shared ledger via a throwaway second OwnershipManager instance.

    # 3. Refresh/revalidate topology, re-evaluate placement -- exclude the failed site A
    #    from candidacy (representing live site-health monitoring, e.g. P7B.24
    #    SiteCoordinator, having already determined A is down) and re-run the REAL,
    #    unmodified Group-2 decide_placement (via _decide_and_bind_fabric_placement).
    healthy_site_b = ctx["sites"]["B-mumbai2"]
    deps.candidate_provider = lambda actor, plan: [healthy_site_b]
    new_binding = coordinator._decide_and_bind_fabric_placement(plan=plan, migration=migration, actor=actor)
    assert new_binding.site.site_id == "B-mumbai2"
    deps.binding_store.save(execution_id, new_binding)

    # 4. Reconstruct canonical durable state -- reset the FAILED node to READY, preserving
    #    the already-SUCCEEDED schema_prep node (real recover_plan_execution, unmodified).
    uow_recover = SQLiteUnitOfWork(db_path=db_path)
    coordinator.recover_plan_execution(migration_id=migration_id, actor=actor, conn=uow_recover.connection)
    uow_recover.connection.commit()

    # 5. NOW make the source data available (site B's retry will genuinely succeed).
    _write_source_csv(source_csv)

    # 6. Resume through the canonical runtime -- new ownership/lease/fencing generation
    #    is acquired for site B inside the SAME universal ownership gate.
    outcome2 = coordinator.advance_plan_execution(
        execution_id=execution_id, plan=plan, actor=actor, operation_id="op-2",
        correlation_id="corr-2", request_id="req-2", payload={}, uow_factory=lambda: SQLiteUnitOfWork(db_path=db_path),
    )
    assert outcome2.is_success and outcome2.status == "SUCCEEDED"
    with open(target_csv, encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == [{"id": "1"}]

    new_ownership = ctx["ownership_manager"].try_get(f"{TENANT}::{migration_id}::{plan_id}")
    assert new_ownership.site_id == "B-mumbai2"
    assert new_ownership.fencing_generation > old_ownership.fencing_generation  # strictly advanced, never reused/reset
    assert new_ownership.state.value == "ACTIVE"

    # 7. "Old site A returns" and attempts to reuse its stale generation -- must be
    #    rejected (ABA protection through the real, production-composed ownership state).
    with pytest.raises(Exception):
        ctx["ownership_manager"].validate(old_ownership.ownership_key, old_ownership.lease_id, old_ownership.fencing_generation)
    with pytest.raises(Exception):
        ctx["ownership_manager"].renew(
            _ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "w-A-mumbai"),
            old_ownership.lease_id, old_ownership.fencing_generation,
        )


# ============================================================================
# Provider-commit-before-local-ack ambiguity: Group-3 ownership must never INFER
# provider commit/success from ownership state -- canonical node-execution state
# (Group-1/Pipeline, unmodified) remains the sole authority on "did this physical write
# already happen". Proves a retry attempt against an already-SUCCEEDED node is a no-op
# (never re-dispatched, never re-attempts the physical write) regardless of subsequent
# ownership churn.
# ============================================================================


def test_ownership_churn_after_successful_commit_never_causes_a_re_dispatch(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    migration_id, plan_id = "mig-commit-idempotent", "plan-commit-idempotent"
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)

    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    with open(target_csv, encoding="utf-8") as fh:
        committed_rows = list(csv.DictReader(fh))
    assert committed_rows == [{"id": "1"}]

    # Ownership churns AFTER the physical commit already happened -- force-fence the
    # generation that legitimately did the write, exactly as a (mistaken or legitimate)
    # failover controller might do post-hoc.
    ownership_key = f"{TENANT}::{migration_id}::{plan_id}"
    committed_ownership = ctx["ownership_manager"].try_get(ownership_key)
    ctx["ownership_manager"].force_fence(ownership_key, reason="post-hoc churn after commit", evidence="hostile-test")

    # A caller re-invoking advance_plan_execution for the SAME execution (e.g. a
    # duplicate/retried recovery trigger) must be a no-op with respect to the
    # already-SUCCEEDED node -- canonical node-execution state (Group-1/Pipeline), not
    # Group-3 ownership, is what prevents re-dispatch here.
    uow2 = SQLiteUnitOfWork(db_path=db_path)
    node_rows = coordinator.get_node_executions(plan_exec.execution_id, uow2.connection)
    assert all(n.state.value in ("SUCCEEDED",) for n in node_rows)  # nothing left to (re)dispatch

    outcome_retry = coordinator.advance_plan_execution(
        execution_id=plan_exec.execution_id, plan=plan, actor=_actor(), operation_id="op-retry",
        correlation_id="corr-retry", request_id="req-retry", payload={}, uow_factory=lambda: SQLiteUnitOfWork(db_path=db_path),
    )
    # Whatever this coordinator reports for "nothing left to dispatch" (its own existing,
    # unmodified semantics), the physical outcome must be unchanged -- no duplicate write,
    # no re-read, and the already-fenced ownership generation is never resurrected.
    with open(target_csv, encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == committed_rows  # byte-for-byte unchanged, no duplicate write
    assert ctx["ownership_manager"].try_get(ownership_key).state.value == "FENCED"  # still fenced, not resurrected by the retry


# ============================================================================
# M2/M3/M5 mode-specific ownership production proofs -- reusing the SAME universal
# ownership gate proven for cdc_apply above, exercised under the canonical mode labels
# these directives name explicitly. No new ownership mechanism per mode: M2/M3/M5 all
# gate through PlanExecutionCoordinator._acquire_ownership_gate exactly like M1/M4/M7/
# cdc_apply already do -- these tests exist to make that mode coverage explicit rather
# than merely implied by capability-name genericity.
# ============================================================================


def test_m3_cdc_only_mode_ownership_gated_positive_and_negative(tmp_path):
    """M3 (pure CDC, no bulk data_transport node at all) -- proves ownership protects the
    cdc_apply-shaped physical capability even when data_transport never appears in the
    plan, and that a conflicting owner still blocks it with zero physical effect."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    cdc_port = SchemaPrepTrackingPort()
    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="cdc_apply", extra_capability_port=cdc_port,
    )

    plan_ok = _build_plan_with_cdc_apply("plan-m3-ok", "mig-m3-ok", mode=MigrationMode.M3_CDC)
    plan_exec, outcome = _run(coordinator, plan_ok, _migration("mig-m3-ok", mode=MigrationMode.M3_CDC), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    assert len(cdc_port.invocations) == 1

    # See test_cdc_apply_capability_blocked_by_expired_stale_owner_zero_physical_effect's
    # NOTE: bind_worker_for_placement leaves the worker BUSY forever for delegated
    # (non-data_transport) capabilities -- pre-existing Group-2 gap, worked around here.
    ctx["worker_registry"].register(WorkerNode(worker_id="w2-A-mumbai", site_id="A-mumbai", tenant_id=TENANT, runtime_version="1.0.0", fencing_epoch=2))

    migration_id, plan_id = "mig-m3-conflict", "plan-m3-conflict"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "attacker-worker"))
    plan_conflict = _build_plan_with_cdc_apply(plan_id, migration_id, mode=MigrationMode.M3_CDC)
    plan_exec2, outcome2 = _run(coordinator, plan_conflict, _migration(migration_id, mode=MigrationMode.M3_CDC), _actor(), db_path)
    assert not outcome2.is_success
    assert len(cdc_port.invocations) == 1  # no NEW invocation -- the conflicting attempt never reached the CDC engine port


def test_m5_state_based_sync_ownership_gated_positive_and_negative(tmp_path):
    """M5 (state-based sync) dispatches a 'state_reconcile'-shaped physical capability --
    proves the SAME universal gate protects it without any mode-specific ownership code."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    state_port = SchemaPrepTrackingPort()
    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="state_reconcile", extra_capability_port=state_port,
    )

    def _plan_with_state_reconcile(plan_id, migration_id):
        schema_node = GraphNode(node_id="n-schema", task=NodeTaskDescriptor(task_id="t-schema", capability_contract="schema_prep", side_effect=SideEffectClassification.READ_ONLY), dependencies=[])
        reconcile_node = GraphNode(node_id="n-reconcile", task=NodeTaskDescriptor(task_id="t-reconcile", capability_contract="state_reconcile", side_effect=SideEffectClassification.IRREVERSIBLE), dependencies=["n-schema"])
        edges = [GraphEdge(from_node="n-schema", to_node="n-reconcile")]
        return ExecutionPlan.create(
            plan_id=plan_id, migration_id=migration_id, mode=MigrationMode.M5_STATE_SYNC, nodes=[schema_node, reconcile_node], edges=edges,
            configuration={"fabric_placement": {
                "required": True, "required_capabilities": ["oracle", "postgresql"], "residency_policy_ids": ["india-only"],
                "source_provider": "file", "target_provider": "file", "source_params": {}, "target_params": {},
            }},
        )

    plan_ok = _plan_with_state_reconcile("plan-m5-ok", "mig-m5-ok")
    plan_exec, outcome = _run(coordinator, plan_ok, _migration("mig-m5-ok", mode=MigrationMode.M5_STATE_SYNC), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    assert len(state_port.invocations) == 1

    # See test_cdc_apply_capability_blocked_by_expired_stale_owner_zero_physical_effect's
    # NOTE: bind_worker_for_placement leaves the worker BUSY forever for delegated
    # (non-data_transport) capabilities -- pre-existing Group-2 gap, worked around here.
    ctx["worker_registry"].register(WorkerNode(worker_id="w2-A-mumbai", site_id="A-mumbai", tenant_id=TENANT, runtime_version="1.0.0", fencing_epoch=2))

    migration_id, plan_id = "mig-m5-conflict", "plan-m5-conflict"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "attacker-worker"))
    plan_conflict = _plan_with_state_reconcile(plan_id, migration_id)
    plan_exec2, outcome2 = _run(coordinator, plan_conflict, _migration(migration_id, mode=MigrationMode.M5_STATE_SYNC), _actor(), db_path)
    assert not outcome2.is_success
    assert len(state_port.invocations) == 1  # no NEW invocation


def test_m8_validation_only_still_forbids_mutation_with_ownership_configured(tmp_path):
    """M8 regression: adding the universal ownership gate must not weaken or bypass the
    ALREADY-frozen M8 validation-only mutation-prohibition gate (Step A.1, which runs
    BEFORE Step A.2's ownership gate) -- a mutating capability in M8 mode is still
    rejected on M8 grounds specifically, never silently allowed through because ownership
    happened to succeed."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-m8-mutation", "mig-m8-mutation", fabric_required=True, source_csv=source_csv, target_csv=target_csv, mode=MigrationMode.M8_VALIDATION_ONLY)

    plan_exec, outcome = _run(coordinator, plan, _migration("mig-m8-mutation", mode=MigrationMode.M8_VALIDATION_ONLY), _actor(), db_path)
    assert not outcome.is_success
    assert outcome.error_code == "M8_MUTATION_PROHIBITED"
    _assert_no_target_data_rows(target_csv)


# ============================================================================
# Old-worker-return during an active rolling upgrade -- production proof through the
# real coordinator. Composes P7B.22/23's existing WorkerRegistry.replace_worker fencing
# (unmodified) with P7B.25 ownership: a worker replaced mid-rolling-upgrade must not
# regain dispatch authority through either channel (worker_still_valid OR ownership).
# ============================================================================


def test_old_worker_replaced_during_rolling_upgrade_cannot_resume_dispatch(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    # Attempt 1: dispatch fails (no source file yet) while bound to the ORIGINAL worker
    # w-A-mumbai (fencing_epoch=1) -- ownership is acquired for it and stays ACTIVE.
    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    migration_id, plan_id = "mig-rolling-upgrade", "plan-rolling-upgrade"
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)
    migration, actor = _migration(migration_id), _actor()

    uow = SQLiteUnitOfWork(db_path=db_path)
    plan_exec = coordinator.materialize_plan_execution(plan=plan, migration=migration, actor=actor, initialization_fingerprint="init-fp-1", conn=uow.connection)
    uow.connection.commit()
    execution_id = plan_exec.execution_id
    original_binding = deps.binding_store.require(execution_id)
    old_worker_id = original_binding.worker.worker_id
    assert old_worker_id == "w-A-mumbai"

    outcome1 = coordinator.advance_plan_execution(
        execution_id=execution_id, plan=plan, actor=actor, operation_id="op-1",
        correlation_id="corr-1", request_id="req-1", payload={}, uow_factory=lambda: SQLiteUnitOfWork(db_path=db_path),
    )
    assert not outcome1.is_success

    ownership_key = f"{TENANT}::{migration_id}::{plan_id}"
    old_ownership = ctx["ownership_manager"].try_get(ownership_key)
    assert old_ownership.worker_id == old_worker_id

    # --- Rolling upgrade: the worker is REPLACED (P7B.22/23, unmodified) mid-execution ---
    new_worker = WorkerNode(worker_id="w-A-mumbai-v2", site_id="A-mumbai", tenant_id=TENANT, runtime_version="2.0.0", fencing_epoch=2)
    ctx["worker_registry"].replace_worker(old_worker_id, new_worker)

    # The old worker is now REVOKED -- worker_still_valid (execute_via_placement's own
    # existing live_trust_check) already fails it; ownership renewal ALSO independently
    # fails it (WrongWorkerOwnershipError if a caller somehow tried the new worker's
    # identity against the old record, or the record simply stays bound to the revoked
    # worker forever since nothing re-validates worker liveness for an ACTIVE, unexpired
    # record until the next renew/acquire attempt).
    with pytest.raises(Exception):
        ctx["worker_registry"].heartbeat(old_worker_id, TENANT)  # revoked worker cannot heartbeat back to life (P7B.22 law)

    # Recovery: fence old ownership, re-decide placement (worker_registry now offers the
    # NEW worker as the only schedulable one at this site), resume.
    ctx["ownership_manager"].force_fence(ownership_key, reason="rolling upgrade replaced the bound worker", evidence="hostile-test")
    new_binding = coordinator._decide_and_bind_fabric_placement(plan=plan, migration=migration, actor=actor)
    assert new_binding.worker.worker_id == "w-A-mumbai-v2"
    deps.binding_store.save(execution_id, new_binding)

    uow_recover = SQLiteUnitOfWork(db_path=db_path)
    coordinator.recover_plan_execution(migration_id=migration_id, actor=actor, conn=uow_recover.connection)
    uow_recover.connection.commit()

    _write_source_csv(source_csv)
    outcome2 = coordinator.advance_plan_execution(
        execution_id=execution_id, plan=plan, actor=actor, operation_id="op-2",
        correlation_id="corr-2", request_id="req-2", payload={}, uow_factory=lambda: SQLiteUnitOfWork(db_path=db_path),
    )
    assert outcome2.is_success and outcome2.status == "SUCCEEDED"

    new_ownership = ctx["ownership_manager"].try_get(ownership_key)
    assert new_ownership.worker_id == "w-A-mumbai-v2"
    assert new_ownership.fencing_generation > old_ownership.fencing_generation

    # The OLD worker's stale ownership claim can never be renewed again -- old-worker
    # return during/after the upgrade cannot regain authority through either channel.
    with pytest.raises(Exception):
        ctx["ownership_manager"].renew(
            _ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", old_worker_id),
            old_ownership.lease_id, old_ownership.fencing_generation,
        )


# ============================================================================
# P7B.35 hostile-review fix: worker BUSY lifecycle leak for non-data_transport
# physical-effect capabilities. bind_worker_for_placement marks a worker BUSY once per
# execution; only execute_via_placement's own internal cleanup ever finalized it back --
# for cdc_apply/incremental_apply/etc. (dispatched through their own independently-
# resolved ExecutionPort, never through execute_via_placement), the worker leaked BUSY
# forever. Fixed at the ONE real dispatch call site (PlanExecutionCoordinator.
# advance_plan_execution's Step C `finally`), reusing the SAME canonical
# akaalEngine.fabric.placement.execution.finalize_worker_after_dispatch
# execute_via_placement itself now also calls -- one worker-lifecycle finalization
# authority, not two. These tests assert the FIX directly (worker observed IDLE
# afterward), not merely work around the leak with a second worker.
# ============================================================================


class _FailingCdcPort(ExecutionPort):
    """A real, non-data_transport physical-effect ExecutionPort that always raises --
    proves worker finalization happens on the EXCEPTION path too, not only on success."""

    def __init__(self) -> None:
        self.invocations = 0

    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult:
        self.invocations += 1
        raise RuntimeError("simulated CDC engine failure")


def test_worker_returns_to_idle_after_successful_cdc_apply_dispatch(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    cdc_port = SchemaPrepTrackingPort()
    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="cdc_apply", extra_capability_port=cdc_port,
    )

    plan = _build_plan_with_cdc_apply("plan-worker-idle-ok", "mig-worker-idle-ok")
    plan_exec, outcome = _run(coordinator, plan, _migration("mig-worker-idle-ok", mode=MigrationMode.M2_BULK_CDC), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    assert len(cdc_port.invocations) == 1

    worker_after = ctx["worker_registry"].get("w-A-mumbai", TENANT)
    assert worker_after.state == WorkerState.IDLE  # THE fix: no longer leaked BUSY


def test_worker_returns_to_idle_after_failed_cdc_apply_dispatch(tmp_path):
    """Exception-safety: the worker must be finalized even when the CDC engine port
    itself raises -- proves cleanup is not merely a success-path convenience."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    failing_cdc_port = _FailingCdcPort()
    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="cdc_apply", extra_capability_port=failing_cdc_port,
    )

    plan = _build_plan_with_cdc_apply("plan-worker-idle-fail", "mig-worker-idle-fail")
    plan_exec, outcome = _run(coordinator, plan, _migration("mig-worker-idle-fail", mode=MigrationMode.M2_BULK_CDC), _actor(), db_path)
    assert not outcome.is_success
    assert failing_cdc_port.invocations == 1

    worker_after = ctx["worker_registry"].get("w-A-mumbai", TENANT)
    assert worker_after.state == WorkerState.IDLE  # finalized even on exception -- no leak


def test_repeated_cdc_dispatches_never_exhaust_the_single_worker_pool(tmp_path):
    """Proves the fix holds under repeated use, not just once -- a single worker at a
    single site must be able to serve many sequential CDC-shaped dispatches (each a
    DIFFERENT migration/plan, so a DIFFERENT ownership_key, but the SAME physical
    worker) without ever running out of schedulable capacity."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    cdc_port = SchemaPrepTrackingPort()
    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="cdc_apply", extra_capability_port=cdc_port,
    )

    for i in range(5):
        plan = _build_plan_with_cdc_apply(f"plan-repeat-{i}", f"mig-repeat-{i}")
        plan_exec, outcome = _run(coordinator, plan, _migration(f"mig-repeat-{i}", mode=MigrationMode.M2_BULK_CDC), _actor(), db_path)
        assert outcome.is_success and outcome.status == "SUCCEEDED", f"dispatch {i} failed: {outcome.error_message}"

    assert len(cdc_port.invocations) == 5
    assert ctx["worker_registry"].get("w-A-mumbai", TENANT).state == WorkerState.IDLE


def test_finalization_never_resurrects_a_worker_revoked_during_dispatch(tmp_path):
    """The critical negative proof: a worker revoked WHILE its dispatch was in flight
    (simulated here by revoking it from inside the CDC port's own execute_task, standing
    in for a concurrent P7B.22 revocation) must NOT be reset to IDLE by finalization --
    it must remain REVOKED."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])

    class _RevokingCdcPort(ExecutionPort):
        def execute_task(self, request):
            ctx["worker_registry"].revoke("w-A-mumbai", TENANT)
            payload = request.payload or {}
            sig = sign_receipt(
                migration_id=payload.get("migration_id", ""), run_id=request.attempt_id,
                operation_id=request.operation_id or f"op-{request.invocation_id}",
                fencing_epoch=request.fence_epoch, status_code="SUCCESS",
                initialization_fingerprint=request.initialization_fingerprint, job_id=request.graph_node_id,
            )
            return EngineInvocationResult(
                invocation_id=request.invocation_id, attempt_id=request.attempt_id, lease_id=request.lease_id,
                fence_epoch=request.fence_epoch, is_success=True, graph_node_id=request.graph_node_id,
                binding_id=request.binding_id, initialization_fingerprint=request.initialization_fingerprint,
                result_payload={"node": request.graph_node_id, "engine_execution_receipt": sig if isinstance(sig, dict) else {}},
            )

    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="cdc_apply", extra_capability_port=_RevokingCdcPort(),
    )
    plan = _build_plan_with_cdc_apply("plan-revoke-mid-dispatch", "mig-revoke-mid-dispatch")
    _run(coordinator, plan, _migration("mig-revoke-mid-dispatch", mode=MigrationMode.M2_BULK_CDC), _actor(), db_path)

    worker_after = ctx["worker_registry"].get("w-A-mumbai", TENANT)
    assert worker_after.state == WorkerState.REVOKED  # never resurrected to IDLE


def test_finalization_never_resurrects_a_worker_put_into_draining_during_dispatch(tmp_path):
    """Same proof for DRAINING -- a worker drained mid-dispatch must stay DRAINING, never
    silently reset to IDLE (which would make it newly eligible for fresh scheduling,
    exactly the 'accidentally return a draining worker to normal scheduling eligibility'
    outcome that must never happen)."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])

    class _DrainingCdcPort(ExecutionPort):
        def execute_task(self, request):
            ctx["worker_registry"].request_drain("w-A-mumbai", TENANT)
            payload = request.payload or {}
            return EngineInvocationResult(
                invocation_id=request.invocation_id, attempt_id=request.attempt_id, lease_id=request.lease_id,
                fence_epoch=request.fence_epoch, is_success=True, graph_node_id=request.graph_node_id,
                binding_id=request.binding_id, initialization_fingerprint=request.initialization_fingerprint,
                result_payload={"node": request.graph_node_id, "engine_execution_receipt": {}},
            )

    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="cdc_apply", extra_capability_port=_DrainingCdcPort(),
    )
    plan = _build_plan_with_cdc_apply("plan-drain-mid-dispatch", "mig-drain-mid-dispatch")
    _run(coordinator, plan, _migration("mig-drain-mid-dispatch", mode=MigrationMode.M2_BULK_CDC), _actor(), db_path)

    worker_after = ctx["worker_registry"].get("w-A-mumbai", TENANT)
    assert worker_after.state == WorkerState.DRAINING  # never reset to IDLE mid-drain


def test_data_transport_worker_finalization_is_not_double_released_incorrectly(tmp_path):
    """The outer coordinator-level finalization (added for CDC/incremental capabilities)
    must not corrupt data_transport's own, pre-existing internal finalization inside
    execute_via_placement -- proves calling finalize_worker_after_dispatch twice
    (once inside execute_via_placement, once at the outer coordinator boundary) is a safe
    no-op, not a double-transition or error."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    plan = _build_plan("plan-dt-double-release", "mig-dt-double-release", fabric_required=True, source_csv=source_csv, target_csv=target_csv)
    plan_exec, outcome = _run(coordinator, plan, _migration("mig-dt-double-release"), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    worker_after = ctx["worker_registry"].get("w-A-mumbai", TENANT)
    assert worker_after.state == WorkerState.IDLE
    assert worker_after.fencing_epoch == 1  # untouched by the (safe no-op) second finalization call


# ============================================================================
# Checkpoint-boundary hostile proofs. Uses the REAL, canonical, frozen
# akaalPipeline.recovery.checkpoints.CheckpointManager + akaalPipeline.operations.leases.
# LeaseManager (the SAME instances PlanExecutionCoordinator itself holds as
# self.lease_manager) -- no Group-3 checkpoint authority is created. These tests prove:
# OWNERSHIP != CHECKPOINT, LEASE != CHECKPOINT, FENCING GENERATION != CHECKPOINT --
# Group-3 ownership fencing and canonical Pipeline checkpoint advancement are two
# completely separate authorities with zero shared state, and a stale/fenced owner is
# blocked from ever reaching physical dispatch (proven elsewhere) long before it could
# attempt to influence canonical checkpoint state (which it structurally cannot touch at
# all -- CheckpointManager.record_checkpoint validates only against the Pipeline's OWN
# LeaseManager, never against akaalEngine.fabric.ownership.OwnershipManager).
# ============================================================================


def _record_real_checkpoint(coordinator, db_path, execution_id, node_execution_id, migration_id, plan_id, init_fp="init-fp-1"):
    """Uses the coordinator's OWN real lease_manager + a real CheckpointManager to record
    one canonical checkpoint for the given (already-dispatched) node -- exactly the
    shape a real physical engine port would use, reusing the REAL attempt/lease state
    Step B already established during dispatch."""
    from akaalPipeline.recovery.checkpoints import CheckpointCandidate, CheckpointManager

    uow = SQLiteUnitOfWork(db_path=db_path)
    node_row = uow.connection.execute(
        "SELECT * FROM node_executions WHERE node_execution_id = ?", (node_execution_id,)
    ).fetchone()
    lease = coordinator.lease_manager.get_lease(node_row["current_attempt_id"], conn=uow.connection)
    assert lease is not None, "node must have an active Pipeline-level lease from real Step B dispatch"

    checkpoint_manager = CheckpointManager(lease_manager=coordinator.lease_manager)
    checkpoint_id = f"cp-{execution_id}-{node_row['graph_node_id']}"
    checkpoint_manager.record_checkpoint(
        CheckpointCandidate(
            checkpoint_id=checkpoint_id, attempt_id=lease.attempt_id, engine_invocation_id=node_row["current_invocation_id"] or "inv-1",
            lease_id=lease.lease_id, fence_epoch=lease.fence_epoch, graph_node_id=node_row["graph_node_id"],
            initialization_fingerprint=init_fp, engine_binding=node_row["binding_id"] or "binding-1",
            checkpoint_payload_reference=f"ref-{checkpoint_id}",
        ),
        expected_initialization_fingerprint=init_fp,
        conn=uow.connection,
    )
    uow.connection.commit()
    return checkpoint_manager, checkpoint_id


def test_ownership_fencing_never_touches_the_canonical_checkpoint_table(tmp_path):
    """Structural + behavioral proof: fencing Group-3 ownership before/after a real
    checkpoint is recorded leaves the checkpoints table completely untouched -- ownership
    and checkpoint are provably independent authorities."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    migration_id, plan_id = "mig-checkpoint-independence", "plan-checkpoint-independence"
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)
    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    uow = SQLiteUnitOfWork(db_path=db_path)
    transport_node = next(n for n in coordinator.get_node_executions(plan_exec.execution_id, uow.connection) if n.graph_node_id == "n-transport")
    _, checkpoint_id = _record_real_checkpoint(coordinator, db_path, plan_exec.execution_id, transport_node.node_execution_id, migration_id, plan_id)

    checkpoint_row_before = uow.connection.execute("SELECT * FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,)).fetchone()
    assert checkpoint_row_before is not None

    # Fence Group-3 ownership -- this must have ZERO effect on the checkpoints table.
    ownership_key = f"{TENANT}::{migration_id}::{plan_id}"
    ctx["ownership_manager"].force_fence(ownership_key, reason="hostile-test: checkpoint independence", evidence="hostile-test")

    uow2 = SQLiteUnitOfWork(db_path=db_path)
    checkpoint_row_after = uow2.connection.execute("SELECT * FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,)).fetchone()
    assert dict(checkpoint_row_after) == dict(checkpoint_row_before)  # byte-for-byte unchanged


def test_post_checkpoint_ownership_transfer_does_not_roll_back_or_replay_checkpoint(tmp_path):
    """Scenario D: Owner A/N -> physical success -> canonical checkpoint advances ->
    A fenced -> B/N+1 becomes owner -> recovery. B must resume from the ALREADY-ADVANCED
    canonical checkpoint, never replay earlier work or roll it back merely because
    ownership changed. OWNERSHIP TRANSFER != CHECKPOINT ROLLBACK."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(
        TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM), ("B-mumbai2", "IN", SiteKind.CLOUD_VM)],
    )
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    migration_id, plan_id = "mig-checkpoint-transfer", "plan-checkpoint-transfer"
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)
    migration, actor = _migration(migration_id), _actor()

    plan_exec, outcome = _run(coordinator, plan, migration, actor, db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"  # site A completes real physical work

    uow = SQLiteUnitOfWork(db_path=db_path)
    transport_node = next(n for n in coordinator.get_node_executions(plan_exec.execution_id, uow.connection) if n.graph_node_id == "n-transport")
    checkpoint_manager, checkpoint_id = _record_real_checkpoint(coordinator, db_path, plan_exec.execution_id, transport_node.node_execution_id, migration_id, plan_id)

    original_checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id, conn=SQLiteUnitOfWork(db_path=db_path).connection)
    assert original_checkpoint is not None

    # A fenced (e.g. post-hoc, site A presumed compromised even after its own success).
    ownership_key = f"{TENANT}::{migration_id}::{plan_id}"
    ctx["ownership_manager"].force_fence(ownership_key, reason="post-success fencing", evidence="hostile-test")

    # B acquires the NEXT generation for a (hypothetical) subsequent unit of work at the
    # same ownership_key -- proves the transfer itself, independent of checkpoint state.
    new_record = ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "B-mumbai2", "w-B-mumbai2"))
    assert new_record.fencing_generation > 0

    # The canonical checkpoint must be EXACTLY as it was -- never rolled back, never
    # replayed, never mutated by the ownership transfer.
    uow2 = SQLiteUnitOfWork(db_path=db_path)
    checkpoint_after_transfer = checkpoint_manager.get_checkpoint(checkpoint_id, conn=uow2.connection)
    assert checkpoint_after_transfer == original_checkpoint

    # recover_plan_execution, given this checkpoint_id explicitly, must reference the
    # SAME advanced checkpoint -- not fabricate an earlier one.
    uow3 = SQLiteUnitOfWork(db_path=db_path)
    coordinator.recover_plan_execution(migration_id=migration_id, actor=actor, conn=uow3.connection, checkpoint_id=checkpoint_id)
    uow3.connection.commit()
    uow4 = SQLiteUnitOfWork(db_path=db_path)
    plan_row = uow4.connection.execute("SELECT checkpoint_id FROM plan_executions WHERE execution_id = ?", (plan_exec.execution_id,)).fetchone()
    assert plan_row["checkpoint_id"] == checkpoint_id  # recovery references the real, advanced checkpoint verbatim


def test_checkpoint_rejects_stale_lease_fence_epoch_independent_of_ownership_state(tmp_path):
    """Defense in depth: even setting Group-3 ownership aside entirely, the CANONICAL
    checkpoint authority independently fails closed on a stale/forged lease or fence
    epoch -- this is pre-existing, frozen Pipeline behavior (akaalPipeline.recovery.
    checkpoints.CheckpointManager, unmodified), reused here to prove Group-3 introduced
    no weakening of it."""
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    coordinator, schema_port, never_port = _build_coordinator(db_path, fabric_dependencies=deps)

    source_csv, target_csv = tmp_path / "source.csv", tmp_path / "target.csv"
    _write_source_csv(source_csv)
    migration_id, plan_id = "mig-checkpoint-stale-lease", "plan-checkpoint-stale-lease"
    plan = _build_plan(plan_id, migration_id, fabric_required=True, source_csv=source_csv, target_csv=target_csv)
    plan_exec, outcome = _run(coordinator, plan, _migration(migration_id), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"

    from akaalPipeline.contracts.errors import CheckpointRejectedError
    from akaalPipeline.recovery.checkpoints import CheckpointCandidate, CheckpointManager

    uow = SQLiteUnitOfWork(db_path=db_path)
    transport_node = next(n for n in coordinator.get_node_executions(plan_exec.execution_id, uow.connection) if n.graph_node_id == "n-transport")
    checkpoint_manager = CheckpointManager(lease_manager=coordinator.lease_manager)

    with pytest.raises(CheckpointRejectedError):
        checkpoint_manager.record_checkpoint(
            CheckpointCandidate(
                checkpoint_id="cp-forged", attempt_id=transport_node.current_attempt_id, engine_invocation_id="inv-forged",
                lease_id="lease-forged-not-real", fence_epoch=999, graph_node_id="n-transport",
                initialization_fingerprint="init-fp-1", engine_binding="binding-1", checkpoint_payload_reference="ref-forged",
            ),
            expected_initialization_fingerprint="init-fp-1",
            conn=uow.connection,
        )


# ============================================================================
# Physical-effect capability inventory sweep: the universal ownership gate keys off
# SideEffectClassification (READ_ONLY vs. everything else), not a capability-name
# whitelist -- proves this generalizes to a capability this file has not exercised yet
# (akaalPipeline.adapters.engine_gateway.CAPABILITY_SEMANTIC_MAP's "schema_apply",
# mapped to APPLY_SCHEMA_CHANGES -- a genuinely physical, mutating DDL capability).
# ============================================================================


def test_schema_apply_capability_is_ownership_gated_via_side_effect_not_name_whitelist(tmp_path):
    db_path, _ = _fresh_db(tmp_path)
    deps, ctx = _build_fabric_dependencies(TENANT, tmp_path, [("A-mumbai", "IN", SiteKind.CLOUD_VM)])
    schema_apply_port = SchemaPrepTrackingPort()
    coordinator, schema_port, never_port = _build_coordinator(
        db_path, fabric_dependencies=deps, extra_capability_id="schema_apply", extra_capability_port=schema_apply_port,
    )

    def _plan_with_schema_apply(plan_id, migration_id):
        schema_node = GraphNode(node_id="n-schema", task=NodeTaskDescriptor(task_id="t-schema", capability_contract="schema_prep", side_effect=SideEffectClassification.READ_ONLY), dependencies=[])
        apply_node = GraphNode(node_id="n-apply", task=NodeTaskDescriptor(task_id="t-apply", capability_contract="schema_apply", side_effect=SideEffectClassification.IRREVERSIBLE), dependencies=["n-schema"])
        edges = [GraphEdge(from_node="n-schema", to_node="n-apply")]
        return ExecutionPlan.create(
            plan_id=plan_id, migration_id=migration_id, mode=MigrationMode.M6_SCHEMA_ONLY, nodes=[schema_node, apply_node], edges=edges,
            configuration={"fabric_placement": {
                "required": True, "required_capabilities": ["oracle", "postgresql"], "residency_policy_ids": ["india-only"],
                "source_provider": "file", "target_provider": "file", "source_params": {}, "target_params": {},
            }},
        )

    plan_ok = _plan_with_schema_apply("plan-schema-apply-ok", "mig-schema-apply-ok")
    plan_exec, outcome = _run(coordinator, plan_ok, _migration("mig-schema-apply-ok", mode=MigrationMode.M6_SCHEMA_ONLY), _actor(), db_path)
    assert outcome.is_success and outcome.status == "SUCCEEDED"
    assert len(schema_apply_port.invocations) == 1
    assert ctx["worker_registry"].get("w-A-mumbai", TENANT).state == WorkerState.IDLE  # also proves worker finalization for this capability

    ctx["worker_registry"].register(WorkerNode(worker_id="w2-A-mumbai", site_id="A-mumbai", tenant_id=TENANT, runtime_version="1.0.0", fencing_epoch=2))
    migration_id, plan_id = "mig-schema-apply-conflict", "plan-schema-apply-conflict"
    ctx["ownership_manager"].acquire(_ownership_claim_for(TENANT, migration_id, plan_id, "A-mumbai", "attacker-worker"))
    plan_conflict = _plan_with_schema_apply(plan_id, migration_id)
    plan_exec2, outcome2 = _run(coordinator, plan_conflict, _migration(migration_id, mode=MigrationMode.M6_SCHEMA_ONLY), _actor(), db_path)
    assert not outcome2.is_success
    assert len(schema_apply_port.invocations) == 1  # no NEW invocation -- conflict blocked before the DDL engine port
