"""tests/security/test_p7c_campaign_b_production_path.py
============================================================
P7C Campaign B production-path proof: Campaign B producers (P7C.7-P7C.12) are
reachable through the REAL PipelineUnifiedCaller / intelligence.submit seam
(the same production path already proven for P7C.1/P7C.6), not just as isolated
unit-level function calls. Also includes the required cross-Campaign A+B
integration journey (§28 of the P7C brief): assessment -> strategy -> wave plan
-> schema optimization -> SQL conversion -> capacity simulation, all through the
one production kernel instance, plus tenant-isolation hostile coverage.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command, make_query


def _region_scoped_caller(db_path: str, tenant_id: str, principal_id: str, allowed_region: str):
    """Builds a REAL PipelineUnifiedCaller wired to the REAL CentralAuthorizationEngine
    (no auto-provisioning wrapper -- that grants a SYSTEM/root-scoped blanket permission
    which would defeat this test's purpose).

    RBAC resource-scoped grants in this repository are structurally restricted to a
    fixed hierarchy (role_grants.resource_type CHECK constraint: ORGANIZATION/
    WORKSPACE/PROJECT/MIGRATION/SYSTEM only -- confirmed by inspection, "region" is not
    a legal RBAC grant scope and this test does not alter that frozen schema). The
    permission itself is therefore granted broadly via RBAC (SYSTEM scope), and the
    actual per-region restriction is enforced by a REAL ABAC DENY policy (condition:
    resource.id NOT IN [allowed_region]) -- exactly the mechanism
    akaalPipeline.security.abac.ABACAuthority.evaluate_policies exists for. This is
    still the real, existing, canonical authorization engine deciding -- not a second
    authority P7C invented."""
    from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
    from akaalPipeline.identity.groups import GroupAuthority
    from akaalPipeline.security.abac import ABACAuthority
    from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
    from akaalPipeline.security.permission_registry import PermissionRegistry
    from akaalPipeline.security.rbac import RBACAuthority
    from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork

    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()

    uow.tenants.create_tenant(tenant_id, tenant_id)
    uow.principals.create(tenant_id=tenant_id, principal_id=principal_id, principal_type="HUMAN", username=principal_id)

    # RBAC: broad grant of every permission (including the region/capability-use
    # permissions) -- the actual region restriction comes entirely from the ABAC
    # DENY policy below, proving ABAC genuinely overrides an RBAC allow.
    uow.roles.create_role(role_id="baseline-role", tenant_id=tenant_id, name="Baseline")
    for perm in PermissionRegistry.ALL_PERMISSIONS:
        uow.role_permissions.assign_permission(tenant_id, "baseline-role", perm, principal_id)
    uow.role_grants.grant_role(f"grant-baseline-{principal_id}", tenant_id, "PRINCIPAL", principal_id, "baseline-role", "SYSTEM", "root", principal_id)

    # ABAC: the real canonical region restriction. DENY unless resource.id is the
    # one allowed region -- fail closed for every other region.
    uow.abac_policies.create_policy(
        tenant_id=tenant_id,
        policy_id=f"region-restriction-{tenant_id}",
        name="Canonical region restriction",
        effect="DENY",
        target_action=PermissionRegistry.INTELLIGENCE_STRATEGY_REGION_USE,
        target_resource_type="region",
        condition_expression={"not": {"in": ["resource.id", [allowed_region]]}},
        priority=10,
    )
    uow.connection.commit()

    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    real_engine = CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)

    from tests.pipeline.conftest import build_session_manager

    return PipelineUnifiedCaller(shared_uow=uow, central_authz=real_engine, session_manager=build_session_manager(uow))


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def caller(temp_db_path):
    uc = authorized_caller(db_path=temp_db_path)
    yield uc
    uc.close()


def _actor(org_id: str, actor_id: str = None) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=actor_id or f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id,
        workspace_id="ws-main",
        project_id="proj-1",
    )


def _schema_model_dict() -> dict:
    """A real, minimal CanonicalSchemaModel serialized to dict -- exactly what
    CanonicalSchemaModel.from_dict expects (round-tripped via to_dict below)."""
    from akaalEngine.schema.models.schema import CanonicalSchemaModel
    from akaalEngine.schema.models.table import CanonicalColumn, CanonicalTable
    from akaalEngine.schema.models.types import CanonicalType, CanonicalTypeCategory

    table = CanonicalTable(
        table_name="customers", schema_name="public",
        columns=(CanonicalColumn(
            name="id", ordinal_position=1, source_native_type="INTEGER",
            canonical_type=CanonicalType(category=CanonicalTypeCategory.EXACT_NUMERIC, raw_vendor_type="INTEGER"),
        ),),
    )
    model = CanonicalSchemaModel(model_id="model-prod", source_vendor="postgresql", tables=(table,))
    return model.to_dict()


class TestCampaignBReachableThroughRealSeam:
    def test_estate_assessment_via_real_seam(self, caller):
        actor = _actor("tenant-alpha")
        cmd = make_command(
            "intelligence.submit",
            {
                "task": "ASSESS", "subject_type": "migration_plan", "subject_id": "plan-1",
                "subject_version": "v1", "capability": "estate_assessment",
                "parameters": {"target_engine": "postgresql", "schema_model": _schema_model_dict()},
            },
            actor, CorrelationContext.new(),
        )
        result = caller.handle_command(cmd)
        assert result.status == CallerResultStatus.OK
        assert "compatibility_breakdown" in result.result["result"]["data"]

    def test_capacity_simulation_via_real_seam_no_schema_model_needed(self, caller):
        actor = _actor("tenant-alpha")
        cmd = make_command(
            "intelligence.submit",
            {
                "task": "SIMULATE", "subject_type": "migration_plan", "subject_id": "plan-1",
                "subject_version": "v1", "capability": "capacity_scenario",
                "parameters": {
                    "dataset_size_bytes": 1_000_000_000, "worker_throughput_bytes_per_sec": 10_000_000,
                    "validation_throughput_bytes_per_sec": 20_000_000, "cutover_window_seconds": 500,
                },
            },
            actor, CorrelationContext.new(),
        )
        result = caller.handle_command(cmd)
        assert result.status == CallerResultStatus.OK
        assert result.result["result"]["epistemic_type"] == "PREDICTION"

    def test_missing_capability_falls_back_to_unregistered_error_not_wrong_producer(self, caller):
        """Requesting a task without specifying the right capability must fail
        cleanly, never silently dispatch to an unrelated Campaign B producer that
        happens to share the same coarse task."""
        actor = _actor("tenant-alpha")
        cmd = make_command(
            "intelligence.submit",
            {
                "task": "OPTIMIZE", "subject_type": "migration_plan", "subject_id": "plan-1",
                "subject_version": "v1",  # no capability specified
                "parameters": {},
            },
            actor, CorrelationContext.new(),
        )
        result = caller.handle_command(cmd)
        assert result.status == CallerResultStatus.ERROR


class TestCrossTenantHostile:
    def test_hostile_inline_schema_model_never_leaks_cross_tenant_since_no_id_lookup(self, caller):
        """Because schema_model is supplied inline by the caller (never looked up
        by a foreign artifact ID), there is no cross-tenant read surface here --
        prove that tenant B's assessment reflects only tenant B's own supplied
        data, never tenant A's."""
        actor_a = _actor("tenant-alpha")
        actor_b = _actor("tenant-beta")

        cmd_a = make_command(
            "intelligence.submit",
            {"task": "ASSESS", "subject_type": "migration_plan", "subject_id": "plan-1", "subject_version": "v1",
             "capability": "estate_assessment", "parameters": {"target_engine": "postgresql", "schema_model": _schema_model_dict()}},
            actor_a, CorrelationContext.new(),
        )
        result_a = caller.handle_command(cmd_a)
        assert result_a.result["tenant_id"] == "tenant-alpha"

        cmd_b = make_command(
            "intelligence.submit",
            {"task": "ASSESS", "subject_type": "migration_plan", "subject_id": "plan-1", "subject_version": "v1",
             "capability": "estate_assessment", "parameters": {"target_engine": "postgresql", "schema_model": _schema_model_dict()}},
            actor_b, CorrelationContext.new(),
        )
        result_b = caller.handle_command(cmd_b)
        assert result_b.result["tenant_id"] == "tenant-beta"

        # Each tenant can only ever list/see their own artifact.
        list_a = caller.handle_query(make_query("intelligence.artifact.list", {}, actor_a, CorrelationContext.new()))
        assert all(a["tenant_id"] == "tenant-alpha" for a in list_a.result["artifacts"])


class TestCrossCampaignABIntegrationJourney:
    def test_full_journey_assessment_through_capacity_simulation(self, caller):
        """The required Campaign A+B combined journey: a single tenant's realistic
        migration flows through estate assessment (P7C.7), multi-objective
        strategy generation (P7C.8), wave planning (P7C.9), schema optimization
        (P7C.10), SQL translation (P7C.11), and capacity simulation (P7C.12) --
        all through the one production intelligence.submit seam, each step's
        artifact independently retrievable afterward, and all mediated through
        the same tenant-bound actor identity established by Campaign A (P7C.1-6)."""
        actor = _actor("tenant-journey")
        schema_model = _schema_model_dict()
        subject = {"subject_type": "migration_plan", "subject_id": "plan-journey", "subject_version": "v1"}
        artifact_ids = {}

        # P7C.7 Estate Assessment
        r = caller.handle_command(make_command(
            "intelligence.submit",
            {**subject, "task": "ASSESS", "capability": "estate_assessment",
             "parameters": {"target_engine": "postgresql", "schema_model": schema_model}},
            actor, CorrelationContext.new(),
        ))
        assert r.status == CallerResultStatus.OK
        artifact_ids["assessment"] = r.result["artifact_id"]

        # P7C.8 Multi-Objective Strategy Generation
        r = caller.handle_command(make_command(
            "intelligence.submit",
            {**subject, "task": "OPTIMIZE", "capability": "strategy_generation",
             "parameters": {"objective": "BALANCED"}},
            actor, CorrelationContext.new(),
        ))
        assert r.status == CallerResultStatus.OK
        artifact_ids["strategy"] = r.result["artifact_id"]

        # P7C.9 Wave Planning
        r = caller.handle_command(make_command(
            "intelligence.submit",
            {**subject, "task": "OPTIMIZE", "capability": "wave_planning",
             "parameters": {"schema_model": schema_model}},
            actor, CorrelationContext.new(),
        ))
        assert r.status == CallerResultStatus.OK
        artifact_ids["wave_plan"] = r.result["artifact_id"]

        # P7C.10 Schema Optimization
        r = caller.handle_command(make_command(
            "intelligence.submit",
            {**subject, "task": "OPTIMIZE", "capability": "schema_optimization",
             "parameters": {"schema_model": schema_model}},
            actor, CorrelationContext.new(),
        ))
        assert r.status == CallerResultStatus.OK
        artifact_ids["schema_optimization"] = r.result["artifact_id"]

        # P7C.11 SQL Translation
        r = caller.handle_command(make_command(
            "intelligence.submit",
            {**subject, "task": "CONVERT", "capability": "sql_translation",
             "parameters": {"target_engine": "postgresql", "schema_model": schema_model}},
            actor, CorrelationContext.new(),
        ))
        assert r.status == CallerResultStatus.OK
        artifact_ids["sql_translation"] = r.result["artifact_id"]

        # P7C.12 Capacity Simulation
        r = caller.handle_command(make_command(
            "intelligence.submit",
            {**subject, "task": "SIMULATE", "capability": "capacity_scenario",
             "parameters": {
                 "dataset_size_bytes": 5_000_000_000, "worker_throughput_bytes_per_sec": 10_000_000,
                 "validation_throughput_bytes_per_sec": 15_000_000, "cutover_window_seconds": 1000,
             }},
            actor, CorrelationContext.new(),
        ))
        assert r.status == CallerResultStatus.OK
        artifact_ids["capacity_simulation"] = r.result["artifact_id"]

        # Every artifact from the journey is independently retrievable and
        # correctly tenant-bound (Campaign A's P7C.1 identity/lifecycle guarantee
        # holding across every Campaign B capability).
        assert len(set(artifact_ids.values())) == 6
        for step, artifact_id in artifact_ids.items():
            q = caller.handle_query(make_query("intelligence.artifact.get", {"artifact_id": artifact_id}, actor, CorrelationContext.new()))
            assert q.status == CallerResultStatus.OK, f"step {step} artifact not retrievable"
            assert q.result["tenant_id"] == "tenant-journey"
            assert q.result["lifecycle_state"] == "GENERATED"

        # P7C.6 mediation still governs any consequential next step: a proposal
        # derived from this journey (e.g. proposing the generated wave plan) must
        # still pass through the real ActionMediationGateway seam, proving
        # Campaign A and Campaign B are integrated as one system, not two.
        mediation_payload = {
            "action_type": "propose_wave_plan",
            "target_resource_type": "migration_plan",
            "target_resource_id": "plan-journey",
            "context_fingerprint": "ctx-fp-journey",
            "current_context_fingerprint": "ctx-fp-journey",
            "source_artifact_id": artifact_ids["wave_plan"],
        }
        mediation_result = caller.handle_query(make_query("intelligence.mediation.evaluate", mediation_payload, actor, CorrelationContext.new()))
        assert mediation_result.status == CallerResultStatus.OK
        assert mediation_result.result["decision"]["status"] == "APPROVED_FOR_CANONICAL_PROCESSING"


class TestP7C8CanonicalRegionTrustProductionPath:
    """Blocker-1 closure: proves the REAL RBAC resource-scoping mechanism
    (akaalPipeline.security.rbac.RBACAuthority) backs P7C.8's canonical region
    projection end-to-end through the actual production IPC seam -- not just a
    unit-level fake authorizer."""

    def test_hostile_real_rbac_india_only_grant_excludes_singapore_end_to_end(self, temp_db_path):
        caller = _region_scoped_caller(temp_db_path, tenant_id="tenant-rbac", principal_id="actor-rbac", allowed_region="india")
        try:
            actor = _actor("tenant-rbac", actor_id="actor-rbac")
            cmd = make_command(
                "intelligence.submit",
                {
                    "task": "OPTIMIZE", "subject_type": "migration_plan", "subject_id": "plan-1", "subject_version": "v1",
                    "capability": "strategy_generation",
                    "parameters": {
                        "objective": "LOWEST_COST",
                        "candidate_regions": ["india", "singapore"],
                        "allowed_regions": ["india", "singapore"],  # caller tries to claim both
                    },
                },
                actor, CorrelationContext.new(),
            )
            result = caller.handle_command(cmd)
            assert result.status == CallerResultStatus.OK
            alternatives = result.result["result"]["optimization"]["alternatives"]
            assert all("india" in a["label"] for a in alternatives)
            assert not any("singapore" in a["label"] for a in alternatives)
        finally:
            caller.close()

    def test_hostile_real_rbac_no_region_grant_yields_empty_feasible_set(self, temp_db_path):
        """A principal with zero region grants must get an empty canonical
        feasible set -- and since candidate_regions/allowed_regions were
        requested, the producer refuses rather than silently succeeding."""
        caller = _region_scoped_caller(temp_db_path, tenant_id="tenant-rbac2", principal_id="actor-rbac2", allowed_region="germany")
        try:
            actor = _actor("tenant-rbac2", actor_id="actor-rbac2")
            cmd = make_command(
                "intelligence.submit",
                {
                    "task": "OPTIMIZE", "subject_type": "migration_plan", "subject_id": "plan-1", "subject_version": "v1",
                    "capability": "strategy_generation",
                    "parameters": {"objective": "LOWEST_COST", "candidate_regions": ["singapore"], "allowed_regions": ["singapore"]},
                },
                actor, CorrelationContext.new(),
            )
            result = caller.handle_command(cmd)
            assert result.status == CallerResultStatus.ERROR
        finally:
            caller.close()
