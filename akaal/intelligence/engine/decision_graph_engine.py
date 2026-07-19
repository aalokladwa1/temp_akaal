"""
AKAAL Enterprise Intelligence Platform — Decision Graph Engine
===============================================================
Directed Acyclic Graph (DAG) dependency evaluation, topological sorting, cycle detection,
Multi-Attribute Utility Theory (MAUT) conflict resolution, and strategic decision synthesis.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from akaal.intelligence.models.agent_coordination_plan import AgentCoordinationPlan
from akaal.intelligence.models.enterprise_decision import EnterpriseDecision
from akaal.intelligence.models.enterprise_intelligence_enums import (
    DecisionPriority,
    ReadinessTier,
    RiskLevel,
    StrategyType,
)
from akaal.intelligence.models.migration_simulation_result import MigrationSimulationResult
from akaal.intelligence.models.readiness_assessment import ReadinessAssessment
from akaal.intelligence.models.strategy_synthesis import StrategySynthesis


class DecisionGraphError(Exception):
    """Exception raised for errors in DecisionGraphEngine operations."""
    pass


class DecisionGraphCycleError(DecisionGraphError):
    """Exception raised when a circular dependency is detected in the Decision Graph."""
    pass


@dataclass(frozen=True)
class DecisionGraphNode:
    """Immutable node in the Decision Graph representing an analyzer or decision dependency."""
    node_id: str
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    weight: float = 1.0
    payload: Dict[str, Any] = field(default_factory=dict)


class DecisionGraphEngine:
    """
    Core intelligence engine that builds a DAG of analyzers/decisions, performs topological
    sorting, detects cycles, resolves decision conflicts via MAUT, and synthesizes output models.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, DecisionGraphNode] = {}

    def add_node(self, node_id: str, dependencies: Optional[List[str]] = None, weight: float = 1.0, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Adds a node to the graph.

        Raises:
            DecisionGraphError: If node_id is invalid or node already exists.
        """
        if not node_id or not isinstance(node_id, str):
            raise DecisionGraphError("Node ID must be a non-empty string.")

        if node_id in self._nodes:
            raise DecisionGraphError(f"Node '{node_id}' is already registered in the graph.")

        deps_tuple = tuple(dependencies) if dependencies else ()
        self._nodes[node_id] = DecisionGraphNode(
            node_id=node_id,
            dependencies=deps_tuple,
            weight=float(weight),
            payload=dict(payload) if payload else {},
        )

    def validate_graph(self) -> bool:
        """
        Validates graph integrity, missing dependencies, and cycle presence.

        Raises:
            DecisionGraphError: If a node references a non-existent dependency.
            DecisionGraphCycleError: If a cycle is detected.
        """
        # Missing dependency validation
        for node in self._nodes.values():
            for dep in node.dependencies:
                if dep not in self._nodes:
                    raise DecisionGraphError(
                        f"Node '{node.node_id}' references non-existent dependency '{dep}'."
                    )

        # Cycle detection via DFS (Kahn's / Tarjan's cycle check)
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)

            for dep in self._nodes[node_id].dependencies:
                if dep not in visited:
                    dfs(dep, path + [dep])
                elif dep in rec_stack:
                    cycle_path = " -> ".join(path + [dep])
                    raise DecisionGraphCycleError(f"Circular dependency detected: {cycle_path}")

            rec_stack.remove(node_id)

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id, [node_id])

        return True

    def topological_sort(self) -> List[str]:
        """
        Performs a deterministic topological sort of the graph nodes.
        Dependencies are returned BEFORE dependent nodes. Tied nodes are sorted alphabetically.

        Returns:
            List of node IDs in deterministic execution order.
        """
        self.validate_graph()

        # In-degree calculation
        in_degree: Dict[str, int] = {node_id: 0 for node_id in self._nodes}
        for node in self._nodes.values():
            for dep in node.dependencies:
                # In this graph, node depends on dep (dep -> node)
                in_degree[node.node_id] += 1

        # Queue of nodes with zero in-degree (ready to evaluate)
        zero_in_degree = sorted([n for n, deg in in_degree.items() if deg == 0])
        sorted_order: List[str] = []

        while zero_in_degree:
            # Pop deterministically (first in sorted list)
            curr = zero_in_degree.pop(0)
            sorted_order.append(curr)

            # Reduce in-degree for nodes that depend on curr
            for node_id, node in self._nodes.items():
                if curr in node.dependencies:
                    in_degree[node_id] -= 1
                    if in_degree[node_id] == 0:
                        zero_in_degree.append(node_id)
                        zero_in_degree.sort()

        if len(sorted_order) != len(self._nodes):
            raise DecisionGraphCycleError("Cycle detected during topological sorting.")

        return sorted_order

    def compute_graph_hash(self) -> str:
        """Computes a 100% deterministic SHA-256 hash of the graph structure."""
        nodes_summary = []
        for node_id in sorted(self._nodes.keys()):
            node = self._nodes[node_id]
            nodes_summary.append({
                "id": node.node_id,
                "deps": sorted(list(node.dependencies)),
                "weight": node.weight,
            })
        canonical_json = json.dumps(nodes_summary, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @staticmethod
    def resolve_conflicts(decisions: List[EnterpriseDecision]) -> List[EnterpriseDecision]:
        """
        Resolves conflicting enterprise decisions using Multi-Attribute Utility Theory (MAUT).
        MAUT Score = priority_weight * 0.4 + confidence_score * 0.4 + (1 - risk_weight) * 0.2
        Deduplicates decisions targeting identical categories/components deterministically.
        """
        if not decisions:
            return []

        priority_weights = {
            DecisionPriority.CRITICAL: 1.0,
            DecisionPriority.HIGH: 0.8,
            DecisionPriority.MEDIUM: 0.5,
            DecisionPriority.LOW: 0.2,
            DecisionPriority.OPTIONAL: 0.1,
        }

        risk_weights = {
            RiskLevel.CRITICAL: 1.0,
            RiskLevel.HIGH: 0.8,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.LOW: 0.2,
            RiskLevel.NEGLIGIBLE: 0.0,
        }

        # Deduplicate & rank by MAUT score
        grouped: Dict[str, List[EnterpriseDecision]] = {}
        for d in decisions:
            key = f"{d.category}:{d.title}"
            grouped.setdefault(key, []).append(d)

        resolved_decisions: List[EnterpriseDecision] = []

        for key in sorted(grouped.keys()):
            candidates = grouped[key]
            if len(candidates) == 1:
                resolved_decisions.append(candidates[0])
            else:
                # Rank candidates by MAUT score
                def maut_score(d: EnterpriseDecision) -> float:
                    p_w = priority_weights.get(d.priority, 0.5)
                    r_w = risk_weights.get(d.risk_level, 0.5)
                    return round((p_w * 0.4) + (d.confidence_score * 0.4) + ((1.0 - r_w) * 0.2), 4)

                candidates.sort(key=lambda x: (-maut_score(x), x.decision_id))
                resolved_decisions.append(candidates[0])

        # Sort final resolved decisions deterministically (CRITICAL -> HIGH -> MEDIUM -> LOW -> OPTIONAL)
        priority_rank = {
            DecisionPriority.CRITICAL: 0,
            DecisionPriority.HIGH: 1,
            DecisionPriority.MEDIUM: 2,
            DecisionPriority.LOW: 3,
            DecisionPriority.OPTIONAL: 4,
        }

        resolved_decisions.sort(key=lambda d: (priority_rank.get(d.priority, 5), -d.confidence_score, d.decision_id))
        return resolved_decisions
