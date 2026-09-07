"""
akaalEngine.fabric.regional_operation.evaluator
===================================================
P7B.26 -- Multi-Region Operation.

Composes P7B.24 SiteCoordinator's per-site CoordinationView into a per-region rollup, and
curates ExecutionSite candidate lists by region health for handoff to the UNMODIFIED
Group-2 akaalEngine.fabric.placement.engine.evaluate_candidates.

This module makes NO placement, capability, authorization, or residency decision itself
-- it only decides which candidates are even worth OFFERING to evaluate_candidates, based
purely on regional/site liveness (P7B.24). It is explicitly NOT a second placement engine
(P7B Group-3 Section 32 discipline): curate_regional_candidates never accepts or rejects a
candidate for capability/policy/residency reasons, and its output must always be passed
through evaluate_candidates (or an equivalent Group-2 call) before being treated as usable.

ABSOLUTE LAW (restated, and load-bearing precisely because this module could otherwise be
mistaken for a shortcut around it): a region being reachable/healthier/cheaper NEVER
overrides residency. This module curates CANDIDATES ONLY -- evaluate_candidates' own
residency check remains the final, unbypassable word on whether any curated candidate is
actually usable. See
tests/unit/engine_fabric/test_p7b26_multi_region_operation.py::
test_mandatory_india_only_mumbai_down_singapore_rejected for the exact proof required by
the Group-3 directive's sovereignty-under-failure scenario.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from akaalEngine.fabric.execution_site.models import ExecutionSite
from akaalEngine.fabric.regional_operation.models import RegionHealthSnapshot, RegionOperationalState
from akaalEngine.fabric.site_coordination.coordinator import SiteCoordinator
from akaalEngine.fabric.site_coordination.models import CoordinationView

UNKNOWN_REGION_LABEL = "UNKNOWN_REGION"

_USABLE_VIEWS = (CoordinationView.AVAILABLE, CoordinationView.DEGRADED)


def region_of(site: ExecutionSite) -> str:
    """A site with no declared region is bucketed under a truthful UNKNOWN_REGION_LABEL
    -- never silently assigned to whichever region happens to be evaluated first, and
    never treated as belonging to the caller's preferred/expected region by default."""
    return site.region or UNKNOWN_REGION_LABEL


def compute_region_health(sites: List[ExecutionSite], coordinator: SiteCoordinator) -> Dict[str, RegionHealthSnapshot]:
    """
    Pure, read-only rollup. Never mutates SiteRegistry or SiteCoordinator liveness state.
    A region absent from `sites` entirely is simply absent from the returned mapping --
    callers asking about such a region should treat it as RegionOperationalState.UNKNOWN
    (see `get_region_state`), never assume HEALTHY by omission.
    """
    by_region: Dict[str, List[ExecutionSite]] = {}
    for site in sites:
        by_region.setdefault(region_of(site), []).append(site)

    snapshots: Dict[str, RegionHealthSnapshot] = {}
    for region, region_sites in by_region.items():
        available: List[str] = []
        degraded: List[str] = []
        unavailable: List[str] = []
        reasons: List[str] = []

        for site in region_sites:
            snap = coordinator.snapshot(site.site_id)
            reasons.append(f"{site.site_id}: {snap.view.value}")
            if snap.view == CoordinationView.AVAILABLE:
                available.append(site.site_id)
            elif snap.view == CoordinationView.DEGRADED:
                degraded.append(site.site_id)
            else:
                unavailable.append(site.site_id)

        if available:
            state = RegionOperationalState.HEALTHY
        elif degraded:
            state = RegionOperationalState.DEGRADED
        else:
            state = RegionOperationalState.UNAVAILABLE

        snapshots[region] = RegionHealthSnapshot(
            region=region,
            site_ids=tuple(s.site_id for s in region_sites),
            available_site_ids=tuple(available),
            degraded_site_ids=tuple(degraded),
            unavailable_site_ids=tuple(unavailable),
            state=state,
            reasons=tuple(reasons),
        )
    return snapshots


def get_region_state(health: Dict[str, RegionHealthSnapshot], region: str) -> RegionOperationalState:
    snap = health.get(region)
    return snap.state if snap is not None else RegionOperationalState.UNKNOWN


def curate_regional_candidates(
    sites: List[ExecutionSite],
    coordinator: SiteCoordinator,
    *,
    exclude_regions: Tuple[str, ...] = (),
) -> Tuple[List[ExecutionSite], Dict[str, RegionHealthSnapshot]]:
    """
    Returns (candidates, health_snapshots). `candidates` is every site whose region is NOT
    in `exclude_regions` (e.g. a caller-confirmed-failed/preferred-but-down region) AND
    whose own individual CoordinationView is AVAILABLE or DEGRADED -- an individual site
    within an otherwise-healthy region can still be unusable on its own, so exclusion
    happens per-site, not merely per-region.

    The returned `candidates` are exactly the ExecutionSite objects to hand to
    akaalEngine.fabric.placement.engine.evaluate_candidates for the real capability/
    authorization/residency decision; this function makes none of those three decisions
    itself and never returns a "compliant placement" verdict of its own.
    """
    health = compute_region_health(sites, coordinator)
    candidates: List[ExecutionSite] = []
    for site in sites:
        if region_of(site) in exclude_regions:
            continue
        snap = coordinator.snapshot(site.site_id)
        if snap.view in _USABLE_VIEWS:
            candidates.append(site)
    return candidates, health
