"""
akaalEngine.fabric.multi_cloud.evaluator
============================================
P7B.27 -- Multi-Cloud Operation.

Mirrors akaalEngine.fabric.regional_operation.evaluator's composition discipline exactly,
but groups/curates ExecutionSite candidates by CLOUD IDENTITY (derived from each site's
Environment -- P7B.1, unmodified) instead of by `ExecutionSite.region`. This is
deliberate: two different clouds can and do reuse the same region-label vocabulary (e.g.
neither AWS's "us-east-1" nor Azure's "eastus" happen to collide here, but this module
never relies on that -- cloud identity is always resolved via the canonical Environment/
boundary, never via string comparison of region labels).

This module makes NO placement, capability, authorization, or residency decision --
identical discipline to regional_operation.evaluator: it curates CANDIDATES ONLY, and its
output must always be passed through the UNMODIFIED Group-2
akaalEngine.fabric.placement.engine.evaluate_candidates before being treated as usable.
Cross-cloud identity substitution is structurally impossible here because
`cloud_identity_of` never accepts a caller-supplied cloud label -- it is always resolved
by looking up the site's `environment_id` in the canonical EnvironmentRegistry and reading
that Environment's own `environment_type`/`boundary.native_key()`.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from akaalEngine.fabric.environment.models import Environment
from akaalEngine.fabric.environment.registry import EnvironmentRegistry
from akaalEngine.fabric.execution_site.models import ExecutionSite
from akaalEngine.fabric.multi_cloud.models import CloudHealthSnapshot, CloudIdentity, CloudOperationalState
from akaalEngine.fabric.site_coordination.coordinator import SiteCoordinator
from akaalEngine.fabric.site_coordination.models import CoordinationView

_USABLE_VIEWS = (CoordinationView.AVAILABLE, CoordinationView.DEGRADED)


def cloud_identity_of(site: ExecutionSite, environment_registry: EnvironmentRegistry) -> CloudIdentity:
    """
    Resolves cloud identity STRICTLY from the site's own registered Environment --
    UnknownEnvironmentError propagates unchanged (fail safe) if the site's
    `environment_id` does not resolve, rather than falling back to any default cloud.
    """
    env: Environment = environment_registry.get(site.environment_id)
    boundary_key: Tuple[str, ...] = env.boundary.native_key() if env.boundary is not None else ()
    return CloudIdentity(environment_type=env.environment_type.value, native_boundary_key=boundary_key)


def compute_cloud_health(
    sites: List[ExecutionSite],
    coordinator: SiteCoordinator,
    environment_registry: EnvironmentRegistry,
) -> Dict[Tuple[str, Tuple[str, ...]], CloudHealthSnapshot]:
    by_cloud: Dict[Tuple[str, Tuple[str, ...]], Tuple[CloudIdentity, List[ExecutionSite]]] = {}
    for site in sites:
        identity = cloud_identity_of(site, environment_registry)
        key = identity.as_key()
        if key not in by_cloud:
            by_cloud[key] = (identity, [])
        by_cloud[key][1].append(site)

    snapshots: Dict[Tuple[str, Tuple[str, ...]], CloudHealthSnapshot] = {}
    for key, (identity, cloud_sites) in by_cloud.items():
        available: List[str] = []
        degraded: List[str] = []
        unavailable: List[str] = []
        reasons: List[str] = []
        for site in cloud_sites:
            snap = coordinator.snapshot(site.site_id)
            reasons.append(f"{site.site_id}: {snap.view.value}")
            if snap.view == CoordinationView.AVAILABLE:
                available.append(site.site_id)
            elif snap.view == CoordinationView.DEGRADED:
                degraded.append(site.site_id)
            else:
                unavailable.append(site.site_id)

        if available:
            state = CloudOperationalState.HEALTHY
        elif degraded:
            state = CloudOperationalState.DEGRADED
        else:
            state = CloudOperationalState.UNAVAILABLE

        snapshots[key] = CloudHealthSnapshot(
            cloud_identity=identity,
            site_ids=tuple(s.site_id for s in cloud_sites),
            available_site_ids=tuple(available),
            degraded_site_ids=tuple(degraded),
            unavailable_site_ids=tuple(unavailable),
            state=state,
            reasons=tuple(reasons),
        )
    return snapshots


def curate_cross_cloud_candidates(
    sites: List[ExecutionSite],
    coordinator: SiteCoordinator,
    environment_registry: EnvironmentRegistry,
    *,
    exclude_cloud_identities: Tuple[CloudIdentity, ...] = (),
) -> Tuple[List[ExecutionSite], Dict[Tuple[str, Tuple[str, ...]], CloudHealthSnapshot]]:
    """
    Returns (candidates, health_snapshots), exactly mirroring
    regional_operation.evaluator.curate_regional_candidates's contract, but excluding by
    resolved CloudIdentity instead of region label. `exclude_cloud_identities` lets a
    caller explicitly rule out a confirmed-failed cloud account/subscription/project/
    tenancy (e.g. after a provider-wide outage) without needing every one of its sites to
    have individually gone stale yet.
    """
    health = compute_cloud_health(sites, coordinator, environment_registry)
    exclude_keys = {ci.as_key() for ci in exclude_cloud_identities}
    candidates: List[ExecutionSite] = []
    for site in sites:
        identity = cloud_identity_of(site, environment_registry)
        if identity.as_key() in exclude_keys:
            continue
        snap = coordinator.snapshot(site.site_id)
        if snap.view in _USABLE_VIEWS:
            candidates.append(site)
    return candidates, health
