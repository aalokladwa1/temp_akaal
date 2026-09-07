"""
akaalEngine.fabric.topology.models
=====================================
P7B.11 -- Canonical Topology Graph.

A queryable, provenance-tracked representation of the infrastructure relationships
surrounding migration execution -- environments, execution sites, resources, networks,
regions, clusters and how they relate. This module composes OPAQUE references into the
existing canonical fabric authorities (Environment, ExecutionSite, CloudResourceLocator,
ConnectivityEdge, MovementRoute) -- it never re-derives or duplicates their identity,
trust, or proof semantics. A TopologyNode's `ref_id` and `ref_kind` merely point at an
already-canonical record; this module never invents a parallel identity for the same
physical thing.

ABSOLUTE LAW (P7B Group-2 security invariant, restated from the Group-2 directive and
binding here exactly like every other fail-closed law in this codebase):

    TOPOLOGY PRESENCE != AUTHORIZATION
    TOPOLOGY EDGE != PERMISSION
    REACHABILITY (as topology) != PERMISSION
    SITE ASSOCIATION != TRUST

Nothing in this module ever makes, checks, or influences an authorization decision.
`akaalPipeline.security.central_authorization` remains the sole authorization authority;
this module only ever answers "what does the infrastructure look like", never "is this
allowed".

Every topology fact is tenant/workspace scoped. A TopologyGraph snapshot is always built
for exactly one tenant -- there is no cross-tenant graph view anywhere in this module (see
TopologyRegistry.snapshot in topology.graph, which enforces this structurally).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping, Optional
from types import MappingProxyType


class TopologyNodeKind(str, Enum):
    ENVIRONMENT = "ENVIRONMENT"
    EXECUTION_SITE = "EXECUTION_SITE"
    RESOURCE = "RESOURCE"
    NETWORK = "NETWORK"
    REGION = "REGION"
    CLUSTER = "CLUSTER"
    STAGING = "STAGING"


class TopologyRelationshipKind(str, Enum):
    """Repository-native vocabulary for the relationships this graph actually needs to
    represent. Not exhaustive of every conceivable infrastructure relationship -- only
    what P7B Group-2 placement/locality reasoning genuinely consumes."""
    LOCATED_IN = "LOCATED_IN"
    ATTACHED_TO = "ATTACHED_TO"
    RUNS_IN = "RUNS_IN"
    CAN_REACH = "CAN_REACH"
    CONNECTED_VIA = "CONNECTED_VIA"
    HOSTS = "HOSTS"
    PART_OF = "PART_OF"


class TopologyValidationError(ValueError):
    pass


class TopologyProvenanceError(TopologyValidationError):
    """Raised when a topology fact's provenance is missing or malformed. Unknown
    provenance must never be silently represented as trusted discovery."""


_KNOWN_PROVENANCE_SOURCES = frozenset({
    "PROVIDER_DISCOVERY", "OPERATOR_CONFIGURATION", "SITE_REGISTRATION",
    "NETWORK_DISCOVERY", "REACHABILITY_PROOF", "KUBERNETES_DISCOVERY", "UNKNOWN",
})


def _validate_provenance_source(value: str) -> str:
    if not value or not value.strip():
        raise TopologyProvenanceError(
            "Topology provenance_source must be a non-empty string; unknown provenance "
            "must be explicitly declared as 'UNKNOWN', never omitted."
        )
    return value


@dataclass(frozen=True)
class TopologyNode:
    """
    Immutable topology node. `ref_id` is an opaque locator string into whichever
    canonical fabric record this node represents (an Environment.environment_id, an
    ExecutionSite.site_id, a CloudResourceLocator.native_identifier(), a
    NetworkSubnet.subnet_id, etc.) -- this module never validates or re-derives the
    referenced record's own semantics.

    `generation` increments on every mutation of this specific node's data (see
    TopologyRegistry.update_node); it is the basis for deterministic snapshot
    fingerprinting and staleness detection, mirroring the existing
    MovementRoute.topology_fingerprint()/is_stale_against() pattern from P7B.10.
    """
    node_id: str
    node_kind: TopologyNodeKind
    ref_id: str
    tenant_id: str
    workspace_id: Optional[str] = None
    display_name: str = ""
    provenance_source: str = "UNKNOWN"
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generation: int = 1
    stale: bool = False
    attributes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not self.node_id or not self.node_id.strip():
            raise TopologyValidationError("TopologyNode.node_id must be non-empty.")
        if not self.ref_id or not self.ref_id.strip():
            raise TopologyValidationError("TopologyNode.ref_id must be non-empty.")
        if not self.tenant_id or not self.tenant_id.strip():
            raise TopologyValidationError("TopologyNode.tenant_id must be non-empty.")
        if self.generation < 1:
            raise TopologyValidationError("TopologyNode.generation must be >= 1.")
        _validate_provenance_source(self.provenance_source)
        if not isinstance(self.attributes, MappingProxyType):
            object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

    def native_key(self) -> "tuple":
        """Deterministic dedupe key -- the physical thing this node represents, scoped to
        tenant, never the caller-chosen node_id alone (mirrors Environment.native_key())."""
        return (self.tenant_id, self.node_kind.value, self.ref_id)

    def fingerprint_part(self) -> str:
        return f"{self.node_id}:{self.generation}:{'STALE' if self.stale else 'FRESH'}"


@dataclass(frozen=True)
class TopologyEdge:
    """
    Immutable topology relationship between two TopologyNode ids. `connectivity_edge_ref`
    optionally points at an akaalEngine.fabric.connectivity.models.ConnectivityEdge.edge_id
    when this topology edge represents a CAN_REACH/CONNECTED_VIA relationship backed by a
    real connectivity declaration -- this module never re-implements proof-state semantics;
    it only carries the opaque reference.
    """
    topology_edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_kind: TopologyRelationshipKind
    tenant_id: str
    connectivity_edge_ref: Optional[str] = None
    provenance_source: str = "UNKNOWN"
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generation: int = 1
    stale: bool = False

    def __post_init__(self) -> None:
        if not self.topology_edge_id or not self.topology_edge_id.strip():
            raise TopologyValidationError("TopologyEdge.topology_edge_id must be non-empty.")
        if not self.source_node_id or not self.target_node_id:
            raise TopologyValidationError("TopologyEdge requires non-empty source_node_id and target_node_id.")
        if self.source_node_id == self.target_node_id:
            raise TopologyValidationError("TopologyEdge source_node_id and target_node_id must differ (no self-loop).")
        if not self.tenant_id or not self.tenant_id.strip():
            raise TopologyValidationError("TopologyEdge.tenant_id must be non-empty.")
        if self.generation < 1:
            raise TopologyValidationError("TopologyEdge.generation must be >= 1.")
        _validate_provenance_source(self.provenance_source)

    def fingerprint_part(self) -> str:
        return f"{self.topology_edge_id}:{self.generation}:{'STALE' if self.stale else 'FRESH'}"


def new_topology_node_id(node_kind: TopologyNodeKind) -> str:
    import uuid
    return f"topo-node-{node_kind.value.lower()}-{uuid.uuid4().hex[:16]}"


def new_topology_edge_id() -> str:
    import uuid
    return f"topo-edge-{uuid.uuid4().hex[:16]}"


def snapshot_fingerprint(nodes: "tuple", edges: "tuple") -> str:
    """Deterministic fingerprint of an exact set of (node, edge) generation/staleness
    states -- the Group-2 analogue of MovementRoute.topology_fingerprint(). Two snapshots
    with identical fingerprints are guaranteed to reflect identical topology-fact state;
    a changed fingerprint means SOMETHING (a generation bump or staleness transition)
    changed and any placement decision computed against the old fingerprint must be
    treated as potentially stale."""
    node_parts = sorted(n.fingerprint_part() for n in nodes)
    edge_parts = sorted(e.fingerprint_part() for e in edges)
    payload = "NODES|" + "|".join(node_parts) + "||EDGES|" + "|".join(edge_parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
