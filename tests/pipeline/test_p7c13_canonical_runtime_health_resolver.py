"""tests/pipeline/test_p7c13_canonical_runtime_health_resolver.py
====================================================================
P7C.13 canonical-truth correction: component-level proof that
CanonicalRuntimeHealthResolver reads ONLY real canonical authorities --
never a caller-supplied claim -- for tenant scoping and P7B Fabric ownership.

Reuses the SAME real OwnershipManager/SiteRegistry/FencingTokenManager
construction already proven correct by
tests/unit/engine_fabric/test_p7b25_ownership_leasing_fencing.py (P7B.25) --
never a second/fake ownership authority.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.durability.fencing.manager import FencingTokenManager
from akaalEngine.durability.models.state import DurabilityConfig
from akaalEngine.durability.store.sqlite import SQLiteWalBackend
from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.ownership import OwnershipClaim, OwnershipManager
from akaalEngine.fabric.ownership.models import OwnershipRecord
from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.runtime_health import make_runtime_health_producer
from akaalPipeline.contracts.enums import AuthenticationAssurance, AuthenticationState, MigrationLifecycleState, MigrationMode
from akaalPipeline.observability.runtime_health_resolver import CanonicalRuntimeHealthResolver
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.aggregates import MigrationAggregate

# Reuses the exact same real OwnershipManager/SiteRegistry/FencingTokenManager
# construction already proven correct by
# tests/unit/engine_fabric/test_p7b25_ownership_leasing_fencing.py (P7B.25) --
# duplicated locally (not imported across test modules) to avoid cross-test-file
# import coupling; never a second/fake ownership authority implementation.
_FENCING_KEY = b"p7c13-fencing-signing-key-000001"
_ANCHOR_KEY = b"p7c13-journal-anchor-key-0000002"


def _fresh_fencing_manager(tmp_path, name="fencing.db"):
    cfg = DurabilityConfig(storage_dir=str(tmp_path / name), fencing_signing_key=_FENCING_KEY, journal_anchor_key=_ANCHOR_KEY)
    backend = SQLiteWalBackend(cfg)
    backend.initialize()
    return FencingTokenManager(backend, signing_key=_FENCING_KEY)


def _trusted_site(registry: SiteRegistry, site_id="site-1", tenant_id="tenant-a", environment_id="env-1"):
    registry.register(ExecutionSite(
        site_id=site_id, site_kind=SiteKind.ON_PREM_VM, environment_id=environment_id,
        claimed_security_identity=f"spiffe://akaal.local/site/{site_id}",
    ))
    registry.verify_identity(site_id, verifier=lambda s, c: True, presented_credential="cert")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry.get(site_id)


def _claim(**overrides):
    base = dict(
        tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1", migration_id="mig-1",
        plan_id="plan-1", plan_fingerprint="fp-1", execution_identity_seal_fingerprint="seal-1",
        execution_id="exec-1", placement_id="place-1", assignment_id="assign-1",
        site_id="site-1", worker_id="worker-1", correlation_id="corr-1", ttl_seconds=30.0,
    )
    base.update(overrides)
    return OwnershipClaim(**base)


def _manager(tmp_path, name="fencing.db"):
    registry = SiteRegistry()
    _trusted_site(registry)
    fm = _fresh_fencing_manager(tmp_path, name)
    return OwnershipManager(site_registry=registry, fencing_manager=fm), registry, fm


class _FakeMigrationRepo:
    """Stands in for SQLiteMigrationRepository -- the resolver only ever
    calls get_by_id(migration_id); this double proves the resolver never
    reaches for anything else to establish canonical tenant/plan identity."""

    def __init__(self, agg: MigrationAggregate):
        self._agg = agg

    def get_by_id(self, migration_id, connection=None):
        return self._agg if migration_id == self._agg.migration_id else None


def _agg(tenant_id="tenant-a", migration_id="mig-1", plan_id="plan-1"):
    return MigrationAggregate(
        migration_id=migration_id, revision=1, name="m", mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT, tenant_id=tenant_id, workspace_id="ws-1",
        project_id="proj-1", plan_id=plan_id,
    )


def _actor(tenant_id="tenant-a"):
    return PipelineActorContext(
        actor_id="u1", actor_type="human", organization_id=tenant_id, roles=(),
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.MEDIUM, provenance="internal-core",
    )


def _kernel_with_resolver(resolver_impl: CanonicalRuntimeHealthResolver):
    kernel = IntelligenceKernel(store=IntelligenceArtifactStore())

    def resolver(request, context):
        actor = _actor(context.tenant_id)
        migration_id = request.parameters.get("migration_id") or context.subject_id
        return resolver_impl.resolve(migration_id, actor)

    kernel.register_producer(IntelligenceTask.QUERY, make_runtime_health_producer(resolver), capability="runtime_health")
    return kernel


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE intelligence_artifacts (
            artifact_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT,
            project_id TEXT, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
            subject_version TEXT NOT NULL, task TEXT NOT NULL, algorithm_version TEXT NOT NULL,
            policy_version TEXT NOT NULL, canonical_state_fingerprint TEXT NOT NULL,
            fingerprint TEXT NOT NULL, result TEXT NOT NULL, lifecycle_state TEXT NOT NULL,
            created_at TEXT NOT NULL, requested_by TEXT NOT NULL, model_provider TEXT,
            model_id TEXT, model_version TEXT, expires_at TEXT, superseded_by TEXT, updated_at TEXT
        )
        """
    )
    yield connection
    connection.close()


