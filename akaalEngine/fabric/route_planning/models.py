"""
akaalEngine.fabric.route_planning.models
===========================================
P7B.10 -- Data Movement Route Planning models.

Absolute authority boundary: ROUTE PLANNING CHOOSES PATH; the existing canonical
TransportAuthority (akaalEngine.transport) MOVES DATA. A `MovementRoute` is a pure,
inert planning artifact -- it has no `execute()`/`run()` method and performs no I/O.
Consuming code hands a MovementRoute's hop sequence to the existing transport/staging
machinery (e.g. akaalEngine.transport.staging.object_storage.ObjectStorageStagingAdapter
for a STAGED route) rather than this module reimplementing data movement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional, Tuple

from akaalEngine.fabric.connectivity.models import ConnectivityEdge, ConnectivityProofState


class RouteShape(str, Enum):
    DIRECT = "DIRECT"
    STAGED = "STAGED"
    RELAY = "RELAY"
    CROSS_CLOUD = "CROSS_CLOUD"
    MULTI_HOP = "MULTI_HOP"


class RoutePlanningError(RuntimeError):
    pass


class NoRouteFoundError(RoutePlanningError):
    pass


class MalformedRouteError(RoutePlanningError):
    pass


@dataclass(frozen=True)
class MovementRoute:
    """
    Immutable, ordered sequence of ConnectivityEdge hops from source_ref to target_ref.
    Carries NO execution behavior -- see module docstring.
    """
    route_id: str
    source_ref: str
    target_ref: str
    shape: RouteShape
    hops: Tuple[ConnectivityEdge, ...]
    staging_ref: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.hops:
            raise MalformedRouteError("MovementRoute must contain at least one hop.")

        # No duplicate hop, no cycle: every node visited along the path must be distinct.
        visited = [self.source_ref]
        cursor = self.source_ref
        for hop in self.hops:
            if hop.source_ref != cursor:
                raise MalformedRouteError(
                    f"MovementRoute hops are not contiguous: expected hop from {cursor!r}, "
                    f"got hop from {hop.source_ref!r} to {hop.destination_ref!r}."
                )
            if hop.destination_ref in visited:
                raise MalformedRouteError(
                    f"MovementRoute contains a cycle/duplicate hop: node {hop.destination_ref!r} "
                    f"is visited more than once."
                )
            visited.append(hop.destination_ref)
            cursor = hop.destination_ref

        if cursor != self.target_ref:
            raise MalformedRouteError(
                f"MovementRoute hops do not terminate at target_ref {self.target_ref!r} "
                f"(terminated at {cursor!r})."
            )

    def is_usable(self) -> bool:
        """A route is usable only if every hop has actually been PROVEN reachable --
        representability (the route object existing) is never itself usability."""
        return all(hop.proof_state == ConnectivityProofState.PROVEN for hop in self.hops)

    def hop_count(self) -> int:
        return len(self.hops)

    def topology_fingerprint(self) -> str:
        """
        Round-3 hostile-review addition (P7B Group-1 §5 -- "TOCTOU between plan / route /
        execution"): a deterministic fingerprint of exactly what this route was planned
        against -- each hop's edge_id AND its proof_state at planning time. A caller that
        wants to detect "topology drifted since I planned this route" (an edge went
        stale/failed, or a completely different edge object now exists under the same
        edge_id) re-derives the current fingerprint from live edge state and compares it
        against this one via `is_stale_against`. This is intentionally a narrow,
        Group-1-scoped freshness check -- NOT a full topology-versioning/graph authority,
        which remains Group 2 scope.
        """
        import hashlib
        parts = [f"{hop.edge_id}:{hop.proof_state.value}" for hop in self.hops]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def is_stale_against(self, current_edges_by_id: "Mapping[str, ConnectivityEdge]") -> bool:
        """
        Returns True if ANY hop this route was planned against either no longer exists
        in `current_edges_by_id` or now has a different proof_state (stale/failed/
        revoked/re-proven) than it did at planning time. Callers executing a route
        should treat a stale result as "replan before executing", never as "execute
        anyway and hope".
        """
        for hop in self.hops:
            current = current_edges_by_id.get(hop.edge_id)
            if current is None or current.proof_state != hop.proof_state:
                return True
        return False
