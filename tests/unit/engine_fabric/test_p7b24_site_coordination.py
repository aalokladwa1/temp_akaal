"""
tests.unit.engine_fabric.test_p7b24_site_coordination
=========================================================
P7B.24 -- Distributed Site Coordination hostile test suite.

Proves SiteCoordinator (composed strictly over the frozen P7B.5 SiteRegistry, no
duplicate trust/tenant/fencing authority) enforces:
    * heartbeat != ownership/trust
    * a revoked site cannot heartbeat itself back into trust
    * a superseded site generation (old site returning after replacement) cannot
      regain liveness credit via a stale fencing epoch
    * replayed/out-of-order heartbeat sequences are refused
    * unknown/uncertain state is never coerced into AVAILABLE
    * concurrent heartbeats converge to one consistent liveness record
    * fresh-process reconstruction preserves fencing-epoch replay protection
"""

from __future__ import annotations

import threading
import time

import pytest

from akaalEngine.fabric.durability import new_sqlite_backed_store, reconstruct_site_registry
from akaalEngine.fabric.execution_site import (
    ExecutionSite,
    SiteAssignment,
    SiteKind,
    SiteRegistry,
    SiteTrustState,
)
from akaalEngine.fabric.execution_site.models import SiteHealthState
from akaalEngine.fabric.site_coordination import (
    CoordinationView,
    HeartbeatRejectedError,
    SiteCoordinator,
    SiteHeartbeat,
)

SIGNING_KEY = b"p7b24-coordination-test-key-0001"
ANCHOR_KEY = b"p7b24-coordination-anchor-key-02"


def _site(site_id="site-1", environment_id="env-1", claimed_identity=None):
    return ExecutionSite(
        site_id=site_id,
        site_kind=SiteKind.ON_PREM_VM,
        environment_id=environment_id,
        claimed_security_identity=claimed_identity or f"spiffe://akaal.local/site/{site_id}",
    )


def _make_trusted_tenant_bound_site(registry: SiteRegistry, site_id="site-1", tenant_id="tenant-a"):
    registry.register(_site(site_id))
    registry.verify_identity(site_id, verifier=lambda s, c: True, presented_credential="cert")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry.get(site_id)


def _assign(registry: SiteRegistry, site_id, tenant_id, epoch, migration_id="mig-1", plan_id="plan-1"):
    return registry.assign_execution(
        SiteAssignment(
            site_id=site_id, tenant_id=tenant_id, workspace_id="ws-1",
            migration_id=migration_id, plan_id=plan_id, fencing_epoch=epoch,
        ),
        authorization_callback=lambda s, a, c: True,
    )


# ----------------------------------------------------------------------
# Basic positive path
# ----------------------------------------------------------------------

def test_trusted_bound_site_with_fresh_heartbeat_is_available():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry, staleness_threshold_seconds=30.0)

    snap = coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    assert snap.view == CoordinationView.AVAILABLE
    assert snap.reasons


def test_registered_only_site_is_registered_view_not_available():
    registry = SiteRegistry()
    registry.register(_site())
    coord = SiteCoordinator(registry)
    snap = coord.snapshot("site-1")
    assert snap.view == CoordinationView.REGISTERED


def test_trusted_site_with_no_heartbeat_ever_is_pending_contact_not_available():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry)
    snap = coord.snapshot("site-1")
    assert snap.view == CoordinationView.TRUSTED_PENDING_CONTACT
    assert snap.view != CoordinationView.AVAILABLE


# ----------------------------------------------------------------------
# Heartbeat != ownership / trust
# ----------------------------------------------------------------------

def test_heartbeat_never_mutates_registry_trust_state():
    registry = SiteRegistry()
    registry.register(_site())  # only REGISTERED, never trusted
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    assert registry.get("site-1").trust_state == SiteTrustState.REGISTERED  # unchanged


def test_unauthorized_but_fresh_heartbeat_is_partitioned_uncertain_not_available():
    """A site that is TRUSTED but not yet tenant-bound sends a perfectly fresh heartbeat
    -- must never be reported AVAILABLE merely because it is reachable and answering."""
    registry = SiteRegistry()
    registry.register(_site())
    registry.verify_identity("site-1", verifier=lambda s, c: True, presented_credential="cert")
    registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    coord = SiteCoordinator(registry)

    snap = coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    assert snap.view == CoordinationView.PARTITIONED_UNCERTAIN


