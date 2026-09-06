"""
akaalEngine.fabric.route_planning.planner
============================================
P7B.10 -- RoutePlanner: finds a usable MovementRoute across a graph of
akaalEngine.fabric.connectivity.ConnectivityEdge objects.

Never treats a broken (PROVEN_FAILED) or stale (PROVEN_STALE) edge as a candidate path
segment -- "only broken route" must surface as NoRouteFoundError, not a route that later
fails. Never crosses a tenant boundary an authorization_callback has not explicitly
approved for that specific edge -- route planning cannot bypass central authorization by
construction: every candidate edge is filtered through the callback before it is ever
considered part of a path.
"""

from __future__ import annotations

import uuid
from collections import deque
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set

from akaalEngine.fabric.connectivity.models import ConnectivityEdge, ConnectivityProofState
from akaalEngine.fabric.route_planning.models import MovementRoute, NoRouteFoundError, RouteShape

RouteAuthorizationCallback = Callable[[ConnectivityEdge, Mapping[str, Any]], bool]

_UNUSABLE_PROOF_STATES = frozenset({ConnectivityProofState.PROVEN_FAILED, ConnectivityProofState.PROVEN_STALE})


class RoutePlanner:
    def plan_route(
        self,
        source_ref: str,
        target_ref: str,
        available_edges: Sequence[ConnectivityEdge],
        *,
        staging_ref: Optional[str] = None,
        authorization_callback: Optional[RouteAuthorizationCallback] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> MovementRoute:
        """
        Finds the shortest hop sequence from source_ref to target_ref via BFS, excluding
        known-broken/stale edges and any edge an authorization_callback rejects. Raises
        NoRouteFoundError -- never silently returns a partial or best-effort route -- when
        no such path exists.
        """
        if source_ref == target_ref:
            raise NoRouteFoundError("source_ref and target_ref must differ.")

        usable_edges = [
            e for e in available_edges
            if e.proof_state not in _UNUSABLE_PROOF_STATES
            and (authorization_callback is None or authorization_callback(e, context or {}))
        ]

        adjacency: Dict[str, List[ConnectivityEdge]] = {}
        for edge in usable_edges:
            adjacency.setdefault(edge.source_ref, []).append(edge)

        path = self._bfs(source_ref, target_ref, adjacency)
        if path is None:
            raise NoRouteFoundError(f"No usable route found from {source_ref!r} to {target_ref!r}.")

        shape = self._classify_shape(path, staging_ref)
        return MovementRoute(
            route_id=f"route-{uuid.uuid4().hex[:16]}",
            source_ref=source_ref,
            target_ref=target_ref,
            shape=shape,
            hops=tuple(path),
            staging_ref=staging_ref,
        )

    @staticmethod
    def _bfs(source_ref: str, target_ref: str, adjacency: Dict[str, List[ConnectivityEdge]]) -> Optional[List[ConnectivityEdge]]:
        visited: Set[str] = {source_ref}
        queue: deque = deque([(source_ref, [])])

        while queue:
            node, path_so_far = queue.popleft()
            if node == target_ref and path_so_far:
                return path_so_far
            for edge in adjacency.get(node, []):
                if edge.destination_ref in visited:
                    continue
                visited.add(edge.destination_ref)
                queue.append((edge.destination_ref, path_so_far + [edge]))

        return None

    @staticmethod
    def _classify_shape(path: List[ConnectivityEdge], staging_ref: Optional[str]) -> RouteShape:
        if staging_ref is not None and any(staging_ref in (e.source_ref, e.destination_ref) for e in path):
            return RouteShape.STAGED
        if len(path) == 1:
            return RouteShape.DIRECT
        if len(path) == 2:
            return RouteShape.RELAY
        return RouteShape.MULTI_HOP


default_route_planner = RoutePlanner()
