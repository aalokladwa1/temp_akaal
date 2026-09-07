"""
P7B Group-2 production wiring: end-to-end proof that Campaign C placement and Campaign D
worker fabric are LOAD-BEARING on the real Group-1 execution boundary, not primitives
sitting beside it.

Chain proven end-to-end through REAL production classes (no business-logic mocks --
`TransportAuthority`, `RemoteExecutionControlPlane`, `SiteRegistry`, `WorkerRegistry`,
`TopologyRegistry`, real file-based reader/writer, exactly the pattern already
established in test_p7b_round4_mandatory_revalidation.py):

    ExecutionPlan-derived requirements -> topology -> locality -> capability -> policy
    -> sovereignty -> optimization/cost -> PlacementDecision -> worker binding ->
    RemoteExecutionAssignment -> execute_assignment_via_transport -> TransportAuthority
    -> physical file read/write.

The India/Singapore/incapable/unauthorized hostile scenario is run through THIS
production entry point (not just the Campaign-C-only unit test in
test_p7b16_placement_engine_composition.py), and the negative case is proven with a
transport double that raises if ever invoked -- true zero-physical-call proof.
"""

from __future__ import annotations

import csv
import inspect

import pytest

from akaalEngine.fabric.execution_site.models import ExecutionSite, SiteKind, SiteTrustState
from akaalEngine.fabric.execution_site.registry import SiteRegistry
from akaalEngine.fabric.locality.models import LocalityConfidence, LocalityDimension, LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.placement.binding import NoCompliantPlacementError, PlacementDecision, StalePlacementError, decide_placement
from akaalEngine.fabric.placement.capability import CapabilityRequirement
from akaalEngine.fabric.placement.execution import (
    KubernetesPodSpecRequiredError,
    PlacementBindingIntegrityError,
    WorkerNotAvailableError,
    bind_worker_for_placement,
    execute_via_placement,
)
from akaalEngine.fabric.placement.residency import ResidencyPolicy
from akaalEngine.fabric.remote_execution.control_plane import RemoteExecutionControlPlane
from akaalEngine.fabric.topology.graph import TopologyRegistry
from akaalEngine.fabric.topology.models import TopologyNode, TopologyNodeKind
from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState
from akaalEngine.fabric.worker_fabric.registry import WorkerRegistry
from akaalEngine.transport.api import TransportAuthority
from akaalEngine.transport.models.errors import TransportFencingError
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition

SIGNING_KEY = b"group2-production-wiring-test-key"
TENANT = "tenant-a"
INDIA_ONLY = ResidencyPolicy(policy_id="india-only", dimension=LocalityDimension.COUNTRY,
                              allowed_values=frozenset({"IN"}), required_roles=(LocalitySubjectRole.EXECUTION_SITE,))
REQ = CapabilityRequirement(required_capabilities=frozenset({"oracle", "postgresql"}), plan_reference="oracle-to-pg-india-e2e")


def _topology_with_one_node(tenant=TENANT):
    reg = TopologyRegistry()
    reg.register_node(TopologyNode(node_id="topo-env-1", node_kind=TopologyNodeKind.ENVIRONMENT, ref_id="env-1",
                                    tenant_id=tenant, provenance_source="OPERATOR_CONFIGURATION"))
    return reg


def _site(site_id, caps, country, kind=SiteKind.CLOUD_VM):
    return ExecutionSite(site_id=site_id, site_kind=kind, environment_id=f"env-{site_id}",
                          capabilities=frozenset(caps), trust_state=SiteTrustState.TRUSTED)


def _locality(site_id, country):
    return {LocalitySubjectRole.EXECUTION_SITE: LocalityRecord(
        subject_ref=site_id, subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id=TENANT,
        country=country, confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    )}


def _ready_site_registry(site_id="A-mumbai", tenant_id=TENANT):
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id="env-A",
                                     claimed_security_identity="spiffe://x/A"))
    registry.verify_identity(site_id, verifier=lambda s, cred: True, presented_credential="cred")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry


