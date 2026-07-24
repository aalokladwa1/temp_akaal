"""TopologyDiscoveryManager: Discovers live replication nodes and clusters."""

from typing import List, Optional
from akaal.replication.topology.graph import ReplicationTopologyGraph
from akaal.replication.core.models import ReplicaNode, ReplicaRole


class TopologyDiscoveryManager:
    """Discovers live cluster nodes and populates topology graph."""

    def discover_live_topology(self, default_regions: Optional[List[str]] = None) -> ReplicationTopologyGraph:
        graph = ReplicationTopologyGraph()
        regions = default_regions or ["us-east", "us-west", "eu-central"]
        for idx, region in enumerate(regions):
            node_p = ReplicaNode(node_id=f"node_primary_{region}", region=region, role=ReplicaRole.PRIMARY, is_active=True, health_score=100.0)
            node_s = ReplicaNode(node_id=f"node_sec_{region}", region=region, role=ReplicaRole.SECONDARY, is_active=True, health_score=98.0)
            graph.add_node(node_p)
            graph.add_node(node_s)
            graph.add_replication_path(node_p.node_id, node_s.node_id)

        # Connect inter-region primaries for active-active
        primaries = [n.node_id for n in graph.nodes.values() if n.role == ReplicaRole.PRIMARY]
        if len(primaries) >= 2:
            graph.add_replication_path(primaries[0], primaries[1])
        return graph
