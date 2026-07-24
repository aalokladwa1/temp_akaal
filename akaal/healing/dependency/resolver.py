"""DependencyResolver: Resolves execution order for multi-table repairs."""

from typing import List, Any
from akaal.healing.dependency.analyzer import DependencyAnalyzer


class DependencyResolver:
    """Resolves correct execution order for complex cascading repairs."""

    def __init__(self):
        self.analyzer = DependencyAnalyzer()

    def resolve_repair_order(self, issues: List[Any]) -> List[str]:
        """Return topological list of table names to repair in order."""
        graph = self.analyzer.build_graph_from_issues(issues)
        return graph.get_topological_order()