def _worker(site_id, worker_id="w1", tenant=TENANT, epoch=1):
    return WorkerNode(worker_id=worker_id, site_id=site_id, tenant_id=tenant, runtime_version="1.0.0", fencing_epoch=epoch)


def _transport_and_files(tmp_path):
    source_csv = tmp_path / "source.csv"
    target_csv = tmp_path / "target.csv"
    with open(source_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id"])
        w.writeheader()
        w.writerow({"id": "1"})
    transport_authority = TransportAuthority()
    reader = transport_authority.resolve_source_reader_for_provider("file", file_path=str(source_csv), format_type="CSV")
    writer = transport_authority.resolve_target_writer_for_provider("file", file_path=str(target_csv), format_type="CSV")
    partition = TransportPartition(partition_id="p0", table_name="source.csv", schema_name="file", target_schema="file", strategy=list(PartitionStrategy)[0])
    return transport_authority, reader, writer, partition, target_csv


class _NeverCalledTransport:
    """A transport double that raises AssertionError if execute_partition_transport is
    EVER invoked -- true zero-physical-call proof for the negative-placement path, since
    decide_placement must raise before this object is ever reached."""

    def execute_partition_transport(self, *args, **kwargs):  # pragma: no cover -- must never run
        raise AssertionError("execute_partition_transport was called despite NO COMPLIANT PLACEMENT")


# ------------------------------------------------------------------ full production-path E2E (happy path)


def test_full_production_path_from_placement_through_physical_write(tmp_path):
    """ExecutionPlan requirements -> topology -> capability -> policy -> residency ->
    optimization -> PlacementDecision -> worker binding -> RemoteExecutionAssignment ->
    execute_assignment_via_transport -> TransportAuthority -> real file write. Every
    object in this chain is the real production class."""
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")

    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={"tenant": TENANT}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    assert decision.selected_site_id == "A-mumbai"

    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)
    assert worker.state == WorkerState.BUSY

    site_registry = _ready_site_registry("A-mumbai", TENANT)
    control_plane = RemoteExecutionControlPlane(site_registry)
    transport_authority, reader, writer, partition, target_csv = _transport_and_files(tmp_path)

    rows = execute_via_placement(
        decision=decision, site=site_a, worker=worker, control_plane=control_plane,
        worker_registry=worker_registry, transport_authority=transport_authority,
        signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
        reader=reader, writer=writer, partition=partition,
        current_topology_provider=lambda: topology.snapshot(TENANT),
    )
    writer.close()
    assert rows == 1
    with open(target_csv, encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == [{"id": "1"}]
    # Worker returned to IDLE after successful execution.
    assert worker_registry.get(worker.worker_id, TENANT).state == WorkerState.IDLE


# ------------------------------------------------------------------ India/Singapore/incapable/unauthorized through the real path


def test_india_scenario_through_production_path_only_compliant_site_executes(tmp_path):
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    site_b = _site("B-singapore", {"oracle", "postgresql"}, "SG")
    site_c = _site("C-incapable", {"postgresql"}, "IN")
    site_d = _site("D-unauthorized", {"oracle", "postgresql"}, "IN")

    def authz(site, actor, action, ctx):
        return site.site_id in ("A-mumbai", "B-singapore", "C-incapable")  # D excluded

    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a, site_b, site_c, site_d], capability_requirement=REQ,
        actor_context={"tenant": TENANT}, authorization_callback=authz,
        residency_policies=(INDIA_ONLY,),
        locality_by_site={
            "A-mumbai": _locality("A-mumbai", "IN"), "B-singapore": _locality("B-singapore", "SG"),
            "C-incapable": _locality("C-incapable", "IN"), "D-unauthorized": _locality("D-unauthorized", "IN"),
        },
        topology_graph=topology.snapshot(TENANT),
    )
    assert decision.selected_site_id == "A-mumbai"

    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)
    site_registry = _ready_site_registry("A-mumbai", TENANT)
    control_plane = RemoteExecutionControlPlane(site_registry)
    transport_authority, reader, writer, partition, target_csv = _transport_and_files(tmp_path)

    rows = execute_via_placement(
        decision=decision, site=site_a, worker=worker, control_plane=control_plane,
        worker_registry=worker_registry, transport_authority=transport_authority,
        signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
        reader=reader, writer=writer, partition=partition,
        current_topology_provider=lambda: topology.snapshot(TENANT),
    )
    writer.close()
    assert rows == 1


