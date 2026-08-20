"""akaalPipeline.orchestration.graph_validation
=================================================
Validates execution plan graphs against M1-M8 mode legality rules and cycle detection.
"""

from __future__ import annotations

from typing import Dict, Set
from akaalPipeline.contracts.enums import MigrationMode, SideEffectClassification
from akaalPipeline.contracts.errors import UnsupportedModeError
from akaalPipeline.orchestration.plans import ExecutionPlan


class GraphValidator:
    @staticmethod
    def validate_plan(plan: ExecutionPlan) -> None:
        """Validates DAG structure, cycle freedom, and M1-M8 mode legality."""
        # 1. Cycle detection (topological sort check)
        adj: Dict[str, Set[str]] = {n.node_id: set() for n in plan.nodes}
        in_degree: Dict[str, int] = {n.node_id: 0 for n in plan.nodes}

        for edge in plan.edges:
            if edge.from_node not in adj or edge.to_node not in adj:
                raise UnsupportedModeError(f"Edge references unknown node: {edge.from_node} -> {edge.to_node}")
            adj[edge.from_node].add(edge.to_node)
            in_degree[edge.to_node] += 1

        queue = [n for n, deg in in_degree.items() if deg == 0]
        visited_count = 0
        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(plan.nodes):
            raise UnsupportedModeError("Execution plan graph contains a dependency cycle.")

        # 2. M1-M8 Mode Legality Rules
        mode = plan.mode
        for node in plan.nodes:
            contract = node.task.capability_contract.lower()
            side_effect = node.task.side_effect

            if mode == MigrationMode.M6_SCHEMA_ONLY:
                if "data_transport" in contract or "cdc" in contract or "data_write" in contract:
                    raise UnsupportedModeError(
                        f"Mode M6 (Schema Only) prohibits data transport capability {contract!r} in node {node.node_id!r}."
                    )
            elif mode == MigrationMode.M7_DATA_ONLY:
                if "schema_ddl" in contract or "schema_create" in contract:
                    raise UnsupportedModeError(
                        f"Mode M7 (Data Only) prohibits schema DDL capability {contract!r} in node {node.node_id!r}."
                    )
            elif mode == MigrationMode.M8_VALIDATION_ONLY:
                if side_effect in (SideEffectClassification.DESTRUCTIVE, SideEffectClassification.IRREVERSIBLE):
                    raise UnsupportedModeError(
                        f"Mode M8 (Validation Only) prohibits mutation side-effect {side_effect.value!r} in node {node.node_id!r}."
                    )
            elif mode == MigrationMode.M3_CDC:
                if "initial_bulk_copy" in contract:
                    raise UnsupportedModeError(
                        f"Mode M3 (CDC Only) prohibits initial bulk copy capability {contract!r} in node {node.node_id!r}."
                    )
