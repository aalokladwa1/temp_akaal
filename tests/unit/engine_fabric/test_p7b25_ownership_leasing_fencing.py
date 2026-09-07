"""
tests.unit.engine_fabric.test_p7b25_ownership_leasing_fencing
==================================================================
P7B.25 -- Distributed Execution Ownership, Leasing & Fencing hostile test suite.

Proves OwnershipManager (composed over the frozen P7B.5 SiteRegistry and Durability
Authority #5 FencingTokenManager -- no duplicate trust or fencing authority) enforces:
    * exactly one valid owner per (tenant, migration, plan) unit of work
    * atomic acquisition under concurrency
    * renewal validates lease identity/owner identity/tenant/plan/seal/assignment/site/
      worker/current site trust/fencing generation/expiry
    * expired ownership grants no authority
    * controlled transfer with old-owner staleness (ABA protection)
    * fresh-process reconstruction preserves fencing generations and does not resurrect
      expired/stale ownership
    * cross-tenant / wrong-plan / wrong-seal / wrong-site / wrong-worker / wrong-assignment
      substitution is refused
"""

from __future__ import annotations

import threading
import time

import pytest

from akaalEngine.durability.fencing.manager import FencingTokenManager
from akaalEngine.durability.models.state import DurabilityConfig
from akaalEngine.durability.store.sqlite import SQLiteWalBackend
from akaalEngine.fabric.durability import new_sqlite_backed_store, reconstruct_ownership_manager, reconstruct_site_registry
from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.ownership import (
    LeaseConflictError,
    LeaseExpiredError,
    OwnershipClaim,
    OwnershipManager,
    SiteNotExecutionReadyError,
    StaleFencingGenerationError,
    UnknownOwnershipError,
    WrongAssignmentOwnershipError,
    WrongExecutionOwnershipError,
    WrongPlanOwnershipError,
    WrongTenantOwnershipError,
    WrongSealOwnershipError,
    WrongSiteOwnershipError,
    WrongWorkerOwnershipError,
)

FENCING_KEY = b"p7b25-fencing-signing-key-000001"
SIGNING_KEY = b"p7b25-durability-store-key-00001"
ANCHOR_KEY = b"p7b25-journal-anchor-key-0000002"


def _fresh_fencing_manager(tmp_path, name="fencing.db"):
    cfg = DurabilityConfig(storage_dir=str(tmp_path / name), fencing_signing_key=FENCING_KEY, journal_anchor_key=ANCHOR_KEY)
    backend = SQLiteWalBackend(cfg)
    backend.initialize()
    return FencingTokenManager(backend, signing_key=FENCING_KEY)


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


# ----------------------------------------------------------------------
# Basic acquisition / exactly-one-owner
# ----------------------------------------------------------------------

