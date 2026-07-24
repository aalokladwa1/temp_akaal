"""DependencyAnalyzer: Discovers parent-child table FK and sequence dependencies."""

from typing import Dict, List, Any
from akaal.healing.dependency.graph import RepairDependencyGraph


class DependencyAnalyzer:
    """Discovers foreign key relationships and creates repair dependency graphs."""

    def build_graph_from_issues(self, issues: List[Any]) -> RepairDependencyGraph:
        """Construct dependency graph from validation issues."""
        graph = RepairDependencyGraph()
        for issue in issues:
            tbl = getattr(issue, "table_name", None)
            if tbl:
                graph.add_node(tbl)
                # Parent relationship check
                parent_tbl = getattr(issue, "metadata", {}).get("parent_table")
                if parent_tbl:
                    graph.add_dependency(parent_tbl, tbl)
        return graph
