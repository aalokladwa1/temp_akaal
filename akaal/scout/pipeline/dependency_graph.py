"""
Akaal — Stage Dependency Graph
==============================
Topological sorting and dependency validation for Scout pipeline execution.
"""

from collections import defaultdict, deque
from typing import List, Dict, Set
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class StageDependencyGraph:
    """Dependency Graph for Scout pipeline stages."""

    @staticmethod
    def resolve_execution_order(stages: List[BaseDiscoveryStage]) -> List[BaseDiscoveryStage]:
        stage_map: Dict[str, BaseDiscoveryStage] = {s.stage_name: s for s in stages}
        in_degree: Dict[str, int] = {s.stage_name: 0 for s in stages}
        graph: Dict[str, List[str]] = defaultdict(list)

        for s in stages:
            for dep in s.dependencies:
                if dep in stage_map:
                    graph[dep].append(s.stage_name)
                    in_degree[s.stage_name] += 1

        queue = deque([s_name for s_name, deg in in_degree.items() if deg == 0])
        ordered_names: List[str] = []

        while queue:
            node = queue.popleft()
            ordered_names.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered_names) != len(stages):
            # Fallback to declared list order if circular dependency detected
            return list(stages)

        return [stage_map[name] for name in ordered_names]