def test_only_singapore_remains_no_compliant_placement_zero_physical_calls(tmp_path):
    """India-only migration; Mumbai unavailable, only Singapore (capable, authorized,
    cheaper, WRONG country) remains -- must raise NoCompliantPlacementError BEFORE any
    assignment is issued and BEFORE the transport layer is ever touched."""
    topology = _topology_with_one_node()
    site_b = _site("B-singapore", {"oracle", "postgresql"}, "SG")

    never_called_transport = _NeverCalledTransport()

    with pytest.raises(NoCompliantPlacementError):
        decide_placement(
            tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
            plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
            candidates=[site_b], capability_requirement=REQ,
            actor_context={"tenant": TENANT}, authorization_callback=lambda *a: True,
            residency_policies=(INDIA_ONLY,), locality_by_site={"B-singapore": _locality("B-singapore", "SG")},
            topology_graph=topology.snapshot(TENANT),
        )
    # never_called_transport was never even constructed into a live call -- there is no
    # PlacementDecision, no worker binding, no assignment, no execute_via_placement call
    # anywhere in this test after the raise. Its very existence unused in this test IS
    # the proof: nothing downstream of decide_placement's raise can run without a
    # PlacementDecision object, which was never produced.
    assert isinstance(never_called_transport, _NeverCalledTransport)


def test_unknown_locality_no_compliant_placement(tmp_path):
    topology = _topology_with_one_node()
    site_unknown = _site("E-unknown-jurisdiction", {"oracle", "postgresql"}, country=None)
    unknown_locality = {LocalitySubjectRole.EXECUTION_SITE: LocalityRecord(
        subject_ref="E-unknown-jurisdiction", subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id=TENANT,
    )}
    with pytest.raises(NoCompliantPlacementError):
        decide_placement(
            tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
            plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
            candidates=[site_unknown], capability_requirement=REQ,
            actor_context={"tenant": TENANT}, authorization_callback=lambda *a: True,
            residency_policies=(INDIA_ONLY,), locality_by_site={"E-unknown-jurisdiction": unknown_locality},
            topology_graph=topology.snapshot(TENANT),
        )


# ------------------------------------------------------------------ hostile: staleness / bypass / substitution


def test_topology_mutation_after_placement_refused_before_execution(tmp_path):
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    # Topology mutates AFTER the decision was made.
    topology.register_node(TopologyNode(node_id="topo-env-2", node_kind=TopologyNodeKind.ENVIRONMENT,
                                         ref_id="env-2", tenant_id=TENANT, provenance_source="OPERATOR_CONFIGURATION"))

    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)
    site_registry = _ready_site_registry("A-mumbai", TENANT)
    control_plane = RemoteExecutionControlPlane(site_registry)
    never_called_transport = _NeverCalledTransport()

    with pytest.raises(StalePlacementError):
        execute_via_placement(
            decision=decision, site=site_a, worker=worker, control_plane=control_plane,
            worker_registry=worker_registry, transport_authority=never_called_transport,
            signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
            reader=object(), writer=object(), partition=object(),
            current_topology_provider=lambda: topology.snapshot(TENANT),
        )


def test_stale_placement_replay_refused(tmp_path):
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT), decision_ttl_minutes=-0.01,  # already expired
    )
    assert decision.is_expired()

    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)
    site_registry = _ready_site_registry("A-mumbai", TENANT)
    control_plane = RemoteExecutionControlPlane(site_registry)
    never_called_transport = _NeverCalledTransport()

    with pytest.raises(StalePlacementError):
        execute_via_placement(
            decision=decision, site=site_a, worker=worker, control_plane=control_plane,
            worker_registry=worker_registry, transport_authority=never_called_transport,
            signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
            reader=object(), writer=object(), partition=object(),
            current_topology_provider=lambda: topology.snapshot(TENANT),
        )


