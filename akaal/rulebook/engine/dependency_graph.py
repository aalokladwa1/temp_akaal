"""
Akaal — Rule Dependency Graph
=============================
DAG dependency graph for Rule prerequisite relationships, topological sorting, and cycle detection.
"""

from collections import defaultdict, deque
from typing import Dict, List, Set, Any
from akaal.rulebook.models.rule import Rule


class DependencyGraph:
    """Dependency Graph for Rule prerequisite ordering and cycle detection."""

    def __init__(self) -> None:
        self._rules: Dict[str, Rule] = {}
        self._graph: Dict[str, List[str]] = defaultdict(list)
        self._in_degree: Dict[str, int] = defaultdict(int)

    def build(self, rules: List[Rule]) -> None:
        self._rules = {r.rule_id: r for r in rules}
        self._graph.clear()
        self._in_degree.clear()

        for r_id in self._rules:
            self._in_degree[r_id] = 0

        for r in rules:
            for prereq in r.prerequisites:
                if prereq in self._rules:
                    self._graph[prereq].append(r.rule_id)
                    self._in_degree[r.rule_id] += 1

    def detect_cycles(self) -> List[List[str]]:
        """Detect any circular prerequisite dependencies in the rule graph."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles: List[List[str]] = []

        def _dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self._graph.get(node, []):
                if neighbor not in visited:
                    _dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)

        for node in list(self._rules.keys()):
            if node not in visited:
                _dfs(node, [])

        return cycles

    def validate(self) -> List[str]:
        cycles = self.detect_cycles()
        errors = []
        for c in cycles:
            errors.append(f"Circular dependency detected in Rule Graph: {' -> '.join(c)}")
        return errors

    def topological_sort(self) -> List[Rule]:
        """Perform topological sort returning rules in valid dependency execution order."""
        in_deg = self._in_degree.copy()
        queue = deque([r_id for r_id, deg in in_deg.items() if deg == 0])
        ordered_ids: List[str] = []

        while queue:
            node = queue.popleft()
            ordered_ids.append(node)
            for neighbor in self._graph.get(node, []):
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered_ids) != len(self._rules):
            # If cycle detected, fallback to standard priority sorting
            return sorted(self._rules.values(), key=lambda r: r.priority)

        return [self._rules[r_id] for r_id in ordered_ids if r_id in self._rules]

    def affected_rules(self, rule_id: str) -> List[str]:
        """Return list of rule IDs that directly or indirectly depend on rule_id."""
        affected: Set[str] = set()
        queue = deque([rule_id])
        while queue:
            node = queue.popleft()
            for neighbor in self._graph.get(node, []):
                if neighbor not in affected:
                    affected.add(neighbor)
                    queue.append(neighbor)
        return list(affected)

    def dependency_tree(self, rule_id: str) -> Dict[str, Any]:
        """Return direct prerequisite dependencies of rule_id."""
        rule = self._rules.get(rule_id)
        if not rule:
            return {}
        return {
            "rule_id": rule_id,
            "prerequisites": rule.prerequisites,
            "dependent_rules": self._graph.get(rule_id, []),
        }
