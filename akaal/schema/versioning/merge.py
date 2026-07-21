"""
AKAAL Platform 5 — Version Merge Engine

Provides 3-way schema snapshot merging with structural conflict detection.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from akaal.schema.domain.identifiers import VersionID
from akaal.schema.versioning.graph import VersionDAG
from akaal.schema.versioning.snapshot import SchemaSnapshot


@dataclass
class MergeConflict:
    object_type: str
    object_name: str
    base_state: Any
    branch_a_state: Any
    branch_b_state: Any
    resolution_hint: str


@dataclass
class MergeResult:
    is_success: bool
    merged_tables: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[MergeConflict] = field(default_factory=list)


class VersionMergeEngine:
    """Performs 3-way merge between Base, Branch A, and Branch B schema snapshots."""

    def __init__(self, dag: VersionDAG) -> None:
        self.dag = dag

    def merge(self, snapshot_a: SchemaSnapshot, snapshot_b: SchemaSnapshot, base_snapshot: Optional[SchemaSnapshot] = None) -> MergeResult:
        if base_snapshot is None:
            lca_id = self.dag.find_lca(snapshot_a.version_id, snapshot_b.version_id)
            # Default empty if no LCA
            base_tables = {}
        else:
            base_tables = base_snapshot.tables

        tables_a = snapshot_a.tables
        tables_b = snapshot_b.tables
        all_table_keys = set(base_tables.keys()).union(tables_a.keys()).union(tables_b.keys())

        merged_tables = {}
        conflicts = []

        for tbl in all_table_keys:
            in_base = tbl in base_tables
            in_a = tbl in tables_a
            in_b = tbl in tables_b

            if in_a and in_b:
                if tables_a[tbl] == tables_b[tbl]:
                    merged_tables[tbl] = tables_a[tbl]
                elif in_base and tables_a[tbl] == base_tables[tbl]:
                    merged_tables[tbl] = tables_b[tbl]
                elif in_base and tables_b[tbl] == base_tables[tbl]:
                    merged_tables[tbl] = tables_a[tbl]
                else:
                    conflicts.append(
                        MergeConflict(
                            object_type="TABLE",
                            object_name=tbl,
                            base_state=base_tables.get(tbl),
                            branch_a_state=tables_a[tbl],
                            branch_b_state=tables_b[tbl],
                            resolution_hint="Manual structural reconciliation required for conflicting table changes.",
                        )
                    )
            elif in_a and not in_b:
                if in_base and base_tables[tbl] != tables_a[tbl]:
                    conflicts.append(
                        MergeConflict(
                            object_type="TABLE",
                            object_name=tbl,
                            base_state=base_tables.get(tbl),
                            branch_a_state=tables_a[tbl],
                            branch_b_state=None,
                            resolution_hint="Table modified in Branch A but dropped in Branch B.",
                        )
                    )
                elif not in_base:
                    merged_tables[tbl] = tables_a[tbl]
            elif in_b and not in_a:
                if in_base and base_tables[tbl] != tables_b[tbl]:
                    conflicts.append(
                        MergeConflict(
                            object_type="TABLE",
                            object_name=tbl,
                            base_state=base_tables.get(tbl),
                            branch_a_state=None,
                            branch_b_state=tables_b[tbl],
                            resolution_hint="Table dropped in Branch A but modified in Branch B.",
                        )
                    )
                elif not in_base:
                    merged_tables[tbl] = tables_b[tbl]

        return MergeResult(
            is_success=len(conflicts) == 0,
            merged_tables=merged_tables,
            conflicts=conflicts,
        )