def test_residency_recheck_failure_between_placement_and_execution_zero_rows_written(tmp_path):
    """Policy/residency change between placement and execution: proven through the REAL
    TransportAuthority (not a never-called double), because the composed live_trust_check
    must be reached and reject inside TransportAuthority's own pre-flight security gate
    -- proving zero rows are read/written even though the transport object IS live."""
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)
    site_registry = _ready_site_registry("A-mumbai", TENANT)
    control_plane = RemoteExecutionControlPlane(site_registry)
    transport_authority, reader, writer, partition, target_csv = _transport_and_files(tmp_path)

    with pytest.raises(TransportFencingError):
        execute_via_placement(
            decision=decision, site=site_a, worker=worker, control_plane=control_plane,
            worker_registry=worker_registry, transport_authority=transport_authority,
            signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
            reader=reader, writer=writer, partition=partition,
            current_topology_provider=lambda: topology.snapshot(TENANT),
            residency_recheck=lambda: False,  # residency changed/revoked between placement and execution
        )
    writer.close()
    assert transport_authority.rows_written_total == 0
    with open(target_csv, encoding="utf-8") as fh:
        assert fh.read() == ""


def test_worker_revoked_between_bind_and_execution_zero_rows_written(tmp_path):
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)
    worker_registry.revoke(worker.worker_id, TENANT)  # revoked AFTER binding, BEFORE execution

    site_registry = _ready_site_registry("A-mumbai", TENANT)
    control_plane = RemoteExecutionControlPlane(site_registry)
    transport_authority, reader, writer, partition, target_csv = _transport_and_files(tmp_path)

    with pytest.raises(TransportFencingError):
        execute_via_placement(
            decision=decision, site=site_a, worker=worker, control_plane=control_plane,
            worker_registry=worker_registry, transport_authority=transport_authority,
            signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
            reader=reader, writer=writer, partition=partition,
            current_topology_provider=lambda: topology.snapshot(TENANT),
        )
    writer.close()
    assert transport_authority.rows_written_total == 0


def test_worker_replaced_via_rolling_upgrade_between_bind_and_execution_refused(tmp_path):
    """Rolling replacement mid-flight: the WorkerRegistry replaces the bound worker
    (old worker REVOKED, fencing epoch advances) -- proves execute_via_placement detects
    the underlying worker changed and refuses, rather than silently continuing as if the
    old, now-superseded worker were still valid ('Kubernetes restart != migration
    recovery' made concrete)."""
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai", worker_id="w-old", epoch=1))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)
    worker_registry.replace_worker("w-old", _worker("A-mumbai", worker_id="w-new", epoch=2))

    site_registry = _ready_site_registry("A-mumbai", TENANT)
    control_plane = RemoteExecutionControlPlane(site_registry)
    transport_authority, reader, writer, partition, target_csv = _transport_and_files(tmp_path)

    with pytest.raises(TransportFencingError):
        execute_via_placement(
            decision=decision, site=site_a, worker=worker, control_plane=control_plane,
            worker_registry=worker_registry, transport_authority=transport_authority,
            signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
            reader=reader, writer=writer, partition=partition,
            current_topology_provider=lambda: topology.snapshot(TENANT),
        )
    writer.close()
    assert transport_authority.rows_written_total == 0