class TestCanonicalOwnershipDrivesFabricDimension:
    def test_active_valid_ownership_reports_fabric_healthy(self, tmp_path, conn):
        om, _, _ = _manager(tmp_path)
        om.acquire(_claim())  # real OwnershipManager.acquire -- genuine ACTIVE record
        resolver_impl = CanonicalRuntimeHealthResolver(repository=_FakeMigrationRepo(_agg()), binding_registry=None, ownership_manager=om)
        kernel = _kernel_with_resolver(resolver_impl)

        req = IntelligenceRequest(
            task=IntelligenceTask.QUERY, tenant_id="tenant-a", subject_type="migration",
            subject_id="mig-1", subject_version="v1", requested_by="user-1",
            capability="runtime_health", parameters={"migration_id": "mig-1"},
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert artifact.result["data"]["dimensions"]["FABRIC"]["status"] == "HEALTHY"

    def test_expired_ownership_is_critical_and_no_caller_channel_can_override_it(self, tmp_path, conn):
        """The real canonical lease has expired. There is no parameter in the
        production request contract through which a caller could claim
        'lease_valid=true' -- the FABRIC dimension is derived exclusively from
        OwnershipManager.try_get(), so canonical truth wins structurally, not
        merely by convention."""
        om, _, _ = _manager(tmp_path)
        rec = om.acquire(_claim())
        expired = OwnershipRecord(**{**rec.__dict__, "expires_at": "2000-01-01T00:00:00+00:00"})
        om._register_reconstructed(expired)  # real rehydration method, simulating an aged record

        resolver_impl = CanonicalRuntimeHealthResolver(repository=_FakeMigrationRepo(_agg()), binding_registry=None, ownership_manager=om)
        kernel = _kernel_with_resolver(resolver_impl)

        req = IntelligenceRequest(
            task=IntelligenceTask.QUERY, tenant_id="tenant-a", subject_type="migration",
            subject_id="mig-1", subject_version="v1", requested_by="user-1",
            capability="runtime_health",
            # A caller attempting a forged healthy claim -- structurally not a
            # recognized parameter, so it cannot influence the outcome at all.
            parameters={"migration_id": "mig-1", "fabric": {"ownership_valid": True, "lease_valid": True}},
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert artifact.result["data"]["dimensions"]["FABRIC"]["status"] == "CRITICAL"
        assert artifact.result["data"]["overall_status"] == "CRITICAL"

    def test_no_ownership_record_at_all_is_unknown_not_healthy(self, tmp_path, conn):
        om, _, _ = _manager(tmp_path)  # never acquired -- no record exists
        resolver_impl = CanonicalRuntimeHealthResolver(repository=_FakeMigrationRepo(_agg()), binding_registry=None, ownership_manager=om)
        kernel = _kernel_with_resolver(resolver_impl)

        req = IntelligenceRequest(
            task=IntelligenceTask.QUERY, tenant_id="tenant-a", subject_type="migration",
            subject_id="mig-1", subject_version="v1", requested_by="user-1",
            capability="runtime_health", parameters={"migration_id": "mig-1"},
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="migration", subject_id="mig-1", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert artifact.result["data"]["dimensions"]["FABRIC"]["status"] == "UNKNOWN"


class TestTenantEnforcementIsCanonicalNotCallerAsserted:
    def test_cross_tenant_migration_raises_regardless_of_actor_claims(self):
        from akaalPipeline.contracts.errors import PipelineError

        resolver_impl = CanonicalRuntimeHealthResolver(repository=_FakeMigrationRepo(_agg(tenant_id="tenant-beta")), binding_registry=None)
        with pytest.raises(PipelineError):
            resolver_impl.resolve("mig-1", _actor(tenant_id="tenant-alpha"))

    def test_nonexistent_migration_raises_same_error_type_as_cross_tenant(self):
        from akaalPipeline.contracts.errors import PipelineError

        resolver_impl = CanonicalRuntimeHealthResolver(repository=_FakeMigrationRepo(_agg(migration_id="mig-real")), binding_registry=None)
        with pytest.raises(PipelineError) as excinfo_missing:
            resolver_impl.resolve("mig-does-not-exist", _actor())
        with pytest.raises(PipelineError) as excinfo_wrong_tenant:
            CanonicalRuntimeHealthResolver(
                repository=_FakeMigrationRepo(_agg(tenant_id="tenant-beta", migration_id="mig-real")), binding_registry=None
            ).resolve("mig-real", _actor(tenant_id="tenant-alpha"))
        assert excinfo_missing.value.code == excinfo_wrong_tenant.value.code
