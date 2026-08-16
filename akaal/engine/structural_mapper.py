"""
AKAAL Engine — Canonical Structural Row & Document Remapper (P5.3).
Provides unified in-memory row structural remapping for bulk migration workers,
CDC event stream reconciliation, validation comparisons, and live preview rendering.
"""

from typing import List, Dict, Any, Optional


class StructuralRowMapper:
    """Canonical structural row and document remapping service."""

    @classmethod
    def remap_row(
        cls,
        source_object: str,
        row: Dict[str, Any],
        compiled_mapping: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Remaps a single source record to target structural identity:
        - Renames source columns to target columns according to compiled column_map.
        - Omits ignored columns.
        - Omits target default columns so database native DEFAULT populates.
        """
        if not isinstance(row, dict) or not compiled_mapping:
            return dict(row) if isinstance(row, dict) else row

        col_map = compiled_mapping.get("column_map", {}).get(source_object, {})
        ignored = set(compiled_mapping.get("ignored_columns", {}).get(source_object, []))
        defaults = set(compiled_mapping.get("target_defaults", {}).get(source_object, {}).keys())

        remapped = {}
        for src_col, val in row.items():
            if src_col in ignored:
                continue

            # Resolve target column name (defaulting to source name if unmapped)
            tgt_col = col_map.get(src_col, src_col)

            # Skip target defaults unless value is explicitly supplied
            if tgt_col in defaults and val is None:
                continue

            remapped[tgt_col] = val

        return remapped

    @classmethod
    def remap_batch(
        cls,
        source_object: str,
        rows: List[Dict[str, Any]],
        compiled_mapping: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Remaps a batch of source records to target structural identity."""
        if not compiled_mapping or not rows:
            return rows
        return [cls.remap_row(source_object, r, compiled_mapping) for r in rows]