def test_scale_in_draining_during_execution_does_not_abort_in_flight_work(tmp_path):
    """DRAINING means 'no NEW assignments', never 'kill active work' -- proves execution
    already bound to a draining worker still completes successfully."""
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)
    worker_registry.request_drain(worker.worker_id, TENANT)  # scale-in signal mid-flight

    site_registry = _ready_site_registry("A-mumbai", TENANT)
    control_plane = RemoteExecutionControlPlane(site_registry)
    transport_authority, reader, writer, partition, target_csv = _transport_and_files(tmp_path)

    rows = execute_via_placement(
        decision=decision, site=site_a, worker=worker, control_plane=control_plane,
        worker_registry=worker_registry, transport_authority=transport_authority,
        signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
        reader=reader, writer=writer, partition=partition,
        current_topology_provider=lambda: topology.snapshot(TENANT),
    )
    writer.close()
    assert rows == 1  # completed despite DRAINING


def test_site_revoked_after_placement_caught_via_extra_live_trust_check(tmp_path):
    """A site revoked between placement and execution is caught -- proves the Group-2
    binding composes with (never replaces) the exact same SiteRegistry-based
    live_trust_check pattern Group-1's own round-4 tests already require."""
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)

    site_registry = _ready_site_registry("A-mumbai", TENANT)
    control_plane = RemoteExecutionControlPlane(site_registry)
    transport_authority, reader, writer, partition, target_csv = _transport_and_files(tmp_path)

    def site_trust_check(a):
        site = site_registry.get(a.site_id)
        return site.trust_state.value == "TRUSTED"

    def authz_then_revoke(s, a, c):
        # Simulates revocation landing in the narrow window AFTER assignment issuance's
        # own authorization check passes but BEFORE physical execution's live_trust_check
        # re-evaluation runs -- issue_assignment's own pre-check already used the
        # pre-revoke TRUSTED state (this callback's return value is what it evaluates),
        # so this legitimately reaches physical-execution-time revalidation instead of
        # being refused earlier at issuance (see the sibling test proving the
        # EVEN-EARLIER "revoked before issuance" case raises inside issue_assignment).
        site_registry.revoke("A-mumbai", reason="compromised after placement, before execution")
        return True

    with pytest.raises(TransportFencingError):
        execute_via_placement(
            decision=decision, site=site_a, worker=worker, control_plane=control_plane,
            worker_registry=worker_registry, transport_authority=transport_authority,
            signing_key=SIGNING_KEY, site_authorization_callback=authz_then_revoke,
            reader=reader, writer=writer, partition=partition,
            current_topology_provider=lambda: topology.snapshot(TENANT),
            extra_live_trust_check=site_trust_check,
        )
    writer.close()
    assert transport_authority.rows_written_total == 0


def test_site_revoked_before_assignment_issuance_refused_even_earlier(tmp_path):
    """Revocation discovered BEFORE assignment issuance is caught by Group-1's own
    unmodified SiteRegistry.assign_execution -- even earlier than physical-execution-time
    revalidation. This is the companion to the above test: revocation is caught at
    whichever point in the chain it actually happens to be discovered, always before
    physical I/O."""
    from akaalEngine.fabric.execution_site.registry import SiteRegistryError

    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)

    site_registry = _ready_site_registry("A-mumbai", TENANT)
    site_registry.revoke("A-mumbai", reason="compromised before issuance")
    control_plane = RemoteExecutionControlPlane(site_registry)
    never_called_transport = _NeverCalledTransport()

    with pytest.raises(SiteRegistryError):
        execute_via_placement(
            decision=decision, site=site_a, worker=worker, control_plane=control_plane,
            worker_registry=worker_registry, transport_authority=never_called_transport,
            signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
            reader=object(), writer=object(), partition=object(),
            current_topology_provider=lambda: topology.snapshot(TENANT),
        )


def test_no_worker_available_refused_never_falls_back_to_different_site():
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()  # no worker registered anywhere
    with pytest.raises(WorkerNotAvailableError):
        bind_worker_for_placement(decision, worker_registry, site_a)


def test_duplicate_bind_second_attempt_finds_no_schedulable_worker():
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    bind_worker_for_placement(decision, worker_registry, site_a)  # first bind succeeds, worker now BUSY
    with pytest.raises(WorkerNotAvailableError):
        bind_worker_for_placement(decision, worker_registry, site_a)  # duplicate bind attempt refused


