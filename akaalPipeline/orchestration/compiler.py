"""akaalPipeline.orchestration.compiler
======================================
Compiles immutable execution plans from mode, config, and catalog capabilities.
"""

from __future__ import annotations

from typing import List, Mapping
from akaalPipeline.contracts.enums import MigrationMode, SideEffectClassification
from akaalPipeline.orchestration.graph_validation import GraphValidator
from akaalPipeline.orchestration.plans import ExecutionPlan, GraphEdge, GraphNode, NodeTaskDescriptor


class GraphCompiler:
    @staticmethod
    def compile_plan(
        plan_id: str,
        migration_id: str,
        mode: MigrationMode,
        config: Optional[Mapping[str, Any]] = None,
        configuration: Optional[Mapping[str, Any]] = None,
    ) -> ExecutionPlan:
        """Compiles deterministic graph node tasks appropriate for mode."""
        effective_config = configuration if configuration is not None else (config or {})
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []


        if mode == MigrationMode.M1_BULK:
            task1 = NodeTaskDescriptor(task_id="t-schema-prep", capability_contract="schema_prep", side_effect=SideEffectClassification.REVERSIBLE)
            node1 = GraphNode(node_id="n-schema-prep", task=task1, dependencies=[])
            task2 = NodeTaskDescriptor(task_id="t-data-transport", capability_contract="data_transport", side_effect=SideEffectClassification.REVERSIBLE)
            node2 = GraphNode(node_id="n-data-transport", task=task2, dependencies=["n-schema-prep"])
            nodes.extend([node1, node2])
            edges.append(GraphEdge(from_node="n-schema-prep", to_node="n-data-transport"))

        elif mode == MigrationMode.M2_BULK_CDC:
            task1 = NodeTaskDescriptor(task_id="t-schema-prep", capability_contract="schema_prep", side_effect=SideEffectClassification.REVERSIBLE)
            node1 = GraphNode(node_id="n-schema-prep", task=task1, dependencies=[])
            task2 = NodeTaskDescriptor(task_id="t-data-transport", capability_contract="data_transport", side_effect=SideEffectClassification.REVERSIBLE)
            node2 = GraphNode(node_id="n-data-transport", task=task2, dependencies=["n-schema-prep"])
            task3 = NodeTaskDescriptor(task_id="t-cdc-sync", capability_contract="cdc_sync", side_effect=SideEffectClassification.REVERSIBLE)
            node3 = GraphNode(node_id="n-cdc-sync", task=task3, dependencies=["n-data-transport"])
            nodes.extend([node1, node2, node3])
            edges.extend([
                GraphEdge(from_node="n-schema-prep", to_node="n-data-transport"),
                GraphEdge(from_node="n-data-transport", to_node="n-cdc-sync"),
            ])

        elif mode == MigrationMode.M3_CDC:
            task1 = NodeTaskDescriptor(task_id="t-cdc-capture", capability_contract="cdc_capture", side_effect=SideEffectClassification.READ_ONLY)
            node1 = GraphNode(node_id="n-cdc-capture", task=task1, dependencies=[])
            task2 = NodeTaskDescriptor(task_id="t-cdc-apply", capability_contract="cdc_apply", side_effect=SideEffectClassification.REVERSIBLE)
            node2 = GraphNode(node_id="n-cdc-apply", task=task2, dependencies=["n-cdc-capture"])
            nodes.extend([node1, node2])
            edges.append(GraphEdge(from_node="n-cdc-capture", to_node="n-cdc-apply"))

        elif mode == MigrationMode.M4_INCREMENTAL:
            task1 = NodeTaskDescriptor(task_id="t-inc-extract", capability_contract="incremental_extract", side_effect=SideEffectClassification.READ_ONLY)
            node1 = GraphNode(node_id="n-inc-extract", task=task1, dependencies=[])
            task2 = NodeTaskDescriptor(task_id="t-inc-apply", capability_contract="incremental_apply", side_effect=SideEffectClassification.REVERSIBLE)
            node2 = GraphNode(node_id="n-inc-apply", task=task2, dependencies=["n-inc-extract"])
            nodes.extend([node1, node2])
            edges.append(GraphEdge(from_node="n-inc-extract", to_node="n-inc-apply"))

        elif mode == MigrationMode.M5_STATE_SYNC:
            task1 = NodeTaskDescriptor(task_id="t-state-diff", capability_contract="state_diff", side_effect=SideEffectClassification.READ_ONLY)
            node1 = GraphNode(node_id="n-state-diff", task=task1, dependencies=[])
            task2 = NodeTaskDescriptor(task_id="t-state-reconcile", capability_contract="state_reconcile", side_effect=SideEffectClassification.REVERSIBLE)
            node2 = GraphNode(node_id="n-state-reconcile", task=task2, dependencies=["n-state-diff"])
            nodes.extend([node1, node2])
            edges.append(GraphEdge(from_node="n-state-diff", to_node="n-state-reconcile"))

        elif mode == MigrationMode.M6_SCHEMA_ONLY:
            task1 = NodeTaskDescriptor(task_id="t-schema-extract", capability_contract="schema_extract", side_effect=SideEffectClassification.READ_ONLY)
            node1 = GraphNode(node_id="n-schema-extract", task=task1, dependencies=[])
            task2 = NodeTaskDescriptor(task_id="t-schema-apply", capability_contract="schema_apply", side_effect=SideEffectClassification.REVERSIBLE)
            node2 = GraphNode(node_id="n-schema-apply", task=task2, dependencies=["n-schema-extract"])
            nodes.extend([node1, node2])
            edges.append(GraphEdge(from_node="n-schema-extract", to_node="n-schema-apply"))

        elif mode == MigrationMode.M7_DATA_ONLY:
            task1 = NodeTaskDescriptor(task_id="t-data-transport", capability_contract="data_transport", side_effect=SideEffectClassification.REVERSIBLE)
            node1 = GraphNode(node_id="n-data-transport", task=task1, dependencies=[])
            nodes.append(node1)

        elif mode == MigrationMode.M8_VALIDATION_ONLY:
            task1 = NodeTaskDescriptor(task_id="t-val-compare", capability_contract="validation_compare", side_effect=SideEffectClassification.READ_ONLY)
            node1 = GraphNode(node_id="n-val-compare", task=task1, dependencies=[])
            nodes.append(node1)

        else:
            task1 = NodeTaskDescriptor(task_id="t-generic", capability_contract="generic_execution", side_effect=SideEffectClassification.REVERSIBLE)
            node1 = GraphNode(node_id="n-generic", task=task1, dependencies=[])
            nodes.append(node1)


        plan = ExecutionPlan.create(
            plan_id=plan_id,
            migration_id=migration_id,
            mode=mode,
            nodes=nodes,
            edges=edges,
        )
        GraphValidator.validate_plan(plan)
        return plan
