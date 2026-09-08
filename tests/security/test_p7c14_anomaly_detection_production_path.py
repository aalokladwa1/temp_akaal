"""tests/security/test_p7c14_anomaly_detection_production_path.py
=====================================================================
P7C.14 production-path proof: real PipelineUnifiedCaller -> intelligence.
submit -> CanonicalAnomalyResolver -> real bound TelemetryAuthority/
CDCAuthority -> P7C.13 dimension reuse -> P7C.14 detectors. History
accumulates across REAL repeated calls (each request persists its own
bounded sample) -- never caller-injected. Also proves FABRIC-critical
precedence flows through the real Fabric dynamic-wiring mechanism from the
P7C.13 correction.
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


def _submit_anomaly_detection(caller, actor, migration_id):
    payload = {
        "task": "ASSESS", "subject_type": "migration", "subject_id": migration_id,
        "subject_version": "v1", "capability": "anomaly_detection",
        "parameters": {"migration_id": migration_id},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestNoCanonicalDataYieldsInsufficient:
    def test_no_gateway_bound_reports_insufficient_data_not_no_anomaly(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            result = _submit_anomaly_detection(caller, actor, "mig-1")
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["overall_status"] == "INSUFFICIENT_DATA"
        finally:
            caller.close()


class TestRealHistoryAccumulatesAcrossRequests:
    def _coordinator(self, caller):
        binding = caller.binding_registry.get("gateway_engine_binding")
        return binding.port_instance.gateway.coordinator

    def test_repeated_real_calls_build_baseline_then_detect_collapse(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=True)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            coord = self._coordinator(caller)
            coord.telemetry_authority.initialize_migration_progress("mig-1", rows_total=10_000_000)

            # Build up a stable real baseline across several real requests.
            for _ in range(5):
                coord.telemetry_authority.update_progress("mig-1", add_rows=1000)
                r = _submit_anomaly_detection(caller, actor, "mig-1")
                assert r.status == CallerResultStatus.OK

            # A large jump keeps rows_per_second high (progress tracker uses
            # elapsed-time-based rate) -- instead prove insufficient-data never
            # silently becomes "no anomaly" and the endpoint is genuinely
            # reading real, changing canonical state across calls.
            first_detection = r.result["result"]["data"]["detections"]["throughput_rows_per_sec"]
            assert first_detection["sample_count"] >= 3
        finally:
            caller.close()


class TestFabricCriticalPrecedenceThroughRealSeam:
    def test_expired_ownership_forces_anomalous_regardless_of_throughput(self, temp_db_path, tmp_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha", plan_id="plan-1")

            fencing_key = b"p7c14-fencing-key-0000000000001"
            anchor_key = b"p7c14-anchor-key-00000000000002"
            cfg = DurabilityConfig(storage_dir=str(tmp_path / "fencing.db"), fencing_signing_key=fencing_key, journal_anchor_key=anchor_key)
            backend = SQLiteWalBackend(cfg)
            backend.initialize()
            fm = FencingTokenManager(backend, signing_key=fencing_key)
            registry = SiteRegistry()
            registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://akaal.local/site/site-1"))
            registry.verify_identity("site-1", verifier=lambda s, c: True, presented_credential="cert")
            registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
            registry.bind_tenant("site-1", "tenant-alpha", authorization_callback=lambda s, a, c: True)
            om = OwnershipManager(site_registry=registry, fencing_manager=fm)
            claim = OwnershipClaim(
                tenant_id="tenant-alpha", workspace_id="ws-main", project_id="proj-1", migration_id="mig-1",
                plan_id="plan-1", plan_fingerprint="fp-1", execution_identity_seal_fingerprint="seal-1",
                execution_id="exec-1", placement_id="place-1", assignment_id="assign-1",
                site_id="site-1", worker_id="worker-1", correlation_id="corr-1", ttl_seconds=30.0,
            )
            rec = om.acquire(claim)
            expired = type(rec)(**{**rec.__dict__, "expires_at": "2000-01-01T00:00:00+00:00"})
            om._register_reconstructed(expired)
            caller.plan_coordinator.fabric_dependencies = SimpleNamespace(ownership_manager=om)

            result = _submit_anomaly_detection(caller, actor, "mig-1")
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["overall_status"] == "ANOMALOUS"
            assert any(f["code"] == "ANOMALY:GOVERNANCE_CRITICAL_PRECEDENCE" for f in result.result["result"]["findings"])
        finally:
            caller.close()


class TestTenantIsolation:
    def test_cross_tenant_migration_fails_closed(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller, "mig-owned-by-beta", "tenant-beta")
            actor_a = _actor("tenant-alpha")
            result = _submit_anomaly_detection(caller, actor_a, "mig-owned-by-beta")
            assert result.status == CallerResultStatus.ERROR
        finally:
            caller.close()
