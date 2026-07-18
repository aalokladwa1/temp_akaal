"""
Akaal — Risk Evidence Graph
===========================
Interconnected directed graph storing immutable evidence nodes referencing Canonical Objects and Canonical Rule Provenance.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceNode:
    evidence_id: str
    node_type: str  # "CANONICAL_OBJECT", "CANONICAL_RULE_PROVENANCE", "CAPABILITY", "SEMANTIC_MAPPING"
    canonical_id: Optional[str] = None
    canonical_identity: Optional[Dict[str, Any]] = None
    rule_provenance: Optional[Dict[str, Any]] = None  # Embedded rule provenance from Decoder
    analyzer_name: str = ""
    reason: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "node_type": self.node_type,
            "canonical_id": self.canonical_id,
            "canonical_identity": self.canonical_identity,
            "rule_provenance": self.rule_provenance,
            "analyzer_name": self.analyzer_name,
            "reason": self.reason,
            "attributes": self.attributes,
        }


@dataclass
class RiskEvidenceGraph:
    """Directed Evidence Graph linking evidence nodes."""
    nodes: Dict[str, EvidenceNode] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=dict)

    def add_node(self, node: EvidenceNode) -> None:
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
