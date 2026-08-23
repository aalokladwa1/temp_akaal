"""
akaalEngine.schema.dependency
=============================
Multi-domain dependency graph, cycle breaking, and deterministic topological sorter.
"""

from akaalEngine.schema.dependency.cycle_breaker import CycleBreaker
from akaalEngine.schema.dependency.graph import (
    DependencyEdge,
    DependencyNode,
    MultiDomainDependencyGraph,
)
from akaalEngine.schema.dependency.sorter import TopologicalSorter

__all__ = [
    "DependencyNode",
    "DependencyEdge",
    "MultiDomainDependencyGraph",
    "CycleBreaker",
    "TopologicalSorter",
]
