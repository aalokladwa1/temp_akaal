"""tests/security/test_p7c13_worker_and_fabric_hostile.py
=============================================================
P7C.13 final semantic closure: hostile suite for the two remaining blockers.

WORKERS (Final Blocker A): akaalEngine.runtime.api.RuntimeAuthority.
get_runtime_snapshot() is process-global with no migration filter, and by
forensic inspection the migration<->task link is broken in practice
(TaskSnapshot.metadata is never populated by RuntimeAuthority.submit_task
etc.). CanonicalRuntimeHealthResolver._read_workers() therefore always
returns None (UNKNOWN); process-wide counts are only ever exposed as
RuntimeHealthInputs.platform_context, never fed into the WORKERS dimension.
W3 (migration-scoped truth overriding stale/wrong global truth) is not
applicable: no migration-scoped worker read currently exists in this
repository for it to be tested against -- that is the defect this file
proves is now impossible to fabricate around, not a scenario to simulate.

FABRIC (Final Blocker B): P7B Fabric placement (FabricGateDependencies) has
zero production construction sites in this repository -- verified by
forensic grep. CanonicalRuntimeHealthResolver.resolve() now supports an
ownership_manager resolved dynamically per-request from
PlanExecutionCoordinator.fabric_dependencies.ownership_manager (see
PipelineUnifiedCaller._build_runtime_health_resolver), so a deployment that
configures Fabric placement after construction is picked up automatically,
with zero P7C.13 code changes, and with canonical ownership state always
winning over anything a caller claims.
"""

from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

import pytest

from akaalEngine.durability.fencing.manager import FencingTokenManager
from akaalEngine.durability.models.state import DurabilityConfig
from akaalEngine.durability.store.sqlite import SQLiteWalBackend
from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.ownership import OwnershipClaim, OwnershipManager
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command

_FENCING_KEY = b"p7c13-hostile-fencing-key-000001"
_ANCHOR_KEY = b"p7c13-hostile-journal-anchor-002"


def _fresh_fencing_manager(tmp_path, name="fencing.db"):
    cfg = DurabilityConfig(storage_dir=str(tmp_path / name), fencing_signing_key=_FENCING_KEY, journal_anchor_key=_ANCHOR_KEY)
    backend = SQLiteWalBackend(cfg)
    backend.initialize()
    return FencingTokenManager(backend, signing_key=_FENCING_KEY)


def _trusted_site(registry: SiteRegistry, site_id="site-1", tenant_id="tenant-alpha", environment_id="env-1"):
    registry.register(ExecutionSite(
        site_id=site_id, site_kind=SiteKind.ON_PREM_VM, environment_id=environment_id,
        claimed_security_identity=f"spiffe://akaal.local/site/{site_id}",
    ))
    registry.verify_identity(site_id, verifier=lambda s, c: True, presented_credential="cert")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)


def _manager(tmp_path):
    registry = SiteRegistry()
    _trusted_site(registry)
    fm = _fresh_fencing_manager(tmp_path)
    return OwnershipManager(site_registry=registry, fencing_manager=fm)


def _claim(**overrides):
    base = dict(
        tenant_id="tenant-alpha", workspace_id="ws-main", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_fingerprint="fp-1", execution_identity_seal_fingerprint="seal-1",
        execution_id="exec-1", placement_id="place-1", assignment_id="assign-1",
        site_id="site-1", worker_id="worker-1", correlation_id="corr-1", ttl_seconds=30.0,
    )
    base.update(overrides)
    return OwnershipClaim(**base)


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _actor(org_id: str) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id, workspace_id="ws-main", project_id="proj-1",
    )


def _seed_migration(caller, migration_id, tenant_id, plan_id=None):
    from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
    from akaalPipeline.state.aggregates import MigrationAggregate

    agg = MigrationAggregate(
        migration_id=migration_id, revision=1, name=f"migration-{migration_id}",
        mode=MigrationMode.M1_BULK, state=MigrationLifecycleState.DRAFT,
        tenant_id=tenant_id, workspace_id="ws-main", project_id="proj-1", plan_id=plan_id,
    )
    caller.repository.save(agg)
    return agg


