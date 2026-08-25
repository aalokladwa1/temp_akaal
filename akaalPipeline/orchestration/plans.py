"""akaalPipeline.orchestration.plans
===================================
Immutable execution graph node, edge, and plan descriptors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional
from akaalPipeline.contracts.enums import MigrationMode, NodeExecutionState, PlanExecutionStatus, SideEffectClassification
from akaalPipeline.contracts.serialization import canonical_fingerprint, canonical_serialize, deep_freeze



@dataclass(frozen=True)
class NodeTaskDescriptor:
    task_id: str
    capability_contract: str
    side_effect: SideEffectClassification
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", deep_freeze(self.parameters))

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

    def __post_init__(self) -> None:
        object.__setattr__(self, "dependencies", tuple(self.dependencies))

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
    configuration: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "configuration", deep_freeze(self.configuration))

    @classmethod
    def create(
        cls,
        plan_id: str,
        migration_id: str,
        mode: MigrationMode,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        configuration: Optional[Mapping[str, Any]] = None,
    ) -> ExecutionPlan:
        cfg = dict(configuration) if configuration else {}
        content = {
            "plan_id": plan_id,
            "migration_id": migration_id,
            "mode": mode.value,
            "nodes": [n.to_dict() for n in nodes],
            "edges": [e.to_dict() for e in edges],
            "configuration": cfg,
        }
        fp = canonical_fingerprint(content)
        return cls(
            plan_id=plan_id,
            migration_id=migration_id,
            mode=mode,
            nodes=nodes,
            edges=edges,
            fingerprint=fp,
            configuration=cfg,
        )

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "migration_id": self.migration_id,
            "mode": self.mode.value,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "fingerprint": self.fingerprint,
            "configuration": dict(self.configuration),
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
            configuration=data.get("configuration", {}),
        )


@dataclass(frozen=True)
class PlanExecutionRecord:
    execution_id: str
    migration_id: str
    plan_id: str
    plan_fingerprint: str
    initialization_fingerprint: str
    tenant_id: str
    workspace_id: str
    project_id: str
    status: PlanExecutionStatus
    created_at: str
    updated_at: str
    start_operation_id: Optional[str] = None
    checkpoint_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "migration_id": self.migration_id,
            "plan_id": self.plan_id,
            "plan_fingerprint": self.plan_fingerprint,
            "initialization_fingerprint": self.initialization_fingerprint,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "start_operation_id": self.start_operation_id,
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlanExecutionRecord:
        return cls(
            execution_id=data["execution_id"],
            migration_id=data["migration_id"],
            plan_id=data["plan_id"],
            plan_fingerprint=data["plan_fingerprint"],
            initialization_fingerprint=data["initialization_fingerprint"],
            tenant_id=data["tenant_id"],
            workspace_id=data["workspace_id"],
            project_id=data["project_id"],
            status=PlanExecutionStatus(data["status"]),
            start_operation_id=data.get("start_operation_id"),
            checkpoint_id=data.get("checkpoint_id"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


@dataclass(frozen=True)
class NodeExecutionRecord:
    node_execution_id: str
    execution_id: str
    migration_id: str
    graph_node_id: str
    capability_contract: str
    side_effect: SideEffectClassification
    state: NodeExecutionState
    current_attempt_id: Optional[str] = None
    current_invocation_id: Optional[str] = None
    current_engine_task_id: Optional[str] = None
    binding_id: Optional[str] = None
    contract_version: Optional[str] = None
    lease_id: Optional[str] = None
    fence_epoch: Optional[int] = None
    checkpoint_id: Optional[str] = None
    result_payload: Optional[Mapping[str, Any]] = None
    error: Optional[Mapping[str, Any]] = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "node_execution_id": self.node_execution_id,
            "execution_id": self.execution_id,
            "migration_id": self.migration_id,
            "graph_node_id": self.graph_node_id,
            "capability_contract": self.capability_contract,
            "side_effect": self.side_effect.value,
            "state": self.state.value,
            "current_attempt_id": self.current_attempt_id,
            "current_invocation_id": self.current_invocation_id,
            "current_engine_task_id": self.current_engine_task_id,
            "binding_id": self.binding_id,
            "contract_version": self.contract_version,
            "lease_id": self.lease_id,
            "fence_epoch": self.fence_epoch,
            "checkpoint_id": self.checkpoint_id,
            "result_payload": dict(self.result_payload) if self.result_payload else None,
            "error": dict(self.error) if self.error else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NodeExecutionRecord:
        return cls(
            node_execution_id=data["node_execution_id"],
            execution_id=data["execution_id"],
            migration_id=data["migration_id"],
            graph_node_id=data["graph_node_id"],
            capability_contract=data["capability_contract"],
            side_effect=SideEffectClassification(data["side_effect"]),
            state=NodeExecutionState(data["state"]),
            current_attempt_id=data.get("current_attempt_id"),
            current_invocation_id=data.get("current_invocation_id"),
            current_engine_task_id=data.get("current_engine_task_id"),
            binding_id=data.get("binding_id"),
            contract_version=data.get("contract_version"),
            lease_id=data.get("lease_id"),
            fence_epoch=data.get("fence_epoch"),
            checkpoint_id=data.get("checkpoint_id"),
            result_payload=data.get("result_payload"),
            error=data.get("error"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
