"""
AKAAL Platform 5 — ConstraintDependencyGraph Engine

Builds DAGs across tables, constraints, indexes, views, and triggers to drive execution ordering.
"""

from typing import Dict, List, Optional

from akaal.schema.domain.changes import BaseSchemaChange
from akaal.schema.graph.node import SchemaNode
from akaal.schema.graph.sorter import TarjanTopologicalSorter


class ConstraintDependencyGraph:
    """Multi-object Constraint Dependency Graph."""

    def __init__(self) -> None:
        self.nodes: Dict[str, SchemaNode] = {}

    def add_change(self, change: BaseSchemaChange) -> SchemaNode:
        nid = change.change_id
        node = SchemaNode(node_id=nid, node_type=change.change_type.value, change_object=change)

        deps = change.analyze_dependencies()
        for dep in deps:
            node.add_dependency(dep.target)

        self.nodes[nid] = node
        return node

    def compute_execution_order(self) -> List[BaseSchemaChange]:
        sorted_nodes = TarjanTopologicalSorter.sort(self.nodes)
        return [node.change_object for node in sorted_nodes if node.change_object is not None]

    def compute_rollback_order(self) -> List[BaseSchemaChange]:
        exec_order = self.compute_execution_order()
        return list(reversed(exec_order))
