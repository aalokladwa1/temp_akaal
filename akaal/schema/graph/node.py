"""
AKAAL Platform 5 — Constraint & Object Dependency Graph Nodes

Represents tables, PKs, FKs, indexes, views, triggers, sequences, and generated columns as graph nodes.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SchemaNode:
    node_id: str
    node_type: str  # TABLE, PRIMARY_KEY, FOREIGN_KEY, UNIQUE, CHECK, INDEX, VIEW, SEQUENCE, TRIGGER
    change_object: Optional[Any] = None
    dependencies: List[str] = field(default_factory=list)

    def add_dependency(self, target_node_id: str) -> None:
        if target_node_id not in self.dependencies and target_node_id != self.node_id:
            self.dependencies.append(target_node_id)