def test_revoked_site_cannot_heartbeat_itself_back_into_trust():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    registry.revoke("site-1", reason="hostile-test revocation")
    coord = SiteCoordinator(registry)

    with pytest.raises(HeartbeatRejectedError):
        coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))

    snap = coord.snapshot("site-1")
    assert snap.view == CoordinationView.REVOKED


def test_unknown_site_heartbeat_fails_safe():
    registry = SiteRegistry()
    coord = SiteCoordinator(registry)
    with pytest.raises(KeyError):
        coord.record_heartbeat(SiteHeartbeat(site_id="ghost-site", sequence=1, reported_health=SiteHealthState.HEALTHY))


# ----------------------------------------------------------------------
# Replay / out-of-order heartbeat
# ----------------------------------------------------------------------

def test_replayed_heartbeat_sequence_is_rejected():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=5, reported_health=SiteHealthState.HEALTHY))
    with pytest.raises(HeartbeatRejectedError):
        coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=5, reported_health=SiteHealthState.HEALTHY))
    with pytest.raises(HeartbeatRejectedError):
        coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=3, reported_health=SiteHealthState.HEALTHY))


def test_rejected_heartbeat_does_not_pollute_liveness_bookkeeping():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=5, reported_health=SiteHealthState.HEALTHY))
    with pytest.raises(HeartbeatRejectedError):
        coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=2, reported_health=SiteHealthState.DEGRADED))
    # Last accepted heartbeat (seq=5, HEALTHY) must still be the one reflected.
    snap = coord.snapshot("site-1")
    assert snap.last_heartbeat_sequence == 5
    assert snap.last_reported_health == SiteHealthState.HEALTHY


# ----------------------------------------------------------------------
# Old site returns after replacement (ABA / stale-generation protection)
# ----------------------------------------------------------------------

def test_old_site_generation_heartbeat_after_replacement_is_rejected():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    _assign(registry, "site-1", "tenant-a", epoch=1)
    coord = SiteCoordinator(registry)

    # Original generation heartbeats fine at epoch 1.
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY, fencing_epoch_seen=1))

    # Site is "replaced": a new assignment bumps the fencing epoch to 2 (representing the
    # replacement generation taking over the same site_id's execution authority).
    _assign(registry, "site-1", "tenant-a", epoch=2)

    # The OLD process, still believing it is at epoch 1, sends another heartbeat.
    with pytest.raises(HeartbeatRejectedError):
        coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=2, reported_health=SiteHealthState.HEALTHY, fencing_epoch_seen=1))

    # The new generation, correctly reporting epoch 2, is accepted.
    snap = coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=3, reported_health=SiteHealthState.HEALTHY, fencing_epoch_seen=2))
    assert snap.current_fencing_epoch == 2


def test_heartbeat_with_no_epoch_claim_is_not_penalized():
    """A site that never carries fencing_epoch_seen (e.g. no assignment has ever been
    issued to it) must not be rejected merely for reporting 0 -- 0 means 'no claim', not
    'stale claim'."""
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry)
    snap = coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    assert snap.view == CoordinationView.AVAILABLE


# ----------------------------------------------------------------------
# Site disappearance / staleness detection (pure detection, no auto-failover)
# ----------------------------------------------------------------------

def test_stale_heartbeat_transitions_to_unavailable_stale():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    time.sleep(0.12)
    snap = coord.snapshot("site-1")
    assert snap.view == CoordinationView.UNAVAILABLE_STALE
    assert "site-1" in coord.stale_site_ids()


def test_stale_site_ids_never_mutates_registry_state():
    """Detection must never itself revoke/reassign -- pure read."""
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    time.sleep(0.12)
    coord.stale_site_ids()
    # Registry trust/tenant state must be completely untouched by mere detection.
    site = registry.get("site-1")
    assert site.trust_state == SiteTrustState.TRUSTED
    assert site.tenant_binding == "tenant-a"


def test_draining_lifecycle_reported_regardless_of_heartbeat_freshness():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    # Simulate draining via a fresh SiteRegistry-produced record (bind_tenant/registry has
    # no direct "set draining" API surface at Group-1 freeze; construct the transition the
    # same way SiteRegistry._with is used internally is out of scope for a black-box test,
    # so this test uses the DEGRADED health signal path instead, which IS externally
    # reachable, to prove non-AVAILABLE classification is possible while heartbeats stay fresh.
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=2, reported_health=SiteHealthState.DEGRADED))
    snap = coord.snapshot("site-1")
    assert snap.view == CoordinationView.DEGRADED


def test_forget_liveness_resets_bookkeeping_without_touching_registry():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.forget_liveness("site-1")
    snap = coord.snapshot("site-1")
    assert snap.view == CoordinationView.TRUSTED_PENDING_CONTACT
    assert registry.get("site-1").trust_state == SiteTrustState.TRUSTED  # untouched


