"""
tests.unit.engine_fabric.test_p7b_round2_durability
=======================================================
P7B Group-1 Hostile Review Round 2 -- fresh-process durability/reconstruction proof.

PROCESS A -> establish/persist legitimate state -> destroy A -> instantiate a genuinely
fresh registry object (PROCESS B) -> reconstruct through the canonical durability
backend -> validate identity/trust/tenant/assignment semantics -> continue safely.

Also hostile-tests: corrupt persisted state, missing state, tampered state, stale
fencing epoch surviving restart (replay protection must not reset to zero).
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.fabric.durability import (
    FabricStateCorruptError,
    FabricStateNotFoundError,
    new_sqlite_backed_store,
    reconstruct_environment_registry,
    reconstruct_site_registry,
)
from akaalEngine.fabric.environment import (
    AWSBoundary,
    Environment,
    EnvironmentSelfElevationRejectedError,
    EnvironmentTrustState,
    EnvironmentType,
)
from akaalEngine.fabric.execution_site import (
    ExecutionSite,
    SiteAssignment,
    SiteKind,
    SiteSelfElevationRejectedError,
    SiteTrustState,
    StaleFencingError,
)

SIGNING_KEY = b"durability-test-fencing-key-0001"
ANCHOR_KEY = b"durability-test-anchor-key-00002"


def _store(tmp_path):
    return new_sqlite_backed_store(str(tmp_path), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)


def test_environment_self_elevation_rejected_at_registration():
    """Round-2 finding: the first pass enforced this for sites but not environments."""
    from akaalEngine.fabric.environment import EnvironmentRegistry
    registry = EnvironmentRegistry()
    with pytest.raises(EnvironmentSelfElevationRejectedError):
        registry.register(Environment(
            environment_id="env-x", environment_type=EnvironmentType.AWS,
            boundary=AWSBoundary("123456789012"), trust_state=EnvironmentTrustState.VERIFIED,
        ))


def test_fresh_process_environment_reconstruction(tmp_path):
    store_a = _store(tmp_path)

    from akaalEngine.fabric.environment import EnvironmentRegistry
    process_a_registry = EnvironmentRegistry(durability_store=store_a)
    env = process_a_registry.register(Environment(
        environment_id="env-mumbai", environment_type=EnvironmentType.AWS,
        boundary=AWSBoundary("123456789012"), region="ap-south-1",
    ))
    process_a_registry.elevate_trust("env-mumbai", EnvironmentTrustState.VERIFIED, reason="owner review")

    # Destroy process A entirely -- no reference to process_a_registry is reused below.
    del process_a_registry

    # Genuinely fresh process/backend handle pointed at the same on-disk store.
    store_b = _store(tmp_path)
    process_b_registry = reconstruct_environment_registry(store_b)

    reconstructed = process_b_registry.get("env-mumbai")
    assert reconstructed.trust_state == EnvironmentTrustState.VERIFIED
    assert isinstance(reconstructed.boundary, AWSBoundary)
    assert reconstructed.boundary.account_id == "123456789012"

    # Reconstruction must still enforce every ordinary invariant afterward -- e.g.
    # duplicate-boundary protection remains live post-restart.
    from akaalEngine.fabric.environment import DuplicateEnvironmentIdentityError
    with pytest.raises(DuplicateEnvironmentIdentityError):
        process_b_registry.register(Environment(
            environment_id="env-attacker-claim", environment_type=EnvironmentType.AWS,
            boundary=AWSBoundary("123456789012"),
        ))


def test_fresh_process_unknown_environment_fails_safely(tmp_path):
    store = _store(tmp_path)
    registry = reconstruct_environment_registry(store)  # nothing persisted yet
    from akaalEngine.fabric.environment import UnknownEnvironmentError
    with pytest.raises(UnknownEnvironmentError):
        registry.get("env-never-existed")


def test_corrupt_persisted_environment_state_fails_closed_not_silently(tmp_path):
    store = _store(tmp_path)
    from akaalEngine.fabric.environment import EnvironmentRegistry
    registry = EnvironmentRegistry(durability_store=store)
    registry.register(Environment(environment_id="env-1", environment_type=EnvironmentType.AWS, boundary=AWSBoundary("123456789012")))

    # Directly tamper with the on-disk row (simulating disk corruption / an attacker with
    # filesystem access), bypassing the canonical write path entirely.
    conn = sqlite3.connect(store.backend.db_path)
    conn.execute(
        "UPDATE state_records SET payload_json = ? WHERE key = ? AND namespace = ?",
        ('{"environment_id": "env-1", "tampered": true}', "env-1", "fabric.environment.v1"),
    )
    conn.commit()
    conn.close()

    fresh_store = _store(tmp_path)
    with pytest.raises(FabricStateCorruptError):
        fresh_store.load_environment("env-1")


def test_fresh_process_site_trust_and_tenant_binding_survive_restart(tmp_path):
    store_a = _store(tmp_path)
    from akaalEngine.fabric.execution_site import SiteRegistry
    registry_a = SiteRegistry(durability_store=store_a)
    registry_a.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry_a.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cert")
    registry_a.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    registry_a.bind_tenant("site-1", "tenant-a", authorization_callback=lambda s, a, c: True)
    del registry_a

    store_b = _store(tmp_path)
    registry_b = reconstruct_site_registry(store_b)
    site = registry_b.get("site-1")
    assert site.trust_state == SiteTrustState.TRUSTED
    assert site.tenant_binding == "tenant-a"
    assert site.is_execution_authorized()


def test_fencing_epoch_survives_restart_preventing_replay(tmp_path):
    """Replay protection must not reset to zero across a restart -- otherwise an
    attacker (or an operator's own mistake) could reissue an already-consumed epoch
    simply by waiting for/forcing a process restart."""
    store_a = _store(tmp_path)
    from akaalEngine.fabric.execution_site import SiteRegistry
    registry_a = SiteRegistry(durability_store=store_a)
    registry_a.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.BARE_METAL, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry_a.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cert")
    registry_a.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    registry_a.bind_tenant("site-1", "tenant-a", authorization_callback=lambda s, a, c: True)
    registry_a.assign_execution(
        SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=7),
        authorization_callback=lambda s, a, c: True,
    )
    del registry_a

    store_b = _store(tmp_path)
    registry_b = reconstruct_site_registry(store_b)

    # A "restarted attacker/operator" attempt to replay epoch 7 (or anything <= 7) must
    # still be rejected even though this is a brand-new registry object.
    with pytest.raises(StaleFencingError):
        registry_b.assign_execution(
            SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=7),
            authorization_callback=lambda s, a, c: True,
        )

    # But a genuinely higher epoch after restart succeeds.
    registry_b.assign_execution(
        SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=8),
        authorization_callback=lambda s, a, c: True,
    )


def test_missing_site_state_fails_safely_after_reconstruction(tmp_path):
    store = _store(tmp_path)
    registry = reconstruct_site_registry(store)  # nothing persisted
    from akaalEngine.fabric.execution_site import UnknownSiteError
    with pytest.raises(UnknownSiteError):
        registry.get("site-never-registered")


def test_reconstructed_registry_still_enforces_self_elevation_ceiling_for_new_sites(tmp_path):
    """Reconstruction rehydrates PAST authoritative state faithfully, but the ordinary
    register() path on the same reconstructed registry must still reject a brand-new
    site attempting self-elevation -- reconstruction must not accidentally weaken the
    registry's normal invariants going forward."""
    store = _store(tmp_path)
    registry = reconstruct_site_registry(store)
    with pytest.raises(SiteSelfElevationRejectedError):
        registry.register(ExecutionSite(site_id="site-new", site_kind=SiteKind.KUBERNETES, environment_id="env-1", trust_state=SiteTrustState.TRUSTED))


def test_load_environment_for_unknown_id_raises_not_found(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(FabricStateNotFoundError):
        store.load_environment("does-not-exist")
