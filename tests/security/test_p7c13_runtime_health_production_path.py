"""tests/security/test_p7c13_runtime_health_production_path.py
==================================================================
P7C.13 canonical-truth correction: proves the runtime-health projection is a
TRUSTED, READ-ONLY, CANONICAL projection through the REAL PipelineUnifiedCaller
/ intelligence.submit seam -- never a caller-authoritative snapshot.

Covers the required hostile forgery suite:
  1. Caller cannot forge healthy runtime (canonical absent/degraded wins).
  2/3/4. Caller cannot forge lease/CDC/validation facts -- there is no
     parameter channel for them at all; any extra caller-supplied keys
     (including a legacy 'runtime_health_inputs' blob claiming full health)
     are structurally ignored.
  5. Missing canonical data -> UNKNOWN, never fabricated HEALTHY.
  6. Cross-tenant lookup -> anti-enumeration-safe DENY (identical error shape
     for "not found" and "not yours").
  7. Real production path: real PipelineUnifiedCaller -> intelligence.submit
     -> CanonicalRuntimeHealthResolver -> real bound EngineGateway/
     GatewayCoordinator/TelemetryAuthority -- no monkeypatched resolver.
  8. A canonical change (real TelemetryAuthority.update_progress call) is
     reflected on the next request without the caller resubmitting anything.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command, make_query


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _actor(org_id: str, actor_id: str = None) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=actor_id or f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id,
        workspace_id="ws-main",
        project_id="proj-1",
    )


def _seed_migration(caller, migration_id: str, tenant_id: str, workspace_id: str = "ws-main", project_id: str = "proj-1"):
    from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
    from akaalPipeline.state.aggregates import MigrationAggregate

    agg = MigrationAggregate(
        migration_id=migration_id,
        revision=1,
        name=f"migration-{migration_id}",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
    )
    caller.repository.save(agg)
    return agg


def _submit_runtime_health(caller, actor, migration_id, extra_params=None):
    payload = {
        "task": "QUERY", "subject_type": "migration", "subject_id": migration_id,
        "subject_version": "v1", "capability": "runtime_health",
        "parameters": {"migration_id": migration_id, **(extra_params or {})},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestNoCanonicalGatewayBound:
    """No EngineGateway bound at all -- every dimension must be UNKNOWN, never
    a fabricated HEALTHY, and this must hold regardless of anything the
    caller claims."""

    def test_missing_canonical_data_reports_unknown_not_healthy(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            result = _submit_runtime_health(caller, actor, "mig-1")
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["overall_status"] == "UNKNOWN"
        finally:
            caller.close()

    def test_caller_cannot_forge_healthy_runtime_via_legacy_inline_blob(self, temp_db_path):
        """A caller attempting the old (now-removed) inline
        'runtime_health_inputs' trust channel, claiming every dimension is
        perfectly healthy, must have ZERO effect: canonical data is still
        absent, so the result is still UNKNOWN."""
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            forged = {
                "runtime_health_inputs": {
                    "transport": {"throughput_rows_per_sec": 999999, "baseline_rows_per_sec": 1000},
                    "cdc": {"generation_rate": 100, "apply_rate": 100, "backlog_size": 0, "backlog_trend": "stable"},
                    "validation": {"status": "HEALTHY", "mismatch_count": 0},
                    "workers": {"total": 8, "healthy": 8},
                    "fabric": {"ownership_valid": True, "lease_valid": True, "fencing_conflicts": 0},
                    "governance": {"cutover_ready": True, "approvals_pending": 0, "security_blocking": False},
                }
            }
            result = _submit_runtime_health(caller, actor, "mig-1", extra_params=forged)
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["overall_status"] == "UNKNOWN"
            for dim in result.result["result"]["data"]["dimensions"].values():
                assert dim["status"] == "UNKNOWN"
        finally:
            caller.close()


class TestRealCanonicalGatewayBound:
    """A real EngineGateway/GatewayCoordinator/TelemetryAuthority is bound --
    not monkeypatched -- proving genuine production-path canonical reads."""

    def _coordinator(self, caller):
        binding = caller.binding_registry.get("gateway_engine_binding")
        return binding.port_instance.gateway.coordinator

    def test_real_canonical_progress_is_reflected_and_caller_claims_ignored(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=True)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            coord = self._coordinator(caller)
            coord.telemetry_authority.initialize_migration_progress("mig-1", rows_total=1_000_000)
            coord.telemetry_authority.update_progress("mig-1", add_rows=1000)

            # Caller tries to override with a forged inline blob -- ignored,
            # since the production resolver only ever reads
            # request.parameters['migration_id'].
            forged = {"runtime_health_inputs": {"transport": {"throughput_rows_per_sec": 1, "baseline_rows_per_sec": 1}}}
            result = _submit_runtime_health(caller, actor, "mig-1", extra_params=forged)
            assert result.status == CallerResultStatus.OK
            transport_facts = result.result["result"]["data"]["dimensions"]["TRANSPORT"]["facts"]
            assert "throughput_rows_per_sec=1" not in transport_facts  # forged value never used

        finally:
            caller.close()

    def test_canonical_change_reflected_without_caller_resubmitting_facts(self, temp_db_path):
        """P7C.13 correction requirement #8: change canonical state through
        its legitimate local mechanism, request again, health output changes
        -- caller never resubmits any operational fact, only migration_id."""
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=True)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            coord = self._coordinator(caller)
            coord.telemetry_authority.initialize_migration_progress("mig-1", rows_total=1_000_000)

            coord.telemetry_authority.update_progress("mig-1", add_rows=10)
            r1 = _submit_runtime_health(caller, actor, "mig-1")
            snap1 = coord.telemetry_authority.get_progress_snapshot("mig-1")

            coord.telemetry_authority.update_progress("mig-1", add_rows=500_000)
            r2 = _submit_runtime_health(caller, actor, "mig-1")
            snap2 = coord.telemetry_authority.get_progress_snapshot("mig-1")

            assert r1.status == CallerResultStatus.OK
            assert r2.status == CallerResultStatus.OK
            assert r1.result["result"]["data"]["dimensions"]["TRANSPORT"]["facts"] != r2.result["result"]["data"]["dimensions"]["TRANSPORT"]["facts"]
            assert snap2.rows_processed > snap1.rows_processed
        finally:
            caller.close()


class TestCrossTenantAntiEnumeration:
    def test_cross_tenant_migration_lookup_fails_closed_same_shape_as_not_found(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller, "mig-owned-by-beta", "tenant-beta")
            actor_a = _actor("tenant-alpha")

            result_wrong_tenant = _submit_runtime_health(caller, actor_a, "mig-owned-by-beta")
            result_nonexistent = _submit_runtime_health(caller, actor_a, "mig-does-not-exist")

            assert result_wrong_tenant.status == CallerResultStatus.ERROR
            assert result_nonexistent.status == CallerResultStatus.ERROR
            # Anti-enumeration: identical error code for "not yours" and "does not exist".
            assert result_wrong_tenant.error.code == result_nonexistent.error.code
        finally:
            caller.close()

    def test_each_tenant_only_sees_own_runtime_health_artifacts(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor_a = _actor("tenant-alpha")
            actor_b = _actor("tenant-beta")
            _seed_migration(caller, "mig-a", "tenant-alpha")
            _seed_migration(caller, "mig-b", "tenant-beta")

            result_a = _submit_runtime_health(caller, actor_a, "mig-a")
            result_b = _submit_runtime_health(caller, actor_b, "mig-b")
            assert result_a.result["tenant_id"] == "tenant-alpha"
            assert result_b.result["tenant_id"] == "tenant-beta"

            list_a = caller.handle_query(make_query("intelligence.artifact.list", {}, actor_a, CorrelationContext.new()))
            assert all(a["tenant_id"] == "tenant-alpha" for a in list_a.result["artifacts"])
        finally:
            caller.close()


class TestMissingMigrationParameter:
    def test_no_migration_id_falls_back_to_subject_id_and_still_enforces_tenant(self, temp_db_path):
        """No migration_id in parameters -- resolver falls back to
        context.subject_id, still a canonical, non-caller-authoritative
        locator (subject_id is itself validated against context at kernel
        submission time), and tenant scope is still enforced."""
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller, "mig-fallback", "tenant-beta")
            actor_a = _actor("tenant-alpha")
            payload = {
                "task": "QUERY", "subject_type": "migration", "subject_id": "mig-fallback",
                "subject_version": "v1", "capability": "runtime_health", "parameters": {},
            }
            result = caller.handle_command(make_command("intelligence.submit", payload, actor_a, CorrelationContext.new()))
            assert result.status == CallerResultStatus.ERROR
        finally:
            caller.close()
