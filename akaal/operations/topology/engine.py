"""
Enterprise Topology Engine.
Models parental relationships, system structures, and dependency graphs.
"""

from typing import Dict, List, Set, Optional, Any
from threading import RLock


class TopologyNode:
    """A structural node in the system topology."""
    def __init__(self, node_id: str, node_type: str, label: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.node_id = node_id
        self.node_type = node_type  # AKAAL, Cluster, Node, Worker, Platform, Job
        self.label = label
        self.metadata = metadata or {}
        self.children: Set[str] = set()
        self.parents: Set[str] = set()


class TopologyEngine:
    """Models parent-child relationships and system hierarchy."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._nodes: Dict[str, TopologyNode] = {}
        # Root node
        self.add_node("root_akaal", "AKAAL", "AKAAL Enterprise Core Platform")

    def add_node(self, node_id: str, node_type: str, label: str, metadata: Optional[Dict[str, Any]] = None) -> TopologyNode:
        with self._lock:
            if node_id not in self._nodes:
                self._nodes[node_id] = TopologyNode(node_id, node_type, label, metadata)
            return self._nodes[node_id]

    def add_relationship(self, parent_id: str, child_id: str) -> None:
        with self._lock:
            if parent_id in self._nodes and child_id in self._nodes:
                self._nodes[parent_id].children.add(child_id)
                self._nodes[child_id].parents.add(parent_id)

    def get_children(self, parent_id: str) -> List[TopologyNode]:
        with self._lock:
            parent = self._nodes.get(parent_id)
            if not parent:
                return []
            return [self._nodes[cid] for cid in parent.children if cid in self._nodes]

    def export_hierarchy(self) -> Dict[str, Any]:
        return self.get_topology_snapshot()
    
    def get_topology_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                node_id: {
                    "type": node.node_type,
                    "label": node.label,
                    "children": list(node.children),
                    "parents": list(node.parents)
                }
                for node_id, node in self._nodes.items()
            }
