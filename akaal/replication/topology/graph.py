"""ReplicationTopologyGraph: Directed graph tracking nodes, clusters, regions, and routes."""

from typing import Dict, List, Set, Optional
from akaal.replication.core.models import ReplicaNode, ReplicaRole


class ReplicationTopologyGraph:
    """Manages node relationships, parent-child dependencies, and circular route detection."""

    def __init__(self):
        self.nodes: Dict[str, ReplicaNode] = {}
        self.adj: Dict[str, List[str]] = {}

    def add_node(self, node: ReplicaNode) -> None:
        self.nodes[node.node_id] = node
        if node.node_id not in self.adj:
            self.adj[node.node_id] = []

    def add_replication_path(self, source_id: str, target_id: str) -> None:
        """Source node replicates to Target node."""
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError(f"Nodes {source_id} or {target_id} not registered in topology.")
        self.adj[source_id].append(target_id)

    def detect_circular_routes(self) -> bool:
        """Check for circular loops in replication graph."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def is_cyclic(curr: str) -> bool:
            visited.add(curr)
            rec_stack.add(curr)
            for child in self.adj.get(curr, []):
                if child not in visited:
                    if is_cyclic(child):
                        return True
                elif child in rec_stack:
                    return True
            rec_stack.remove(curr)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if is_cyclic(node_id):
                    return True
        return False

    def get_downstream_nodes(self, source_id: str) -> List[str]:
        return self.adj.get(source_id, [])
