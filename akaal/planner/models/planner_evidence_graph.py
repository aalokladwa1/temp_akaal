"""
Akaal — Planner Evidence Graph
==============================
Interconnected directed graph storing evidence nodes referencing Risk Assessment items and planning decisions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlannerEvidenceNode:
    evidence_id: str
    node_type: str  # "RISK_ASSESSMENT", "STRATEGY", "CONSTRAINT", "CONFLICT_RESOLUTION"
    reference_id: str
    analyzer_name: str
    reason: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "node_type": self.node_type,
            "reference_id": self.reference_id,
            "analyzer_name": self.analyzer_name,
            "reason": self.reason,
            "attributes": self.attributes,
        }


@dataclass
class PlannerEvidenceGraph:
    """Directed Evidence Graph for Planner decisions."""
    nodes: Dict[str, PlannerEvidenceNode] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=dict)

    def add_node(self, node: PlannerEvidenceNode) -> None:
        self.nodes[node.evidence_id] = node

    def add_edge(self, source_id: str, target_id: str) -> None:
        if source_id not in self.edges:
            self.edges[source_id] = []
        self.edges[source_id].append(target_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": self.edges,
        }
