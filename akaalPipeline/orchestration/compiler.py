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
        config: Mapping[str, Any],
    ) -> ExecutionPlan:
        """Compiles deterministic graph node tasks appropriate for mode."""
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        if mode == MigrationMode.M6_SCHEMA_ONLY:
            task1 = NodeTaskDescriptor(
                task_id="t-schema-extract",
                capability_contract="schema_extract",
                side_effect=SideEffectClassification.READ_ONLY,
            )
            node1 = GraphNode(node_id="n-schema-extract", task=task1, dependencies=[])

            task2 = NodeTaskDescriptor(
                task_id="t-schema-apply",
                capability_contract="schema_apply",
                side_effect=SideEffectClassification.REVERSIBLE,
            )
            node2 = GraphNode(node_id="n-schema-apply", task=task2, dependencies=["n-schema-extract"])

            nodes.extend([node1, node2])
            edges.append(GraphEdge(from_node="n-schema-extract", to_node="n-schema-apply"))

        elif mode == MigrationMode.M8_VALIDATION_ONLY:
            task1 = NodeTaskDescriptor(
                task_id="t-val-compare",
                capability_contract="validation_compare",
                side_effect=SideEffectClassification.READ_ONLY,
            )
            node1 = GraphNode(node_id="n-val-compare", task=task1, dependencies=[])
            nodes.append(node1)

        else:  # M1, M2, M4, M5, M7
            task1 = NodeTaskDescriptor(
                task_id="t-schema-prep",
                capability_contract="schema_prep",
                side_effect=SideEffectClassification.REVERSIBLE,
            )
            node1 = GraphNode(node_id="n-schema-prep", task=task1, dependencies=[])

            task2 = NodeTaskDescriptor(
                task_id="t-data-transport",
                capability_contract="data_transport",
                side_effect=SideEffectClassification.REVERSIBLE,
            )
            node2 = GraphNode(node_id="n-data-transport", task=task2, dependencies=["n-schema-prep"])

            nodes.extend([node1, node2])
            edges.append(GraphEdge(from_node="n-schema-prep", to_node="n-data-transport"))

        plan = ExecutionPlan.create(
            plan_id=plan_id,
            migration_id=migration_id,
            mode=mode,
            nodes=nodes,
            edges=edges,
        )
        GraphValidator.validate_plan(plan)
        return plan
