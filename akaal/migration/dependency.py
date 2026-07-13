from typing import Dict, List, Set, Tuple
from akaal.migration.models import MigrationPlan, MigrationOperation

class DependencyResolver:
    """
    Generic, database-agnostic topological sorting engine.
    Works purely on operation_id and depends_on values.
    Does NOT inspect table names, database dialects, or object types.
    """

    def resolve(self, plan: MigrationPlan) -> List[MigrationOperation]:
        """
        Orders the operations in the MigrationPlan topologically.
        Raises ValueError if a cyclic dependency is detected.
        """
        # Step 1: Initialize graph representation
        # adjacency_list: maps parent operation_id to children operation_ids that depend on it
        adjacency_list: Dict[str, List[str]] = {}
        # in_degrees: maps operation_id to count of parent dependencies it requires
        in_degrees: Dict[str, int] = {}
        # id_to_op: maps operation_id to actual MigrationOperation object
        id_to_op: Dict[str, MigrationOperation] = {}

        for op in plan.operations:
            id_to_op[op.operation_id] = op
            in_degrees[op.operation_id] = 0
            adjacency_list[op.operation_id] = []

        # Step 2: Build the graph
        for op in plan.operations:
            for dep_id in op.depends_on:
                # If dependency is part of the plan, record it
                if dep_id in in_degrees:
                    adjacency_list[dep_id].append(op.operation_id)
                    in_degrees[op.operation_id] += 1
                # If dependency is external (not in this plan), we ignore it or treat it as pre-satisfied

        # Step 3: Find all start nodes (in-degree == 0)
        # Sort key to ensure deterministic ordering (Planner determinism requirement)
        start_nodes = [node_id for node_id, deg in in_degrees.items() if deg == 0]
        start_nodes.sort()  # Alphabetical / ID-based sort for stable tie-breaking

        # Step 4: Kahn's Algorithm
        ordered_ids: List[str] = []
        
        while start_nodes:
            # Pop deterministic node
            curr_id = start_nodes.pop(0)
            ordered_ids.append(curr_id)

            # Decrement in-degree of all dependent children
            children = adjacency_list.get(curr_id, [])
            children.sort()  # deterministic tie-breaking for processing order
            for child_id in children:
                in_degrees[child_id] -= 1
                if in_degrees[child_id] == 0:
                    start_nodes.append(child_id)
            start_nodes.sort()  # keep queue sorted for stable outcomes

        # Step 5: Assert no cycles
        if len(ordered_ids) < len(in_degrees):
            # Find nodes involved in cycle
            cycle_nodes = [node_id for node_id, deg in in_degrees.items() if deg > 0]
            raise ValueError(f"Cyclic dependency detected among operations: {sorted(cycle_nodes)}")

        # Step 6: Map back to actual operations
        return [id_to_op[op_id] for op_id in ordered_ids]
