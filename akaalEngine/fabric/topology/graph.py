"""
akaalEngine.fabric.topology.graph
====================================
P7B.11 -- Canonical Topology Graph: registration seam + immutable queryable snapshot.

CRITICAL LAW (restated, load-bearing here): registering topology facts is bookkeeping,
never authorization. `TopologyRegistry` prevents identity collisions and cross-tenant
leakage; it never grants execution permission, trust, or reachability-as-permission.
`akaalPipeline.security.central_authorization` remains the sole authorization authority.

Tenant scoping is structural, not optional: `TopologyGraph.snapshot()` always requires an
explicit `tenant_id` and only ever includes that tenant's nodes/edges -- there is no
"give me the whole graph across all tenants" query anywhere in this module, closing the
cross-tenant topology substitution/enumeration attack class named in the Group-2 hostile
matrix.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from akaalEngine.fabric.topology.models import (
    TopologyEdge,
    TopologyNode,
    TopologyRelationshipKind,
    TopologyValidationError,
    snapshot_fingerprint,
)


class TopologyRegistrationError(TopologyValidationError):
    pass


class DuplicateTopologyNodeIdentityError(TopologyRegistrationError):
    pass


class DuplicateTopologyEdgeIdentityError(TopologyRegistrationError):
    pass


class CrossTenantTopologyError(TopologyRegistrationError):
    """Raised whenever an operation would let one tenant's topology fact reference,
    overwrite, or become visible to a different tenant. Fails closed, always."""


class UnknownTopologyNodeError(KeyError):
    pass


class UnknownTopologyEdgeError(KeyError):
    pass


class TopologyGraph:
    """
    Immutable, queryable snapshot of one tenant's topology facts at a point in time.
    Never mutated in place -- TopologyRegistry.snapshot() always returns a fresh instance
    reflecting current registry state. Traversal here answers "does a path of topology
    facts exist" -- it is explicitly NOT a reachability, permission, or placement
    decision; callers must never treat `has_path` as proof of network reachability
    (that remains akaalEngine.fabric.reachability's job) or as an authorization outcome.
    """

    def __init__(self, tenant_id: str, nodes: Tuple[TopologyNode, ...], edges: Tuple[TopologyEdge, ...]) -> None:
        self.tenant_id = tenant_id
        self._nodes: Dict[str, TopologyNode] = {n.node_id: n for n in nodes}
        self._edges: Dict[str, TopologyEdge] = {e.topology_edge_id: e for e in edges}
        self._adjacency: Dict[str, List[TopologyEdge]] = {}
        for edge in edges:
            self._adjacency.setdefault(edge.source_node_id, []).append(edge)
        self._fingerprint = snapshot_fingerprint(tuple(nodes), tuple(edges))

    def fingerprint(self) -> str:
        return self._fingerprint

    def node(self, node_id: str) -> TopologyNode:
        node = self._nodes.get(node_id)
        if node is None:
            raise UnknownTopologyNodeError(f"Unknown node_id in this tenant's topology snapshot: {node_id!r}")
        return node

    def try_node(self, node_id: str) -> Optional[TopologyNode]:
        return self._nodes.get(node_id)

    def edge(self, topology_edge_id: str) -> TopologyEdge:
        edge = self._edges.get(topology_edge_id)
        if edge is None:
            raise UnknownTopologyEdgeError(f"Unknown topology_edge_id in this tenant's topology snapshot: {topology_edge_id!r}")
        return edge

    def nodes(self) -> Tuple[TopologyNode, ...]:
        return tuple(self._nodes.values())

    def edges(self) -> Tuple[TopologyEdge, ...]:
        return tuple(self._edges.values())

    def neighbors(
        self,
        node_id: str,
        relationship_kind: Optional[TopologyRelationshipKind] = None,
        *,
        include_stale: bool = False,
    ) -> Tuple[str, ...]:
        out = []
        for edge in self._adjacency.get(node_id, ()):
            if not include_stale and edge.stale:
                continue
            if relationship_kind is not None and edge.relationship_kind != relationship_kind:
                continue
            out.append(edge.target_node_id)
        return tuple(out)

    def has_path(self, source_node_id: str, target_node_id: str, *, include_stale: bool = False) -> bool:
        """BFS reachability WITHIN THE TOPOLOGY GRAPH ONLY. This is a graph-traversal
        fact, never a network-reachability or authorization fact -- see module docstring."""
        if source_node_id not in self._nodes or target_node_id not in self._nodes:
            return False
        if source_node_id == target_node_id:
            return True
        visited: Set[str] = {source_node_id}
        queue = deque([source_node_id])
        while queue:
            current = queue.popleft()
            for edge in self._adjacency.get(current, ()):
                if not include_stale and edge.stale:
                    continue
                nxt = edge.target_node_id
                if nxt == target_node_id:
                    return True
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return False

    def is_stale_against(self, current_graph: "TopologyGraph") -> bool:
        """True if this snapshot's fingerprint no longer matches a freshly taken snapshot
        of the same tenant's current registry state. Mirrors
        MovementRoute.is_stale_against() (P7B.10) at the whole-graph level."""
        return self.fingerprint() != current_graph.fingerprint()


class TopologyRegistry:
    """Thread-safe, tenant-scoped Topology registration/query authority. Optionally
    durability-backed (see akaalEngine.fabric.durability) for cross-restart
    reconstruction of authoritative topology facts."""

    def __init__(self, durability_store: Optional[Any] = None) -> None:
        self._lock = threading.RLock()
        self._nodes_by_id: Dict[str, TopologyNode] = {}
        self._nodes_by_native_key: Dict[tuple, str] = {}
        self._edges_by_id: Dict[str, TopologyEdge] = {}
        self._durability_store = durability_store

    # ---------------------------------------------------------------- nodes

    def register_node(self, node: TopologyNode) -> TopologyNode:
        with self._lock:
            native_key = node.native_key()

            existing_by_id = self._nodes_by_id.get(node.node_id)
            if existing_by_id is not None:
                if existing_by_id.tenant_id != node.tenant_id:
                    raise CrossTenantTopologyError(
                        f"node_id {node.node_id!r} is already registered to a different "
                        f"tenant; refusing cross-tenant node substitution."
                    )
                if existing_by_id.native_key() != native_key:
                    raise DuplicateTopologyNodeIdentityError(
                        f"node_id {node.node_id!r} is already registered against a different "
                        f"physical reference {existing_by_id.native_key()!r}; refusing to "
                        f"silently repoint an existing locator at {native_key!r}."
                    )

            existing_id_for_native = self._nodes_by_native_key.get(native_key)
            if existing_id_for_native is not None and existing_id_for_native != node.node_id:
                raise DuplicateTopologyNodeIdentityError(
                    f"Physical reference {native_key!r} is already registered under "
                    f"node_id {existing_id_for_native!r}; cannot register a second, distinct "
                    f"node_id {node.node_id!r} for the same physical reference."
                )

            self._nodes_by_id[node.node_id] = node
            self._nodes_by_native_key[native_key] = node.node_id
            if self._durability_store is not None:
                self._durability_store.save_topology_node(node)
            return node

    def _register_reconstructed_node(self, node: TopologyNode) -> None:
        """INTERNAL ONLY -- fresh-process rehydration from durable state. Bypasses no
        security check that matters at reconstruction time (there is no self-elevation
        risk for topology facts -- they carry no trust/authorization state), but is kept
        as a distinct internal method to match the established fabric registry pattern
        and to make future security-relevant fields easy to gate here if ever added."""
        with self._lock:
            self._nodes_by_id[node.node_id] = node
            self._nodes_by_native_key[node.native_key()] = node.node_id

    def update_node(self, node_id: str, tenant_id: str, **changes: Any) -> TopologyNode:
        """Applies changes to an existing node, always bumping `generation` by 1 so
        fingerprint-based staleness detection observes the change. Cross-tenant update is
        refused outright."""
        with self._lock:
            existing = self._nodes_by_id.get(node_id)
            if existing is None:
                raise UnknownTopologyNodeError(f"Unknown node_id: {node_id!r}")
            if existing.tenant_id != tenant_id:
                raise CrossTenantTopologyError(
                    f"node_id {node_id!r} belongs to a different tenant; refusing cross-tenant update."
                )
            payload = existing.__dict__.copy()
            payload.update(changes)
            payload["generation"] = existing.generation + 1
            updated = TopologyNode(**payload)
            self._nodes_by_id[node_id] = updated
            if self._durability_store is not None:
                self._durability_store.save_topology_node(updated)
            return updated

    def mark_node_stale(self, node_id: str, tenant_id: str) -> TopologyNode:
        return self.update_node(node_id, tenant_id, stale=True)

    def get_node(self, node_id: str, tenant_id: str) -> TopologyNode:
        with self._lock:
            node = self._nodes_by_id.get(node_id)
            if node is None:
                raise UnknownTopologyNodeError(f"Unknown node_id: {node_id!r}")
            if node.tenant_id != tenant_id:
                raise CrossTenantTopologyError(
                    f"node_id {node_id!r} belongs to a different tenant; refusing cross-tenant read."
                )
            return node

    # ---------------------------------------------------------------- edges

    def register_edge(self, edge: TopologyEdge) -> TopologyEdge:
        with self._lock:
            existing = self._edges_by_id.get(edge.topology_edge_id)
            if existing is not None:
                if existing.tenant_id != edge.tenant_id:
                    raise CrossTenantTopologyError(
                        f"topology_edge_id {edge.topology_edge_id!r} is already registered to a "
                        f"different tenant; refusing cross-tenant edge substitution."
                    )
                if (existing.source_node_id, existing.target_node_id, existing.relationship_kind) != (
                    edge.source_node_id, edge.target_node_id, edge.relationship_kind,
                ):
                    raise DuplicateTopologyEdgeIdentityError(
                        f"topology_edge_id {edge.topology_edge_id!r} is already registered "
                        f"against a different (source, target, relationship); refusing to "
                        f"silently repoint an existing edge."
                    )

            source_node = self._nodes_by_id.get(edge.source_node_id)
            target_node = self._nodes_by_id.get(edge.target_node_id)
            if source_node is None or target_node is None:
                raise TopologyRegistrationError(
                    "TopologyEdge source_node_id and target_node_id must both already be "
                    "registered nodes; a topology edge can never reference a node that "
                    "does not exist."
                )
            if source_node.tenant_id != edge.tenant_id or target_node.tenant_id != edge.tenant_id:
                raise CrossTenantTopologyError(
                    f"TopologyEdge {edge.topology_edge_id!r} references node(s) belonging to a "
                    f"different tenant than the edge's own tenant_id {edge.tenant_id!r}; refusing "
                    f"cross-tenant edge construction."
                )

            self._edges_by_id[edge.topology_edge_id] = edge
            if self._durability_store is not None:
                self._durability_store.save_topology_edge(edge)
            return edge

    def _register_reconstructed_edge(self, edge: TopologyEdge) -> None:
        with self._lock:
            self._edges_by_id[edge.topology_edge_id] = edge

    def mark_edge_stale(self, topology_edge_id: str, tenant_id: str) -> TopologyEdge:
        with self._lock:
            existing = self._edges_by_id.get(topology_edge_id)
            if existing is None:
                raise UnknownTopologyEdgeError(f"Unknown topology_edge_id: {topology_edge_id!r}")
            if existing.tenant_id != tenant_id:
                raise CrossTenantTopologyError(
                    f"topology_edge_id {topology_edge_id!r} belongs to a different tenant; "
                    f"refusing cross-tenant update."
                )
            updated = TopologyEdge(
                topology_edge_id=existing.topology_edge_id,
                source_node_id=existing.source_node_id,
                target_node_id=existing.target_node_id,
                relationship_kind=existing.relationship_kind,
                tenant_id=existing.tenant_id,
                connectivity_edge_ref=existing.connectivity_edge_ref,
                provenance_source=existing.provenance_source,
                observed_at=existing.observed_at,
                generation=existing.generation + 1,
                stale=True,
            )
            self._edges_by_id[topology_edge_id] = updated
            if self._durability_store is not None:
                self._durability_store.save_topology_edge(updated)
            return updated

    # ---------------------------------------------------------------- snapshot

    def snapshot(self, tenant_id: str) -> TopologyGraph:
        """Builds an immutable TopologyGraph for EXACTLY ONE tenant. There is
        deliberately no cross-tenant or all-tenant snapshot API anywhere in this class."""
        with self._lock:
            if not tenant_id or not tenant_id.strip():
                raise TopologyRegistrationError("snapshot() requires a non-empty tenant_id.")
            nodes = tuple(n for n in self._nodes_by_id.values() if n.tenant_id == tenant_id)
            edges = tuple(e for e in self._edges_by_id.values() if e.tenant_id == tenant_id)
            return TopologyGraph(tenant_id=tenant_id, nodes=nodes, edges=edges)


default_topology_registry = TopologyRegistry()