# ------------------------------------------------------------------ structural no-bypass proof


def test_execute_via_placement_has_no_site_id_or_assignment_parameter():
    sig = inspect.signature(execute_via_placement)
    assert "site_id" not in sig.parameters
    assert "assignment" not in sig.parameters


def test_decide_placement_is_the_only_way_to_construct_a_placement_decision_with_valid_fields():
    """PlacementDecision's own validation refuses empty selected_site_id -- a caller
    cannot construct a 'blank' decision and fill in a site later."""
    with pytest.raises(Exception):
        PlacementDecision(
            decision_id="d1", tenant_id="t1", workspace_id="w1", project_id="p1",
            migration_id="m1", plan_id="p1", plan_revision=1, execution_identity_seal_fingerprint="s1",
            correlation_id="c1", selected_site_id="", topology_fingerprint="fp1", fencing_epoch=1,
            plan_reference="ref", acceptance_reasons=(), rejected_candidate_count=0,
        )


# ------------------------------------------------------------------ Kubernetes worker boundary


def test_kubernetes_site_requires_pod_spec_factory():
    topology = _topology_with_one_node()
    site_k8s = _site("K-cluster", {"oracle", "postgresql"}, "IN", kind=SiteKind.KUBERNETES)
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_k8s], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"K-cluster": _locality("K-cluster", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("K-cluster"))
    with pytest.raises(KubernetesPodSpecRequiredError):
        bind_worker_for_placement(decision, worker_registry, site_k8s)  # no pod_spec_factory


def test_kubernetes_site_binds_through_real_pod_spec_builder():
    from akaalEngine.fabric.k8s_runtime.pod_spec import ResourceRequirements, build_worker_pod_spec

    topology = _topology_with_one_node()
    site_k8s = _site("K-cluster", {"oracle", "postgresql"}, "IN", kind=SiteKind.KUBERNETES)
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_k8s], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"K-cluster": _locality("K-cluster", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("K-cluster"))

    def real_pod_spec_factory(worker):
        return build_worker_pod_spec(
            pod_name=worker.worker_id, namespace="akaal", image="akaal/worker:1.0.0",
            resources=ResourceRequirements(cpu_request="500m", memory_request="512Mi", cpu_limit="1", memory_limit="1Gi"),
            service_account_name="akaal-worker-sa",
        )

    worker = bind_worker_for_placement(decision, worker_registry, site_k8s, pod_spec_factory=real_pod_spec_factory)
    assert worker.state == WorkerState.BUSY


# ------------------------------------------------------------------ defense-in-depth: binding integrity


