"""
AKAAL Schema Engine — Canonical Dependency Intelligence & Topological Planner
=============================================================================
Provides database-agnostic dependency graph construction, Tarjan cycle detection,
safe cycle breaking (deferred foreign key DDL), deterministic topological wave grouping,
and missing dependency analysis.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Dict, Any, List, Set, Optional, Tuple

from akaal.schema.domain.ddl_emitter import StructuredDDLArtifact
from akaal.schema.domain.models import CanonicalSchemaModel, CanonicalTable


class DependencyStatus(str, Enum):
    RESOLVED = "RESOLVED"
    EXTERNAL = "EXTERNAL"
    DEFERRED = "DEFERRED"
    MISSING = "MISSING"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class DependencyNode:
    """Canonical node in the schema dependency graph."""
    node_id: str
    object_type: str
    object_name: str
    schema_name: str
    artifact: Optional[StructuredDDLArtifact] = None
    dependencies: List[str] = field(default_factory=list)
    status: DependencyStatus = DependencyStatus.RESOLVED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "schema_name": self.schema_name,
            "dependencies": sorted(self.dependencies),
            "status": self.status.value,
        }


@dataclass
class ExecutionGroup:
    """Parallel-safe execution wave containing independent DDL artifacts."""
    group_index: int
    artifacts: List[StructuredDDLArtifact]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_index": self.group_index,
            "artifacts": [a.to_dict() for a in self.artifacts],
        }


@dataclass
class DependencyPlan:
    """Topological DDL execution plan produced by CanonicalDependencyPlanner."""
    execution_groups: List[ExecutionGroup]
    deferred_artifacts: List[StructuredDDLArtifact]
    missing_dependencies: List[str]
    detected_cycles: List[List[str]]
    is_valid: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_groups": [g.to_dict() for g in self.execution_groups],
            "deferred_artifacts": [a.to_dict() for a in self.deferred_artifacts],
            "missing_dependencies": sorted(self.missing_dependencies),
            "detected_cycles": self.detected_cycles,
            "is_valid": self.is_valid,
        }


class CanonicalDependencyPlanner:
    """Canonical Dependency Intelligence Authority."""

    @classmethod
    def plan_ddl_execution(
        cls, artifacts: List[StructuredDDLArtifact], external_tables: Optional[Set[str]] = None
    ) -> DependencyPlan:
        """Transform StructuredDDLArtifacts into a deterministic, cycle-safe dependency plan."""
        ext_tables = external_tables or set()

        nodes: Dict[str, DependencyNode] = {}
        deferred_artifacts: List[StructuredDDLArtifact] = []
        table_artifacts: Dict[str, StructuredDDLArtifact] = {}
        all_table_names: Set[str] = set()

        # Step 1: Collect object names and identify candidate deferrable FKs
        for art in artifacts:
            key = f"{art.schema_name.lower()}.{art.object_name.lower()}"
            if art.object_type == "TABLE":
                all_table_names.add(key)
                table_artifacts[key] = art

        # Step 2: Separate Foreign Key artifacts into deferred set if cycle or self-reference exists
        clean_artifacts: List[StructuredDDLArtifact] = []
        for art in artifacts:
            if art.object_type == "FOREIGN_KEY":
                parent_tbl = art.schema_name.lower() + "." + art.object_name.lower()
                ref_tbls = [d.lower() for d in art.dependencies if d.lower() != art.object_name.lower()]

                # Check self-reference or candidate cycle
                is_self_ref = any(d.lower() == art.object_name.lower() for d in art.dependencies)
                if is_self_ref or len(ref_tbls) > 0:
                    deferred_artifacts.append(art)
                    continue
            clean_artifacts.append(art)

        # Step 3: Build Node Graph
        for art in clean_artifacts:
            node_id = f"{art.object_type}:{art.schema_name.lower()}.{art.object_name.lower()}"
            deps = []
            for dep in art.dependencies:
                dep_key = dep.lower()
                if "." not in dep_key:
                    dep_key = f"{art.schema_name.lower()}.{dep_key}"
                deps.append(f"TABLE:{dep_key}")

            nodes[node_id] = DependencyNode(
                node_id=node_id,
                object_type=art.object_type,
                object_name=art.object_name,
                schema_name=art.schema_name,
                artifact=art,
                dependencies=deps,
            )

        # Step 4: Tarjan / DFS Cycle Detection and Wave Grouping
        visited: Set[str] = set()
        visiting: Set[str] = set()
        order: List[str] = []
        detected_cycles: List[List[str]] = []
        missing_deps: List[str] = []

        def dfs(nid: str, path: List[str]) -> None:
            if nid in visiting:
                cycle_slice = path[path.index(nid):]
                detected_cycles.append(cycle_slice)
                return
            if nid not in visited:
                visiting.add(nid)
                path.append(nid)
                if nid in nodes:
                    node = nodes[nid]
                    for dep in node.dependencies:
                        if dep in nodes:
                            dfs(dep, path)
                        else:
                            # Dependency target not in clean nodes
                            dep_obj = dep.split(":")[-1]
                            if dep_obj not in all_table_names and dep_obj not in ext_tables:
                                missing_deps.append(dep_obj)
                visiting.remove(nid)
                path.pop()
                visited.add(nid)
                order.append(nid)

        # Sort node keys deterministically before DFS
        for nid in sorted(nodes.keys()):
            if nid not in visited:
                dfs(nid, [])

        # Step 5: Assign Execution Wave Groups deterministically
        group_map: Dict[str, int] = {}
        for nid in order:
            max_dep_group = -1
            if nid in nodes:
                for dep in nodes[nid].dependencies:
                    if dep in group_map:
                        max_dep_group = max(max_dep_group, group_map[dep])
            group_map[nid] = max_dep_group + 1

        waves: Dict[int, List[StructuredDDLArtifact]] = {}
        for nid in order:
            if nid in nodes and nodes[nid].artifact:
                grp_idx = group_map[nid]
                if grp_idx not in waves:
                    waves[grp_idx] = []
                waves[grp_idx].append(nodes[nid].artifact)

        execution_groups = []
        for idx in sorted(waves.keys()):
            # Sort artifacts in wave deterministically
            sorted_arts = sorted(waves[idx], key=lambda a: (a.schema_name.lower(), a.object_name.lower(), a.object_type))
            execution_groups.append(ExecutionGroup(group_index=idx, artifacts=sorted_arts))

        # Sort deferred artifacts deterministically
        deferred_artifacts = sorted(deferred_artifacts, key=lambda a: (a.schema_name.lower(), a.object_name.lower(), a.object_type))

        return DependencyPlan(
            execution_groups=execution_groups,
            deferred_artifacts=deferred_artifacts,
            missing_dependencies=sorted(list(set(missing_deps))),
            detected_cycles=detected_cycles,
            is_valid=(len(missing_deps) == 0),
        )
