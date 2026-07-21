"""
AKAAL Platform 5 — SchemaComparator Engine

Compares source vs target schema snapshots to identify added, removed, and modified schema objects.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from akaal.schema.versioning.snapshot import SchemaSnapshot


@dataclass
class SchemaDiff:
    added_objects: List[Dict[str, Any]] = field(default_factory=list)
    removed_objects: List[Dict[str, Any]] = field(default_factory=list)
    modified_objects: List[Dict[str, Any]] = field(default_factory=list)


class SchemaComparator:
    """Detailed structural comparator comparing two SchemaSnapshot objects."""

    def compare(self, source: SchemaSnapshot, target: SchemaSnapshot) -> SchemaDiff:
        diff = SchemaDiff()
        src_tables = source.tables
        tgt_tables = target.tables

        src_keys = set(src_tables.keys())
        tgt_keys = set(tgt_tables.keys())

        # Added tables in target
        for name in tgt_keys - src_keys:
            diff.added_objects.append({"type": "TABLE", "name": name, "definition": tgt_tables[name]})

        # Removed tables in target
        for name in src_keys - tgt_keys:
            diff.removed_objects.append({"type": "TABLE", "name": name, "definition": src_tables[name]})

        # Common tables to check for column / constraint modifications
        for name in src_keys.intersection(tgt_keys):
            src_t = src_tables[name]
            tgt_t = tgt_tables[name]
            if src_t != tgt_t:
                col_mods = self._compare_table_details(name, src_t, tgt_t)
                diff.modified_objects.append({
                    "type": "TABLE",
                    "name": name,
                    "src_definition": src_t,
                    "tgt_definition": tgt_t,
                    "modifications": col_mods,
                })

        return diff

    def _compare_table_details(self, table_name: str, src_t: Dict[str, Any], tgt_t: Dict[str, Any]) -> Dict[str, Any]:
        src_cols = {c["name"]: c for c in src_t.get("columns", [])}
        tgt_cols = {c["name"]: c for c in tgt_t.get("columns", [])}

        added_cols = [c for name, c in tgt_cols.items() if name not in src_cols]
        removed_cols = [c for name, c in src_cols.items() if name not in tgt_cols]
        modified_cols = []

        for cname in set(src_cols.keys()).intersection(tgt_cols.keys()):
            if src_cols[cname] != tgt_cols[cname]:
                modified_cols.append({
                    "column_name": cname,
                    "from": src_cols[cname],
                    "to": tgt_cols[cname],
                })

        return {
            "added_columns": added_cols,
            "removed_columns": removed_cols,
            "modified_columns": modified_cols,
        }