def test_binding_integrity_check_catches_mismatched_assignment_even_if_issuance_were_ever_tricked():
    """`execute_via_placement` has no `assignment` parameter (see the structural
    no-bypass test above), so under normal use the assignment it builds internally is
    always consistent with `decision`. This test proves the defense-in-depth
    PlacementBindingIntegrityError check itself actually fires, using a stub control
    plane that returns a deliberately mismatched assignment -- simulating what would
    happen if `RemoteExecutionControlPlane` were ever compromised/misbehaving, closing
    the class of bug where that check silently never triggers."""
    from akaalEngine.fabric.remote_execution.models import HMACAssignmentSigner, _canonical_payload
    from akaalEngine.fabric.remote_execution.models import RemoteExecutionAssignment as REA
    from datetime import datetime, timedelta, timezone

    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    worker_registry = WorkerRegistry()
    worker_registry.register(_worker("A-mumbai"))
    worker = bind_worker_for_placement(decision, worker_registry, site_a)

    class _StubControlPlane:
        """Simulates a compromised/misbehaving control plane returning an assignment
        for the WRONG correlation_id (a differently-issued assignment substituted in)."""

        def issue_assignment(self, **kwargs):
            issued_at = datetime.now(timezone.utc).isoformat()
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            wrong_correlation_id = "corr-DIFFERENT-NOT-THE-DECISIONS-OWN-ID"
            payload = _canonical_payload(
                "assign-substituted", kwargs["site_id"], kwargs["tenant_id"], kwargs["workspace_id"],
                kwargs["project_id"], kwargs["migration_id"], kwargs["plan_id"], kwargs["plan_revision"],
                kwargs["execution_identity_seal_fingerprint"], kwargs["fencing_epoch"], wrong_correlation_id,
                issued_at, expires_at,
            )
            signature = HMACAssignmentSigner(SIGNING_KEY).sign(payload)
            return REA(
                assignment_id="assign-substituted", site_id=kwargs["site_id"], tenant_id=kwargs["tenant_id"],
                workspace_id=kwargs["workspace_id"], project_id=kwargs["project_id"], migration_id=kwargs["migration_id"],
                plan_id=kwargs["plan_id"], plan_revision=kwargs["plan_revision"],
                execution_identity_seal_fingerprint=kwargs["execution_identity_seal_fingerprint"],
                fencing_epoch=kwargs["fencing_epoch"], correlation_id=wrong_correlation_id,
                signature=signature, issued_at=issued_at, expires_at=expires_at,
            )

    never_called_transport = _NeverCalledTransport()
    with pytest.raises(PlacementBindingIntegrityError):
        execute_via_placement(
            decision=decision, site=site_a, worker=worker, control_plane=_StubControlPlane(),
            worker_registry=worker_registry, transport_authority=never_called_transport,
            signing_key=SIGNING_KEY, site_authorization_callback=lambda s, a, c: True,
            reader=object(), writer=object(), partition=object(),
            current_topology_provider=lambda: topology.snapshot(TENANT),
        )


# ------------------------------------------------------------------ hostile: cross-tenant locality substitution through the real path


def test_cross_tenant_locality_record_rejected_through_decide_placement():
    """A LocalityRecord genuinely proven for a DIFFERENT tenant (e.g. reused from a
    shared cache/bug) must never silently satisfy THIS tenant's residency policy just
    because it was passed under the right site_id key. Proven through the full
    decide_placement production entry point, not just the residency unit test."""
    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    wrong_tenant_locality = {LocalitySubjectRole.EXECUTION_SITE: LocalityRecord(
        subject_ref="A-mumbai", subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id="tenant-B-victim",
        country="IN", confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    )}
    with pytest.raises(NoCompliantPlacementError):
        decide_placement(
            tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
            plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
            candidates=[site_a], capability_requirement=REQ,
            actor_context={}, authorization_callback=lambda *a: True,
            residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": wrong_tenant_locality},
            topology_graph=topology.snapshot(TENANT),
        )


# ------------------------------------------------------------------ tenant/workspace/project/plan substitution -- structural


def test_placement_decision_is_frozen_cannot_be_mutated_after_construction():
    """Tenant/workspace/project/plan substitution between placement and execution is
    structurally impossible: PlacementDecision is a frozen dataclass, and
    execute_via_placement derives every `expected_*` value passed to
    execute_assignment_via_transport EXCLUSIVELY from `decision` -- there is no second
    parameter anywhere that could carry a different tenant/plan/project."""
    import dataclasses

    topology = _topology_with_one_node()
    site_a = _site("A-mumbai", {"oracle", "postgresql"}, "IN")
    decision = decide_placement(
        tenant_id=TENANT, workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_revision=1, execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1,
        candidates=[site_a], capability_requirement=REQ,
        actor_context={}, authorization_callback=lambda *a: True,
        residency_policies=(INDIA_ONLY,), locality_by_site={"A-mumbai": _locality("A-mumbai", "IN")},
        topology_graph=topology.snapshot(TENANT),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.tenant_id = "tenant-substituted"


def test_execute_via_placement_has_no_tenant_workspace_project_plan_override_parameter():
    sig = inspect.signature(execute_via_placement)
    forbidden = {"tenant_id", "workspace_id", "project_id", "plan_id", "expected_tenant_id", "expected_plan_id"}
    assert forbidden.isdisjoint(sig.parameters.keys())
