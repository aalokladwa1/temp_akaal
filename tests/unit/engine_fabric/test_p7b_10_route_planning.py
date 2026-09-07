"""
tests.unit.engine_fabric.test_p7b_10_route_planning
=======================================================
P7B.10 hostile tests -- data movement route planning.

Proves: no route; only broken route; unreachable source/target; malformed multi-hop
(cycle/duplicate hop) rejected; stale route excluded; route cannot bypass authorization
(cross-tenant edge filtered); staging participation classifies STAGED shape; direct vs
relay vs multi-hop classification; MovementRoute has no execute() (route planning !=
transport authority); representability != usability.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.connectivity import (
    ConnectivityClass,
    ConnectivityEdge,
    ConnectivityProofState,
    PrivacyAchieved,
    ReachabilityEvidence,
)
from akaalEngine.fabric.route_planning import (
    MalformedRouteError,
    NoRouteFoundError,
    RoutePlanner,
    RouteShape,
)


def _edge(source, dest, proof_state=ConnectivityProofState.CONFIGURED, **kw) -> ConnectivityEdge:
    e = ConnectivityEdge(
        edge_id=f"edge-{source}-{dest}",
        source_ref=source,
        destination_ref=dest,
        connectivity_class=ConnectivityClass.DIRECT_PRIVATE,
        is_private=True,
        **kw,
    )
    if proof_state == ConnectivityProofState.PROVEN:
        return e.elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id=e.edge_id, achieved_privacy=PrivacyAchieved.PRIVATE))
    if proof_state == ConnectivityProofState.PROVEN_FAILED:
        return e.elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id=e.edge_id))
    if proof_state == ConnectivityProofState.PROVEN_STALE:
        return e.elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id=e.edge_id, achieved_privacy=PrivacyAchieved.PRIVATE)).mark_stale()
    return e


def test_no_route_when_no_edges_exist():
    planner = RoutePlanner()
    with pytest.raises(NoRouteFoundError):
        planner.plan_route("src", "dst", [])


def test_direct_route_via_single_hop():
    planner = RoutePlanner()
    edges = [_edge("src", "dst")]
    route = planner.plan_route("src", "dst", edges)
    assert route.shape == RouteShape.DIRECT
    assert route.hop_count() == 1


def test_relay_route_via_execution_site_hop():
    planner = RoutePlanner()
    edges = [_edge("src", "site-1"), _edge("site-1", "dst")]
    route = planner.plan_route("src", "dst", edges)
    assert route.shape == RouteShape.RELAY
    assert route.hop_count() == 2


def test_multi_hop_route_classified_distinctly_from_relay():
    planner = RoutePlanner()
    edges = [_edge("src", "a"), _edge("a", "b"), _edge("b", "dst")]
    route = planner.plan_route("src", "dst", edges)
    assert route.shape == RouteShape.MULTI_HOP
    assert route.hop_count() == 3


def test_only_broken_route_yields_no_route_found():
    planner = RoutePlanner()
    edges = [_edge("src", "dst", proof_state=ConnectivityProofState.PROVEN_FAILED)]
    with pytest.raises(NoRouteFoundError):
        planner.plan_route("src", "dst", edges)


def test_stale_route_excluded_from_planning():
    planner = RoutePlanner()
    edges = [_edge("src", "dst", proof_state=ConnectivityProofState.PROVEN_STALE)]
    with pytest.raises(NoRouteFoundError):
        planner.plan_route("src", "dst", edges)


def test_unreachable_target_no_edges_touch_it():
    planner = RoutePlanner()
    edges = [_edge("src", "a"), _edge("a", "b")]  # never reaches "dst"
    with pytest.raises(NoRouteFoundError):
        planner.plan_route("src", "dst", edges)


def test_broken_edge_bypassed_in_favor_of_working_alternate_path():
    planner = RoutePlanner()
    edges = [
        _edge("src", "dst", proof_state=ConnectivityProofState.PROVEN_FAILED),  # broken direct
        _edge("src", "site-1"),
        _edge("site-1", "dst"),
    ]
    route = planner.plan_route("src", "dst", edges)
    assert route.shape == RouteShape.RELAY  # took the working alternate, not the broken direct


def test_staged_route_classified_when_path_touches_staging_ref():
    planner = RoutePlanner()
    edges = [_edge("src", "site-1"), _edge("site-1", "staging-bucket"), _edge("staging-bucket", "site-2"), _edge("site-2", "dst")]
    route = planner.plan_route("src", "dst", edges, staging_ref="staging-bucket")
    assert route.shape == RouteShape.STAGED


def test_route_cannot_cross_tenant_boundary_authorization_filters_edge():
    """Route planning cannot bypass central authorization: an edge rejected by the
    authorization_callback is excluded from the candidate graph entirely, even if it is
    the only path."""
    planner = RoutePlanner()
    edges = [_edge("src", "dst")]

    def deny_all(edge, context):
        return False

    with pytest.raises(NoRouteFoundError):
        planner.plan_route("src", "dst", edges, authorization_callback=deny_all)


def test_route_authorization_allows_permitted_edges_only():
    planner = RoutePlanner()
    forbidden = _edge("src", "dst")  # direct, forbidden (e.g. crosses tenant)
    allowed_1 = _edge("src", "site-1")
    allowed_2 = _edge("site-1", "dst")

    def allow_only_via_site(edge, context):
        return edge.edge_id != forbidden.edge_id

    route = planner.plan_route("src", "dst", [forbidden, allowed_1, allowed_2], authorization_callback=allow_only_via_site)
    assert route.shape == RouteShape.RELAY


def test_same_source_and_target_rejected():
    planner = RoutePlanner()
    with pytest.raises(NoRouteFoundError):
        planner.plan_route("same", "same", [_edge("same", "other")])


def test_malformed_route_construction_rejects_cycle():
    e1 = _edge("a", "b")
    e2 = _edge("b", "a")  # cycle back to source
    from akaalEngine.fabric.route_planning.models import MovementRoute
    with pytest.raises(MalformedRouteError):
        MovementRoute(route_id="r1", source_ref="a", target_ref="a", shape=RouteShape.MULTI_HOP, hops=(e1, e2))


def test_malformed_route_construction_rejects_noncontiguous_hops():
    e1 = _edge("a", "b")
    e2 = _edge("x", "c")  # does not continue from "b"
    from akaalEngine.fabric.route_planning.models import MovementRoute
    with pytest.raises(MalformedRouteError):
        MovementRoute(route_id="r1", source_ref="a", target_ref="c", shape=RouteShape.MULTI_HOP, hops=(e1, e2))


def test_movement_route_has_no_execute_method_route_planning_is_not_transport():
    planner = RoutePlanner()
    route = planner.plan_route("src", "dst", [_edge("src", "dst")])
    assert not hasattr(route, "execute")
    assert not hasattr(route, "run")
    assert not hasattr(route, "transfer")


def test_route_object_existing_is_not_itself_usability():
    """Representability != usability: a CONFIGURED-only route must report is_usable()
    False until every hop is actually PROVEN."""
    planner = RoutePlanner()
    route = planner.plan_route("src", "dst", [_edge("src", "dst", proof_state=ConnectivityProofState.CONFIGURED)])
    assert route.is_usable() is False

    proven_route = planner.plan_route("src", "dst", [_edge("src", "dst", proof_state=ConnectivityProofState.PROVEN)])
    assert proven_route.is_usable() is True
