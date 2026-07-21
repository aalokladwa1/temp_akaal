"""
AKAAL Platform 5 — Version DAG Graph

Maintains complete DAG lineage for version snapshots supporting branching, ancestry, and divergence detection.
"""

from dataclasses import dataclass, field
import threading
from typing import Dict, List, Optional, Set

from akaal.schema.domain.errors import MetadataError
from akaal.schema.domain.identifiers import VersionID


@dataclass
class VersionNode:
    version_id: VersionID
    parent_ids: List[VersionID] = field(default_factory=list)
    branch_name: str = "main"
    author: str = "system"
    commit_message: str = ""
    timestamp: float = 0.0


class VersionDAG:
    """Thread-safe version ancestry graph."""

    def __init__(self) -> None:
        self._mutex = threading.RLock()
        self._nodes: Dict[str, VersionNode] = {}
        self._children: Dict[str, Set[str]] = {}

    def add_version(self, node: VersionNode) -> None:
        v_str = str(node.version_id)
        with self._mutex:
            if v_str in self._nodes:
                return
            self._nodes[v_str] = node
            if v_str not in self._children:
                self._children[v_str] = set()

            for p_id in node.parent_ids:
                p_str = str(p_id)
                if p_str not in self._children:
                    self._children[p_str] = set()
                self._children[p_str].add(v_str)

    def get_node(self, version_id: VersionID) -> Optional[VersionNode]:
        with self._mutex:
            return self._nodes.get(str(version_id))

    def find_lca(self, v1: VersionID, v2: VersionID) -> Optional[VersionID]:
        """Finds Lowest Common Ancestor (LCA) for 3-way merging."""
        with self._mutex:
            anc1 = self._get_ancestors(str(v1))
            anc2 = self._get_ancestors(str(v2))
            common = anc1.intersection(anc2)
            if not common:
                return None
            # Return ancestor with highest depth/latest timestamp
            best_node = None
            best_ts = -1.0
            for cid in common:
                node = self._nodes[cid]
                if node.timestamp > best_ts:
                    best_ts = node.timestamp
                    best_node = node.version_id
            return best_node

    def _get_ancestors(self, start_id: str) -> Set[str]:
        ancestors = {start_id}
        queue = [start_id]
        while queue:
            curr = queue.pop(0)
            node = self._nodes.get(curr)
            if node:
                for pid in node.parent_ids:
                    p_str = str(pid)
                    if p_str not in ancestors:
                        ancestors.add(p_str)
                        queue.append(p_str)
        return ancestors
