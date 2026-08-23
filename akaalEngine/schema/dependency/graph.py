"""
akaalEngine.schema.dependency.graph
===================================
Multi-domain semantic dependency graph across schemas, types, sequences, tables, constraints, views, and routines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

from akaalEngine.schema.models.schema import CanonicalSchemaModel


@dataclass(frozen=True)
class DependencyNode:
    """A single node in the multi-domain dependency graph."""
    node_id: str  # e.g. "table:public.orders", "sequence:public.order_seq"
    object_type: str  # SCHEMA, TYPE, SEQUENCE, TABLE, VIEW, ROUTINE, TRIGGER
    schema_name: str
    object_name: str
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True)
class DependencyEdge:
    """Directed edge from dependent node to prerequisite node (source depends on target)."""
    source_id: str
    target_id: str
    dependency_type: str = "HARD"  # HARD, FK_CIRCULAR, VIEW_REF, ROUTINE_REF


class MultiDomainDependencyGraph:
    """Constructs and manages the schema semantic dependency graph."""

    def __init__(self):
        self.nodes: Dict[str, DependencyNode] = {}
        self.edges: List[DependencyEdge] = []
        self.adj_list: Dict[str, Set[str]] = {}  # node -> set of prerequisites
        self.reverse_adj: Dict[str, Set[str]] = {}  # node -> set of dependents

    def add_node(self, node: DependencyNode) -> None:
        self.nodes[node.node_id] = node
        if node.node_id not in self.adj_list:
            self.adj_list[node.node_id] = set()
        if node.node_id not in self.reverse_adj:
            self.reverse_adj[node.node_id] = set()

    def add_edge(self, source_id: str, target_id: str, dep_type: str = "HARD") -> None:
        if source_id == target_id:
            # Self-referential loop (e.g. self-referencing FK)
            dep_type = "SELF_LOOP"
        edge = DependencyEdge(source_id=source_id, target_id=target_id, dependency_type=dep_type)
        self.edges.append(edge)
        if source_id in self.adj_list:
            self.adj_list[source_id].add(target_id)
        if target_id in self.reverse_adj:
            self.reverse_adj[target_id].add(source_id)

    @classmethod
    def build(cls, model: CanonicalSchemaModel) -> MultiDomainDependencyGraph:
        return cls.build_from_model(model)

    @classmethod
    def build_from_model(cls, model: CanonicalSchemaModel) -> MultiDomainDependencyGraph:
        graph = cls()

        # 1. Schemas
        for s in model.schemas:
            nid = f"schema:{s.schema_name}"
            graph.add_node(DependencyNode(node_id=nid, object_type="SCHEMA", schema_name=s.schema_name, object_name=s.schema_name))

        # 2. UDTs
        for u in model.udts:
            nid = f"type:{u.qualified_name}"
            graph.add_node(DependencyNode(node_id=nid, object_type="TYPE", schema_name=u.schema_name, object_name=u.name))
            if u.schema_name:
                graph.add_edge(nid, f"schema:{u.schema_name}")

        # 3. Sequences
        for seq in model.sequences:
            nid = f"sequence:{seq.qualified_name}"
            graph.add_node(DependencyNode(node_id=nid, object_type="SEQUENCE", schema_name=seq.schema_name, object_name=seq.name))
            if seq.schema_name:
                graph.add_edge(nid, f"schema:{seq.schema_name}")

        # 4. Tables
        for tbl in model.tables:
            t_id = f"table:{tbl.qualified_name}"
            graph.add_node(DependencyNode(node_id=t_id, object_type="TABLE", schema_name=tbl.schema_name, object_name=tbl.table_name))
            if tbl.schema_name:
                graph.add_edge(t_id, f"schema:{tbl.schema_name}")

            # FK dependencies
            for fk in tbl.foreign_keys:
                ref_tbl_id = f"table:{fk.referenced_schema}.{fk.referenced_table}"
                graph.add_edge(t_id, ref_tbl_id, dep_type="FOREIGN_KEY")

        # 5. Views
        for v in model.views:
            v_id = f"view:{v.qualified_name}"
            graph.add_node(DependencyNode(node_id=v_id, object_type="VIEW", schema_name=v.schema_name, object_name=v.view_name))
            if v.schema_name:
                graph.add_edge(v_id, f"schema:{v.schema_name}")
            for dep in v.dependencies:
                dep_id = f"table:{dep}" if ":" not in dep else dep
                graph.add_edge(v_id, dep_id, dep_type="VIEW_REF")

        # 6. Routines
        for r in model.routines:
            r_id = f"routine:{r.qualified_name}"
            graph.add_node(DependencyNode(node_id=r_id, object_type="ROUTINE", schema_name=r.schema_name, object_name=r.name))
            if r.schema_name:
                graph.add_edge(r_id, f"schema:{r.schema_name}")
            for dep in r.dependencies:
                dep_id = f"table:{dep}" if ":" not in dep else dep
                graph.add_edge(r_id, dep_id, dep_type="ROUTINE_REF")

        return graph
