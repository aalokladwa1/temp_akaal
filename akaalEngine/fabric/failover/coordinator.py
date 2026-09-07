"""
akaalEngine.fabric.failover.coordinator
==========================================
P7B.28 -- Disaster Recovery & Geo Failover.

`attempt_failover` is the ONE orchestration function implementing the Group-3 failure/
recovery pathway:

    SITE/WORKER/REGION FAILURE
    -> detect and classify failure                (P7B.24 SiteCoordinator, reused)
    -> establish current ownership                 (P7B.25 OwnershipManager, reused)
    -> determine whether existing execution
       still has valid authority                   (checked here -- no new authority)
    -> fence stale owner where required             (P7B.25 OwnershipManager.force_fence)
    -> re-evaluate capability/authorization/
       residency                                    (Group-2 evaluate_candidates, UNMODIFIED)
    -> issue new ownership/lease/fencing identity   (P7B.25 OwnershipManager.acquire)
    -> [resume through canonical AKAAL runtime -- the CALLER's responsibility once this
        function returns SUCCEEDED; this module never touches the runtime, transport,
        checkpoint, or CDC authorities, and never re-evaluates or replays their state]

This module creates NO second migration lifecycle, placement, or ownership authority.
Every decision that already has a canonical home (site liveness, ownership state,
candidate compliance) is READ from or DELEGATED to that home; this module's only own
logic is the ORDER those calls happen in and the fail-safe refusal to act without genuine
evidence.

Never implements "failure -> blindly start another migration": if the responsible site is
still reporting a usable CoordinationView, failover is refused outright (NOT_REQUIRED) --
this is exactly what stops a transient blip / false positive from manufacturing duplicate
ownership. `candidates` (who is even eligible to be considered) is the CALLER's
responsibility to curate, typically via akaalEngine.fabric.regional_operation or
akaalEngine.fabric.multi_cloud (both P7B.26/27, reused, never re-implemented here) --
this module has no opinion on regional/cloud grouping, only on the fence-then-reassign
sequencing.
"""

from __future__ import annotations

from typing import Any, Callable, List, Mapping, Optional, Tuple

from akaalEngine.fabric.execution_site.models import ExecutionSite
from akaalEngine.fabric.failover.models import FailoverOutcome, FailoverResult
from akaalEngine.fabric.locality.models import LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.ownership.manager import OwnershipManager
from akaalEngine.fabric.ownership.models import OwnershipClaim
from akaalEngine.fabric.placement.capability import CapabilityRequirement, CapacityOffer
from akaalEngine.fabric.placement.engine import evaluate_candidates
from akaalEngine.fabric.placement.policy import PlacementAuthorizationCallback
from akaalEngine.fabric.placement.residency import ResidencyPolicy
from akaalEngine.fabric.site_coordination.coordinator import SiteCoordinator
from akaalEngine.fabric.site_coordination.models import CoordinationView

_CONFIRMED_FAILED_VIEWS = (
    CoordinationView.UNAVAILABLE_STALE,
    CoordinationView.PARTITIONED_UNCERTAIN,
    CoordinationView.REVOKED,
)


def attempt_failover(
    *,
    site_coordinator: SiteCoordinator,
    ownership_manager: OwnershipManager,
    old_ownership_key: str,
    candidates: List[ExecutionSite],
    plan_reference: str,
    capability_requirement: CapabilityRequirement,
    authorization_action: str,
    authorization_callback: Optional[PlacementAuthorizationCallback],
    new_claim_factory: Callable[[ExecutionSite], OwnershipClaim],
    residency_policies: Tuple[ResidencyPolicy, ...] = (),
    locality_by_site: Optional[Mapping[str, Mapping[LocalitySubjectRole, LocalityRecord]]] = None,
    capacity_by_site: Optional[Mapping[str, CapacityOffer]] = None,
    tenant_id: Optional[str] = None,
    actor_context: Any = None,
) -> FailoverResult:
    """
    Pure orchestration over already-constructed authorities; performs no I/O of its own
    beyond calling them. Returns a FailoverResult classifying exactly what happened --
    never raises for an ordinary "no failover needed"/"no compliant candidate" outcome
    (those are legitimate results, not errors); genuine misuse (e.g. a malformed
    CapabilityRequirement) still raises through the underlying Group-2 calls unchanged.
    """
    old_record = ownership_manager.try_get(old_ownership_key)

    if old_record is not None and old_record.is_currently_valid_owner():
        try:
            site_snap = site_coordinator.snapshot(old_record.site_id)
            site_view_label = site_snap.view.value
            site_confirmed_failed = site_snap.view in _CONFIRMED_FAILED_VIEWS
        except KeyError:
            # The old owner's site has been deregistered entirely -- treat as confirmed
            # failure evidence (a deregistered site can never again claim AVAILABLE).
            site_view_label = "DEREGISTERED"
            site_confirmed_failed = True

        if not site_confirmed_failed:
            return FailoverResult(
                outcome=FailoverOutcome.NOT_REQUIRED,
                old_ownership_key=old_ownership_key,
                old_record=old_record,
                new_record=None,
                selected_site_id=None,
                placement_result=None,
                reasons=(
                    f"site {old_record.site_id!r} coordination view is {site_view_label!r} "
                    f"and ownership is still active/unexpired; failover refused to avoid "
                    f"manufacturing duplicate work over a transient blip",
                ),
            )

        ownership_manager.force_fence(
            old_ownership_key,
            reason="P7B.28 disaster-recovery failover: responsible site confirmed failed",
            evidence=f"site={old_record.site_id} coordination_view={site_view_label}",
        )

    placement_result = evaluate_candidates(
        plan_reference=plan_reference,
        candidates=candidates,
        capability_requirement=capability_requirement,
        capacity_by_site=capacity_by_site,
        actor_context=actor_context,
        authorization_action=authorization_action,
        authorization_callback=authorization_callback,
        residency_policies=residency_policies,
        locality_by_site=locality_by_site,
        tenant_id=tenant_id,
    )

    if not placement_result.has_compliant_placement():
        return FailoverResult(
            outcome=FailoverOutcome.NO_COMPLIANT_CANDIDATE,
            old_ownership_key=old_ownership_key,
            old_record=old_record,
            new_record=None,
            selected_site_id=None,
            placement_result=placement_result,
            reasons=(
                "zero candidates survived capability/authorization/residency evaluation; "
                "no compliant placement remains -- failing safe rather than weakening "
                "policy to preserve availability",
            ),
        )

    # Deterministic selection of the first accepted candidate in input order -- this is
    # NOT a scoring/optimization decision (that remains Group-2 P7B.16's job, layered
    # above this module by the caller if ranking among multiple compliant candidates is
    # desired); this module only needs ANY one compliant candidate to resume execution.
    chosen_site_id = placement_result.accepted[0].site_id
    chosen_site = next(s for s in candidates if s.site_id == chosen_site_id)
    new_claim = new_claim_factory(chosen_site)
    new_record = ownership_manager.acquire(new_claim)

    return FailoverResult(
        outcome=FailoverOutcome.SUCCEEDED,
        old_ownership_key=old_ownership_key,
        old_record=old_record,
        new_record=new_record,
        selected_site_id=chosen_site_id,
        placement_result=placement_result,
        reasons=(
            f"failed over to site {chosen_site_id!r}; new fencing_generation="
            f"{new_record.fencing_generation}",
        ),
    )