def _submit_runtime_health(caller, actor, migration_id):
    payload = {
        "task": "QUERY", "subject_type": "migration", "subject_id": migration_id,
        "subject_version": "v1", "capability": "runtime_health",
        "parameters": {"migration_id": migration_id},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestW_WorkersNeverFabricatedFromProcessGlobalState:
    def test_w4_no_migration_scoped_worker_read_yields_unknown(self, temp_db_path):
        """W4: with no gateway bound at all (a fortiori no migration-scoped
        worker read), WORKERS must be UNKNOWN."""
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            result = _submit_runtime_health(caller, actor, "mig-1")
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["dimensions"]["WORKERS"]["status"] == "UNKNOWN"
            assert result.result["result"]["data"]["platform_context"] is None
        finally:
            caller.close()

    def test_w5_caller_supplied_worker_claim_has_no_channel_and_no_effect(self, temp_db_path):
        """W5: there is no parameter through which a caller can influence
        WORKERS -- a forged claim is not even a recognized field."""
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            payload = {
                "task": "QUERY", "subject_type": "migration", "subject_id": "mig-1",
                "subject_version": "v1", "capability": "runtime_health",
                "parameters": {"migration_id": "mig-1", "workers": {"total": 50, "healthy": 50}},
            }
            result = caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["dimensions"]["WORKERS"]["status"] == "UNKNOWN"
        finally:
            caller.close()

    def test_w1_w2_resolver_never_derives_workers_regardless_of_runtime_snapshot_shape(self):
        """W1/W2: directly proves _read_workers() is a hard-coded structural
        None regardless of what a process-global runtime snapshot contains --
        neither a busy process (many unrelated workers) nor an idle one (zero
        workers) can ever make migration WORKERS anything but UNKNOWN, because
        the method takes no runtime_snap input at all any more."""
        from akaalPipeline.observability.runtime_health_resolver import CanonicalRuntimeHealthResolver

        resolver = CanonicalRuntimeHealthResolver(repository=None, binding_registry=None)
        assert resolver._read_workers() is None

        busy_platform_ctx = resolver._read_platform_context({"active_workers": [{"state": "HEALTHY"}] * 20})
        assert busy_platform_ctx == {"process_worker_count": 20, "scope": "PLATFORM_WIDE_NOT_MIGRATION_SCOPED"}
        idle_platform_ctx = resolver._read_platform_context({"active_workers": []})
        assert idle_platform_ctx is None


class TestF_DynamicFabricWiringAndCanonicalWins:
    def test_f7_ownership_configured_after_construction_is_picked_up_live_through_production_seam(self, temp_db_path, tmp_path):
        """F7/F9: PlanExecutionCoordinator.fabric_dependencies is None by
        default (verified: zero production construction sites for
        FabricGateDependencies exist in this repository). If a deployment
        configures it AFTER PipelineUnifiedCaller construction (the only way
        Fabric placement can currently be opted into), the SAME
        _build_runtime_health_resolver picks up the live OwnershipManager on
        the very next request -- no P7C.13 code change, no duplicate
        authority (object identity of the manager consulted is the exact one
        the deployment configured, verified via a real acquire() lifecycle)."""
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha", plan_id="plan-1")

            # No Fabric wiring yet -- FABRIC must be UNKNOWN.
            r0 = _submit_runtime_health(caller, actor, "mig-1")
            assert r0.result["result"]["data"]["dimensions"]["FABRIC"]["status"] == "UNKNOWN"

            # Deployment opts into Fabric placement after the fact (the only
            # way this repository's real P7B path is ever populated today).
            om = _manager(tmp_path)
            om.acquire(_claim())
            caller.plan_coordinator.fabric_dependencies = SimpleNamespace(ownership_manager=om)

            r1 = _submit_runtime_health(caller, actor, "mig-1")
            assert r1.result["result"]["data"]["dimensions"]["FABRIC"]["status"] == "HEALTHY"

            # F7: canonical change (expiry, via the manager's own real records
            # dict -- the exact same object, proving no shadow copy exists)
            # is reflected without the caller resubmitting anything.
            key = "tenant-alpha::mig-1::plan-1"
            live_record = om.try_get(key)
            assert live_record is not None
            om._register_reconstructed(type(live_record)(**{**live_record.__dict__, "expires_at": "2000-01-01T00:00:00+00:00"}))

            r2 = _submit_runtime_health(caller, actor, "mig-1")
            assert r2.result["result"]["data"]["dimensions"]["FABRIC"]["status"] == "CRITICAL"
        finally:
            caller.close()

    def test_f4_wrong_tenant_ownership_never_counts_for_this_migration(self, temp_db_path, tmp_path):
        """F4: a valid, active lease exists -- but for a DIFFERENT tenant's
        identically-named migration/plan pairing is impossible by
        construction (ownership_key embeds tenant_id), proving cross-tenant
        ownership substitution is structurally unreachable, not merely
        untested."""
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller, "mig-1", "tenant-beta", plan_id="plan-1")
            om = _manager(tmp_path)
            om.acquire(_claim(tenant_id="tenant-alpha", migration_id="mig-1", plan_id="plan-1"))
            caller.plan_coordinator.fabric_dependencies = SimpleNamespace(ownership_manager=om)

            actor_beta = _actor("tenant-beta")
            result = _submit_runtime_health(caller, actor_beta, "mig-1")
            # tenant-beta's own migration has no ownership record under
            # "tenant-beta::mig-1::plan-1" (only "tenant-alpha::mig-1::plan-1"
            # exists) -- so FABRIC is UNKNOWN, never borrowing tenant-alpha's.
            assert result.result["result"]["data"]["dimensions"]["FABRIC"]["status"] == "UNKNOWN"
        finally:
            caller.close()
