"""akaalPipeline.orchestration.plans
===================================
Immutable execution graph node, edge, and plan descriptors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping
from akaalPipeline.contracts.enums import MigrationMode, SideEffectClassification
from akaalPipeline.contracts.serialization import canonical_fingerprint, canonical_serialize


@dataclass(frozen=True)
class NodeTaskDescriptor:
    task_id: str
    capability_contract: str
    side_effect: SideEffectClassification
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "capability_contract": self.capability_contract,
            "side_effect": self.side_effect.value,
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, data: dict) -> NodeTaskDescriptor:
        return cls(
            task_id=data["task_id"],
            capability_contract=data["capability_contract"],
            side_effect=SideEffectClassification(data["side_effect"]),
            parameters=data.get("parameters", {}),
        )


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    task: NodeTaskDescriptor
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "task": self.task.to_dict(),
            "dependencies": list(self.dependencies),
        }

    @classmethod
    def from_dict(cls, data: dict) -> GraphNode:
        return cls(
            node_id=data["node_id"],
            task=NodeTaskDescriptor.from_dict(data["task"]),
            dependencies=data.get("dependencies", []),
        )


@dataclass(frozen=True)
class GraphEdge:
    from_node: str
    to_node: str

    def to_dict(self) -> dict:
        return {"from_node": self.from_node, "to_node": self.to_node}

    @classmethod
    def from_dict(cls, data: dict) -> GraphEdge:
        return cls(from_node=data["from_node"], to_node=data["to_node"])


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    migration_id: str
    mode: MigrationMode
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    fingerprint: str

    @classmethod
    def create(cls, plan_id: str, migration_id: str, mode: MigrationMode, nodes: List[GraphNode], edges: List[GraphEdge]) -> ExecutionPlan:
        content = {
            "plan_id": plan_id,
            "migration_id": migration_id,
            "mode": mode.value,
            "nodes": [n.to_dict() for n in nodes],
            "edges": [e.to_dict() for e in edges],
        }
        fp = canonical_fingerprint(content)
        return cls(
            plan_id=plan_id,
            migration_id=migration_id,
            mode=mode,
            nodes=nodes,
            edges=edges,
            fingerprint=fp,
        )

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "migration_id": self.migration_id,
            "mode": self.mode.value,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ExecutionPlan:
        nodes = [GraphNode.from_dict(n) for n in data["nodes"]]
        edges = [GraphEdge.from_dict(e) for e in data["edges"]]
        return cls(
            plan_id=data["plan_id"],
            migration_id=data["migration_id"],
            mode=MigrationMode(data["mode"]),
            nodes=nodes,
            edges=edges,
            fingerprint=data["fingerprint"],
        )