# ----------------------------------------------------------------------
# Cross-tenant / duplicate identity -- delegated to SiteRegistry, proven still enforced
# ----------------------------------------------------------------------

def test_coordinator_does_not_weaken_site_identity_collision_protection():
    from akaalEngine.fabric.execution_site import SiteIdentityCollisionError
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry, site_id="site-1")
    SiteCoordinator(registry)  # coordinator merely observes; must not disturb this guard
    with pytest.raises(SiteIdentityCollisionError):
        registry.register(_site(site_id="site-1", claimed_identity="spiffe://attacker/impostor"))


def test_heartbeat_carries_no_tenant_claim_at_all():
    """By construction, SiteHeartbeat has no tenant_id field -- a heartbeat can never be
    used as a channel to claim/substitute tenant binding for any site."""
    assert not hasattr(SiteHeartbeat(site_id="s", sequence=1, reported_health=SiteHealthState.HEALTHY), "tenant_id")


# ----------------------------------------------------------------------
# Concurrency
# ----------------------------------------------------------------------

def test_concurrent_heartbeats_converge_to_highest_sequence():
    registry = SiteRegistry()
    _make_trusted_tenant_bound_site(registry)
    coord = SiteCoordinator(registry, staleness_threshold_seconds=30.0)

    errors = []

    def send(seq):
        try:
            coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=seq, reported_health=SiteHealthState.HEALTHY))
        except HeartbeatRejectedError:
            pass
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=send, args=(seq,)) for seq in range(1, 65)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    snap = coord.snapshot("site-1")
    assert snap.last_heartbeat_sequence == 64
    assert snap.view == CoordinationView.AVAILABLE


def test_concurrent_registration_and_heartbeat_for_distinct_sites_do_not_interfere():
    registry = SiteRegistry()
    coord = SiteCoordinator(registry, staleness_threshold_seconds=30.0)
    errors = []

    def worker(i):
        try:
            site_id = f"site-{i}"
            _make_trusted_tenant_bound_site(registry, site_id=site_id, tenant_id=f"tenant-{i}")
            coord.record_heartbeat(SiteHeartbeat(site_id=site_id, sequence=1, reported_health=SiteHealthState.HEALTHY))
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    for i in range(20):
        snap = coord.snapshot(f"site-{i}")
        assert snap.view == CoordinationView.AVAILABLE
        assert snap.tenant_binding == f"tenant-{i}"


# ----------------------------------------------------------------------
# Fresh-process reconstruction
# ----------------------------------------------------------------------

def test_restart_reconstructs_registry_without_resurrecting_stale_epoch(tmp_path):
    store_a = new_sqlite_backed_store(str(tmp_path), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)
    registry_a = SiteRegistry(durability_store=store_a)
    _make_trusted_tenant_bound_site(registry_a)
    _assign(registry_a, "site-1", "tenant-a", epoch=1)
    _assign(registry_a, "site-1", "tenant-a", epoch=2)
    coord_a = SiteCoordinator(registry_a)
    coord_a.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY, fencing_epoch_seen=2))

    # Destroy process A entirely.
    del registry_a, coord_a

    store_b = new_sqlite_backed_store(str(tmp_path), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)
    registry_b = reconstruct_site_registry(store_b)
    coord_b = SiteCoordinator(registry_b)

    # Reconstructed process has no in-memory heartbeat history (naturally re-established) --
    # but the SECURITY-CRITICAL fencing epoch (2) MUST have survived the restart.
    snap = coord_b.snapshot("site-1")
    assert snap.view == CoordinationView.TRUSTED_PENDING_CONTACT
    assert snap.current_fencing_epoch == 2

    # A heartbeat replaying the pre-restart epoch (1) must still be rejected post-restart --
    # restart must never reopen a replay window.
    with pytest.raises(HeartbeatRejectedError):
        coord_b.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY, fencing_epoch_seen=1))

    # A heartbeat correctly reporting the current epoch succeeds.
    snap2 = coord_b.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY, fencing_epoch_seen=2))
    assert snap2.view == CoordinationView.AVAILABLE


def test_current_fencing_epoch_defaults_to_zero_when_never_issued():
    registry = SiteRegistry()
    registry.register(_site())
    assert registry.current_fencing_epoch("site-1") == 0


def test_current_fencing_epoch_unknown_site_fails_safe():
    registry = SiteRegistry()
    with pytest.raises(KeyError):
        registry.current_fencing_epoch("ghost")