def test_acquire_grants_generation_one_for_first_claimant(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    assert rec.fencing_generation == 1
    assert rec.worker_id == "worker-1"


def test_duplicate_acquisition_by_different_worker_is_rejected(tmp_path):
    om, _, _ = _manager(tmp_path)
    om.acquire(_claim())
    with pytest.raises(LeaseConflictError):
        om.acquire(_claim(worker_id="worker-2"))


def test_same_worker_reacquiring_before_expiry_is_treated_as_renewal_not_new_generation(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec1 = om.acquire(_claim())
    rec2 = om.acquire(_claim())
    assert rec1.fencing_generation == rec2.fencing_generation
    assert rec1.lease_id == rec2.lease_id


def test_acquire_requires_site_execution_ready(tmp_path):
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1"))
    fm = _fresh_fencing_manager(tmp_path)
    om = OwnershipManager(site_registry=registry, fencing_manager=fm)
    with pytest.raises(SiteNotExecutionReadyError):
        om.acquire(_claim())


def test_acquire_rejects_cross_tenant_site_substitution(tmp_path):
    """Site is trusted and bound to tenant-a; a claim for tenant-b at the same site must
    be refused even though the site itself is perfectly healthy/trusted."""
    om, _, _ = _manager(tmp_path)
    with pytest.raises(SiteNotExecutionReadyError):
        om.acquire(_claim(tenant_id="tenant-b"))


# ----------------------------------------------------------------------
# Renewal validation matrix
# ----------------------------------------------------------------------

def test_renewal_rejects_wrong_lease_id(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(LeaseConflictError):
        om.renew(_claim(), lease_id="forged-lease-id", fencing_generation=rec.fencing_generation)


def test_renewal_rejects_stale_fencing_generation(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(StaleFencingGenerationError):
        om.renew(_claim(), lease_id=rec.lease_id, fencing_generation=rec.fencing_generation + 1)


def test_renewal_rejects_wrong_tenant(tmp_path):
    om, registry, fm = _manager(tmp_path)
    _trusted_site(registry, site_id="site-1b", tenant_id="tenant-b")
    rec = om.acquire(_claim())
    bad = _claim(tenant_id="tenant-b", migration_id="mig-1", plan_id="plan-1")
    # ownership_key would differ (tenant embedded in key) -> surfaces as UnknownOwnershipError,
    # which is itself a correct "no such ownership for this claim" fail-safe outcome.
    with pytest.raises(UnknownOwnershipError):
        om.renew(bad, lease_id=rec.lease_id, fencing_generation=rec.fencing_generation)


def test_renewal_rejects_wrong_plan_fingerprint(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(WrongPlanOwnershipError):
        om.renew(_claim(plan_fingerprint="tampered-fp"), lease_id=rec.lease_id, fencing_generation=rec.fencing_generation)


def test_renewal_rejects_wrong_seal(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(WrongSealOwnershipError):
        om.renew(_claim(execution_identity_seal_fingerprint="tampered-seal"), lease_id=rec.lease_id, fencing_generation=rec.fencing_generation)


def test_renewal_with_a_fresh_assignment_id_updates_it_not_rejected(tmp_path):
    """Design finding from P7B.25/production-integration hostile review: a legitimate,
    long-running physical dispatch (execute_via_placement) reissues a FRESH signed
    RemoteExecutionAssignment on every call for the SAME ownership generation (Group-1's
    own, unmodified assignment-issuance behavior) -- so assignment_id must be an
    UPDATABLE field on renewal, never a frozen must-match-forever one (which would
    incorrectly fence a renewing owner's own legitimate re-dispatch). What genuinely must
    never happen -- accepting an assignment for a DIFFERENT site/tenant/plan -- is proven
    separately by assignment_consistent_with_ownership (see
    test_assignment_consistency_check below) and by the tenant/plan/seal checks already
    covered above."""
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    renewed = om.renew(_claim(assignment_id="assign-2-fresh-reissue"), lease_id=rec.lease_id, fencing_generation=rec.fencing_generation)
    assert renewed.assignment_id == "assign-2-fresh-reissue"
    assert renewed.lease_id == rec.lease_id
    assert renewed.fencing_generation == rec.fencing_generation


def test_assignment_consistency_check_accepts_matching_assignment(tmp_path):
    from akaalEngine.fabric.ownership import assignment_consistent_with_ownership
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    assignment_consistent_with_ownership(rec, assignment_site_id=rec.site_id, assignment_tenant_id=rec.tenant_id, assignment_plan_id=rec.plan_id)


def test_assignment_consistency_check_rejects_substituted_plan(tmp_path):
    from akaalEngine.fabric.ownership import assignment_consistent_with_ownership
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(WrongAssignmentOwnershipError):
        assignment_consistent_with_ownership(rec, assignment_site_id=rec.site_id, assignment_tenant_id=rec.tenant_id, assignment_plan_id="plan-substituted")


def test_assignment_consistency_check_rejects_substituted_site(tmp_path):
    from akaalEngine.fabric.ownership import assignment_consistent_with_ownership
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(WrongSiteOwnershipError):
        assignment_consistent_with_ownership(rec, assignment_site_id="site-substituted", assignment_tenant_id=rec.tenant_id, assignment_plan_id=rec.plan_id)


def test_assignment_consistency_check_rejects_substituted_tenant(tmp_path):
    from akaalEngine.fabric.ownership import assignment_consistent_with_ownership
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(WrongTenantOwnershipError):
        assignment_consistent_with_ownership(rec, assignment_site_id=rec.site_id, assignment_tenant_id="tenant-substituted", assignment_plan_id=rec.plan_id)


def test_renewal_rejects_wrong_execution(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(WrongExecutionOwnershipError):
        om.renew(_claim(execution_id="exec-forged"), lease_id=rec.lease_id, fencing_generation=rec.fencing_generation)


def test_renewal_rejects_wrong_worker(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(WrongWorkerOwnershipError):
        om.renew(_claim(worker_id="worker-impostor"), lease_id=rec.lease_id, fencing_generation=rec.fencing_generation)


def test_renewal_rejects_wrong_site(tmp_path):
    om, registry, _ = _manager(tmp_path)
    _trusted_site(registry, site_id="site-2")
    rec = om.acquire(_claim())
    with pytest.raises(WrongSiteOwnershipError):
        om.renew(_claim(site_id="site-2"), lease_id=rec.lease_id, fencing_generation=rec.fencing_generation)


def test_renewal_rejects_expired_lease(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim(ttl_seconds=0.05))
    time.sleep(0.12)
    with pytest.raises(LeaseExpiredError):
        om.renew(_claim(ttl_seconds=0.05), lease_id=rec.lease_id, fencing_generation=rec.fencing_generation)


def test_renewal_fails_closed_when_site_revoked_after_acquisition(tmp_path):
    om, registry, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    registry.revoke("site-1", reason="hostile-test revocation mid-lease")
    with pytest.raises(SiteNotExecutionReadyError):
        om.renew(_claim(), lease_id=rec.lease_id, fencing_generation=rec.fencing_generation)


def test_unknown_ownership_renewal_fails_safe(tmp_path):
    om, _, _ = _manager(tmp_path)
    with pytest.raises(UnknownOwnershipError):
        om.renew(_claim(), lease_id="lease-x", fencing_generation=1)


# ----------------------------------------------------------------------
# Expiry -- expired ownership grants no authority
# ----------------------------------------------------------------------

def test_expired_lease_fails_validate(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim(ttl_seconds=0.05))
    time.sleep(0.12)
    with pytest.raises(LeaseExpiredError):
        om.validate(rec.ownership_key, rec.lease_id, rec.fencing_generation)


def test_expired_lease_permits_new_generation_for_a_different_worker(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec1 = om.acquire(_claim(ttl_seconds=0.05))
    time.sleep(0.12)
    rec2 = om.acquire(_claim(worker_id="worker-2"))
    assert rec2.fencing_generation > rec1.fencing_generation
    assert rec2.worker_id == "worker-2"


def test_expired_lease_forces_fresh_generation_even_for_same_worker(tmp_path):
    """Even the ORIGINAL owner must not silently continue on the old generation after its
    own lease expires -- re-acquisition mints a brand-new fencing generation, invalidating
    any zombie in-process caller still holding the old generation number."""
    om, _, _ = _manager(tmp_path)
    rec1 = om.acquire(_claim(ttl_seconds=0.05))
    time.sleep(0.12)
    rec2 = om.acquire(_claim())
    assert rec2.fencing_generation > rec1.fencing_generation
    # rec1's lease_id is also superseded (a fresh generation mints a fresh lease_id too),
    # so the rejection surfaces as LeaseConflictError (lease_id mismatch checked first) --
    # both LeaseConflictError and StaleFencingGenerationError are equally valid "stale
    # owner rejected" outcomes; what matters is that rec1 is never again treated as current.
    with pytest.raises((LeaseConflictError, StaleFencingGenerationError)):
        om.validate(rec1.ownership_key, rec1.lease_id, rec1.fencing_generation)


# ----------------------------------------------------------------------
# Transfer + ABA protection
# ----------------------------------------------------------------------

def test_controlled_transfer_advances_generation_and_stales_old_owner(tmp_path):
    om, registry, _ = _manager(tmp_path)
    _trusted_site(registry, site_id="site-2")
    rec_a = om.acquire(_claim())
    rec_b = om.transfer(rec_a.lease_id, rec_a.fencing_generation, _claim(site_id="site-2", worker_id="worker-2"))

    assert rec_b.fencing_generation == rec_a.fencing_generation + 1
    assert rec_b.worker_id == "worker-2"

    # Old owner A is now stale on every axis (transfer mints both a new lease_id and a
    # new fencing generation, so rejection may surface as either exception -- both are
    # equally valid "A is no longer the owner" outcomes).
    with pytest.raises((LeaseConflictError, StaleFencingGenerationError)):
        om.validate(rec_a.ownership_key, rec_a.lease_id, rec_a.fencing_generation)
    with pytest.raises(LeaseConflictError):
        om.renew(_claim(), lease_id=rec_a.lease_id, fencing_generation=rec_a.fencing_generation)


def test_aba_old_owner_cannot_be_confused_with_new_generation_after_reappearing(tmp_path):
    """A owns (gen 1) -> transfer -> B owns (gen 2) -> A's process, unaware, tries to
    validate/renew/transfer again using its old gen-1 lease -- must be rejected outright,
    never treated as still-current merely because gen 1 was once legitimate."""
    om, registry, _ = _manager(tmp_path)
    _trusted_site(registry, site_id="site-2")
    rec_a = om.acquire(_claim())
    om.transfer(rec_a.lease_id, rec_a.fencing_generation, _claim(site_id="site-2", worker_id="worker-2"))

    with pytest.raises(LeaseConflictError):
        om.transfer(rec_a.lease_id, rec_a.fencing_generation, _claim(worker_id="worker-3"))
    with pytest.raises((LeaseConflictError, StaleFencingGenerationError)):
        om.validate(rec_a.ownership_key, rec_a.lease_id, rec_a.fencing_generation)


def test_transfer_requires_new_site_execution_ready(tmp_path):
    om, registry, _ = _manager(tmp_path)
    registry.register(ExecutionSite(site_id="site-untrusted", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1"))
    rec = om.acquire(_claim())
    with pytest.raises(SiteNotExecutionReadyError):
        om.transfer(rec.lease_id, rec.fencing_generation, _claim(site_id="site-untrusted", worker_id="worker-2"))


def test_transfer_to_wholly_unknown_site_fails_safe(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(KeyError):
        om.transfer(rec.lease_id, rec.fencing_generation, _claim(site_id="site-does-not-exist", worker_id="worker-2"))


def test_transfer_preserves_tenant_plan_seal_execution_identity(tmp_path):
    om, registry, _ = _manager(tmp_path)
    _trusted_site(registry, site_id="site-2")
    rec_a = om.acquire(_claim())
    rec_b = om.transfer(rec_a.lease_id, rec_a.fencing_generation, _claim(site_id="site-2", worker_id="worker-2"))
    assert rec_b.tenant_id == rec_a.tenant_id
    assert rec_b.plan_id == rec_a.plan_id
    assert rec_b.plan_fingerprint == rec_a.plan_fingerprint
    assert rec_b.execution_identity_seal_fingerprint == rec_a.execution_identity_seal_fingerprint
    assert rec_b.execution_id == rec_a.execution_id


def test_transfer_of_already_expired_lease_is_rejected(tmp_path):
    om, registry, _ = _manager(tmp_path)
    _trusted_site(registry, site_id="site-2")
    rec = om.acquire(_claim(ttl_seconds=0.05))
    time.sleep(0.12)
    with pytest.raises(LeaseExpiredError):
        om.transfer(rec.lease_id, rec.fencing_generation, _claim(site_id="site-2", worker_id="worker-2"))


# ----------------------------------------------------------------------
# Release
# ----------------------------------------------------------------------

def test_release_then_reacquire_mints_new_generation(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    om.release(rec.ownership_key, rec.lease_id, rec.fencing_generation)
    rec2 = om.acquire(_claim(worker_id="worker-2"))
    assert rec2.fencing_generation == rec.fencing_generation + 1


def test_release_requires_matching_lease(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(LeaseConflictError):
        om.release(rec.ownership_key, "forged-lease", rec.fencing_generation)


# ----------------------------------------------------------------------
# Concurrency -- exactly one winner under simultaneous acquisition
# ----------------------------------------------------------------------

def test_concurrent_acquisition_yields_exactly_one_winner(tmp_path):
    om, registry, _ = _manager(tmp_path)
    for i in range(16):
        _trusted_site(registry, site_id=f"site-c{i}")

    winners = []
    conflicts = []
    lock = threading.Lock()

    def attempt(i):
        try:
            rec = om.acquire(_claim(site_id=f"site-c{i}", worker_id=f"worker-c{i}"))
            with lock:
                winners.append(rec)
        except LeaseConflictError:
            with lock:
                conflicts.append(i)

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(winners) == 1
    assert len(conflicts) == 15


def test_concurrent_renewal_by_true_owner_never_raises(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim(ttl_seconds=5.0))
    errors = []

    def do_renew():
        try:
            om.renew(_claim(ttl_seconds=5.0), rec.lease_id, rec.fencing_generation)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=do_renew) for _ in range(32)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors


# ----------------------------------------------------------------------
# Fresh-process reconstruction (restart)
# ----------------------------------------------------------------------

def test_restart_preserves_fencing_generation_and_active_ownership(tmp_path):
    ownership_store = new_sqlite_backed_store(str(tmp_path / "ownership_store"), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)
    site_registry_a = SiteRegistry(durability_store=ownership_store)
    _trusted_site(site_registry_a)
    fm = _fresh_fencing_manager(tmp_path, "fencing_restart.db")
    om_a = OwnershipManager(site_registry=site_registry_a, fencing_manager=fm, durability_store=ownership_store)

    rec_a = om_a.acquire(_claim())

    del om_a, site_registry_a  # destroy process A

    ownership_store_b = new_sqlite_backed_store(str(tmp_path / "ownership_store"), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)
    site_registry_b = reconstruct_site_registry(ownership_store_b)
    om_b = reconstruct_ownership_manager(ownership_store_b, site_registry_b, fm)

    # A heartbeat/validate against the reconstructed manager must see the SAME generation.
    validated = om_b.validate(rec_a.ownership_key, rec_a.lease_id, rec_a.fencing_generation)
    assert validated.fencing_generation == rec_a.fencing_generation

    # A forged/old generation must still be rejected post-restart.
    with pytest.raises(StaleFencingGenerationError):
        om_b.validate(rec_a.ownership_key, rec_a.lease_id, rec_a.fencing_generation - 1 if rec_a.fencing_generation > 1 else 999)

    # Reconstructed manager mints generation 2 next, never replaying generation 1.
    om_b.release(rec_a.ownership_key, rec_a.lease_id, rec_a.fencing_generation)
    rec_next = om_b.acquire(_claim(worker_id="worker-2"))
    assert rec_next.fencing_generation == rec_a.fencing_generation + 1


def test_restart_does_not_resurrect_an_already_expired_lease(tmp_path):
    ownership_store = new_sqlite_backed_store(str(tmp_path / "ownership_store2"), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)
    site_registry_a = SiteRegistry(durability_store=ownership_store)
    _trusted_site(site_registry_a)
    fm = _fresh_fencing_manager(tmp_path, "fencing_restart2.db")
    om_a = OwnershipManager(site_registry=site_registry_a, fencing_manager=fm, durability_store=ownership_store)

    rec_a = om_a.acquire(_claim(ttl_seconds=0.05))
    time.sleep(0.12)

    del om_a, site_registry_a

    ownership_store_b = new_sqlite_backed_store(str(tmp_path / "ownership_store2"), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)
    site_registry_b = reconstruct_site_registry(ownership_store_b)
    om_b = reconstruct_ownership_manager(ownership_store_b, site_registry_b, fm)

    with pytest.raises(LeaseExpiredError):
        om_b.validate(rec_a.ownership_key, rec_a.lease_id, rec_a.fencing_generation)

    # A different worker can freely acquire a fresh generation post-restart.
    rec_next = om_b.acquire(_claim(worker_id="worker-2"))
    assert rec_next.fencing_generation == rec_a.fencing_generation + 1


def test_reconstruction_never_fabricates_a_dependency(tmp_path):
    """reconstruct_ownership_manager must require explicit site_registry/fencing_manager
    -- it must never silently construct a fresh, empty SiteRegistry/FencingTokenManager
    that would pass every trust/fencing check by simply having no prior state."""
    import inspect
    from akaalEngine.fabric.durability import reconstruct_ownership_manager as fn
    params = inspect.signature(fn).parameters
    assert "site_registry" in params and params["site_registry"].default is inspect._empty
    assert "fencing_manager" in params and params["fencing_manager"].default is inspect._empty


# ----------------------------------------------------------------------
# Corrupted / forged state
# ----------------------------------------------------------------------

def test_load_ownership_record_missing_fields_raises_corrupt_error(tmp_path):
    from akaalEngine.fabric.durability import FabricStateCorruptError, ownership_record_from_payload
    with pytest.raises(FabricStateCorruptError):
        ownership_record_from_payload({"ownership_key": "k"})  # missing every other required field


def test_ownership_manager_never_trusts_a_hand_constructed_record(tmp_path):
    """A hand-built OwnershipRecord (bypassing acquire/renew/transfer) is exactly the
    'forged lease' scenario -- validate() must judge a claimed lease_id/fencing_generation
    purely against the manager's own authoritative in-memory/durable map, never against
    whatever the caller hands it. A forged lease_id that happens to match no real record,
    and a forged generation number invented out of thin air, must both be rejected."""
    from akaalEngine.fabric.ownership.models import OwnershipRecord
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())

    forged = OwnershipRecord(**{**rec.__dict__, "fencing_generation": 999, "lease_id": "own-forged-lease-id"})
    # The forged record's own lease_id/generation, checked against the manager's real
    # record for the same ownership_key, must not validate -- it was never issued by
    # acquire()/transfer().
    with pytest.raises((LeaseConflictError, StaleFencingGenerationError)):
        om.validate(forged.ownership_key, forged.lease_id, forged.fencing_generation)


def test_force_fence_removes_authority_without_requiring_lease_cooperation(tmp_path):
    """The P7B.28 disaster-recovery seam: the old owner's site is dead and cannot present
    its lease_id/generation to cooperate in a graceful release/transfer -- force_fence
    must still remove its authority."""
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    fenced = om.force_fence(rec.ownership_key, reason="site confirmed dead", evidence="coordination_view=UNAVAILABLE_STALE")
    assert fenced.state.value == "FENCED"
    with pytest.raises(LeaseConflictError):
        om.validate(rec.ownership_key, rec.lease_id, rec.fencing_generation)


def test_force_fence_requires_non_empty_reason_and_evidence(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    with pytest.raises(Exception):
        om.force_fence(rec.ownership_key, reason="", evidence="something")
    with pytest.raises(Exception):
        om.force_fence(rec.ownership_key, reason="something", evidence="")


def test_force_fence_on_nonexistent_key_is_a_safe_noop(tmp_path):
    om, _, _ = _manager(tmp_path)
    result = om.force_fence("no-such-key", reason="r", evidence="e")
    assert result is None


def test_force_fenced_ownership_permits_fresh_acquisition(tmp_path):
    om, _, _ = _manager(tmp_path)
    rec = om.acquire(_claim())
    om.force_fence(rec.ownership_key, reason="site dead", evidence="coordination_view=REVOKED")
    rec2 = om.acquire(_claim(worker_id="worker-2"))
    assert rec2.fencing_generation == rec.fencing_generation + 1


def test_wrong_tenant_ownership_key_never_collides_with_another_tenants_same_migration_plan_ids(tmp_path):
    """Two different tenants happening to use the same migration_id/plan_id strings must
    never be treated as the same ownership resource."""
    om, registry, _ = _manager(tmp_path)
    _trusted_site(registry, site_id="site-tb", tenant_id="tenant-b")
    rec_a = om.acquire(_claim(tenant_id="tenant-a"))
    rec_b = om.acquire(_claim(tenant_id="tenant-b", site_id="site-tb"))
    assert rec_a.ownership_key != rec_b.ownership_key
    assert rec_a.fencing_generation == 1
    assert rec_b.fencing_generation == 1  # independent fencing ledgers per ownership_key
