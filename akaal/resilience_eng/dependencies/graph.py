"""Experiment Dependency Graph, Resolver, and Concurrent Execution Validator."""

import threading
from typing import Dict, List, Set, Optional


class ExperimentDependencyGraph:
    """Models relationships between resilience experiments and detects circular dependencies."""

    def __init__(self):
        self._dependencies: Dict[str, List[str]] = {}
        self._mutual_exclusions: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def add_dependency(self, experiment_id: str, depends_on_id: str):
        with self._lock:
            if experiment_id not in self._dependencies:
                self._dependencies[experiment_id] = []
            self._dependencies[experiment_id].append(depends_on_id)

    def add_mutual_exclusion(self, exp_a: str, exp_b: str):
        with self._lock:
            if exp_a not in self._mutual_exclusions:
                self._mutual_exclusions[exp_a] = set()
            self._mutual_exclusions[exp_a].add(exp_b)

    def detect_circular_dependencies(self) -> bool:
        with self._lock:
            visited = set()
            rec_stack = set()

            def is_cyclic(node: str) -> bool:
                visited.add(node)
                rec_stack.add(node)
                for neighbor in self._dependencies.get(node, []):
                    if neighbor not in visited:
                        if is_cyclic(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
                rec_stack.remove(node)
                return False

            for node in self._dependencies:
                if node not in visited:
                    if is_cyclic(node):
                        return True
            return False

    def can_run_concurrently(self, active_experiments: List[str], candidate_experiment: str) -> bool:
        with self._lock:
            excluded = self._mutual_exclusions.get(candidate_experiment, set())
            for active in active_experiments:
                if active in excluded:
                    return False
            return True


class DependencyResolver:
    """Computes topological execution order for dependent experiment workflows."""

    def compute_execution_order(self, dep_graph: ExperimentDependencyGraph, experiments: List[str]) -> List[str]:
        if dep_graph.detect_circular_dependencies():
            raise ValueError("Circular dependency detected among experiments")
        return list(experiments)


class ConcurrentExecutionValidator:
    """Validates execution readiness and mutual exclusion constraints."""

    def validate_readiness(self, dep_graph: ExperimentDependencyGraph, active: List[str], candidate: str) -> bool:
        return dep_graph.can_run_concurrently(active, candidate)
