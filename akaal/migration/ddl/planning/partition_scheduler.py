from typing import List, Tuple, Dict, Set
from akaal.migration.ddl.planning.partition_models import PartitionBaseAction, PlanReadinessStatus

class PartitionDependencyScheduler:
    @staticmethod
    def schedule(
        actions: Tuple[PartitionBaseAction, ...],
        dependency_graph: Dict[str, Tuple[str, ...]]
    ) -> Tuple[PartitionBaseAction, ...]:
        """
        Sorts the partition planner actions topologically.
        Breaks ties deterministically using sorting lexicographically by action_id.
        """
        action_map = {a.action_id: a for a in actions}
        
        # Build in-degrees and adjacency maps
        in_degree = {a.action_id: 0 for a in actions}
        adj: Dict[str, List[str]] = {a.action_id: [] for a in actions}

        for node_id, deps in dependency_graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[node_id] += 1
                    adj[dep].append(node_id)

        # Locate root nodes (in-degree == 0)
        roots = [nid for nid, deg in in_degree.items() if deg == 0]
        roots.sort()  # Stable deterministic tie-breaking by name

        ordered_actions: List[PartitionBaseAction] = []

        while roots:
            curr = roots.pop(0)
            if curr in action_map:
                ordered_actions.append(action_map[curr])

            children = adj.get(curr, [])
            children.sort()

            for child in children:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    roots.append(child)

            roots.sort()

        if len(ordered_actions) < len(actions):
            raise ValueError("Dependency cycle detected during partition scheduling topological sort.")

        return tuple(ordered_actions)
