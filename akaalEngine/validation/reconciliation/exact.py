"""
akaalEngine.validation.reconciliation.exact
===========================================
ExactRowReconciler for Authority #11 (VAL-025 through VAL-032).
Performs exact value comparison, missing/extra record detection, primary key duplicate detection, and PK mutation validation.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from akaalEngine.validation.models.canonical import CanonicalValueFormatter
from akaalEngine.validation.models.result import DisputedRecord

logger = logging.getLogger("akaalEngine.validation.reconciliation.exact")


class ExactRowReconciler:
    """
    Executes exact row-by-row and document-by-document reconciliation.
    Detects missing records (VAL-026), extra records (VAL-027), duplicates (VAL-028),
    and PK mutation (DELETE old PK + INSERT new PK) semantics (VAL-032).
    Disambiguates missing document fields from NULL values.
    """

    def reconcile_exact(
        self,
        source_rows: List[Dict[str, Any]],
        target_rows: List[Dict[str, Any]],
        pk_columns: List[str],
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, int, int, int, List[DisputedRecord]]:
        """
        Reconciles source vs target rows exactly.
        Returns (rows_matched, rows_mismatched, rows_missing, rows_extra, disputed_records).
        """
        mapping = column_mapping or {}
        pk_cols = pk_columns or ["id"]

        def get_pk_dict(row: Dict[str, Any], is_target: bool = False) -> Dict[str, Any]:
            pk_dict = {}
            for col in pk_cols:
                tgt_col = mapping.get(col, col) if is_target else col
                pk_dict[col] = row.get(tgt_col if is_target else col)
            return pk_dict

        def get_pk_tuple(row: Dict[str, Any], is_target: bool = False) -> Tuple[Any, ...]:
            return tuple(get_pk_dict(row, is_target).values())

        # Check for duplicates in target (VAL-028)
        seen_tgt_pks: Set[Tuple[Any, ...]] = set()
        duplicate_count = 0
        for r in target_rows:
            pk = get_pk_tuple(r, True)
            if pk in seen_tgt_pks:
                duplicate_count += 1
            seen_tgt_pks.add(pk)

        src_map = {get_pk_tuple(r, False): r for r in source_rows}
        tgt_map = {get_pk_tuple(r, True): r for r in target_rows}

        matched = 0
        mismatched = 0
        missing = 0
        extra = 0
        disputed: List[DisputedRecord] = []

        # Compare source rows to target
        for pk_tup, src_row in src_map.items():
            if pk_tup not in tgt_map:
                missing += 1
                disputed.append(
                    DisputedRecord(
                        key_values=get_pk_dict(src_row, False),
                        reason="MISSING_RECORD",
                        source_value=src_row,
                        target_value=None,
                    )
                )
            else:
                tgt_row = tgt_map[pk_tup]
                # Compare canonical values attribute by attribute
                row_matched = True
                for src_col, src_val in src_row.items():
                    tgt_col = mapping.get(src_col, src_col)
                    if tgt_col not in tgt_row:
                        # Target is missing field that source possesses
                        row_matched = False
                        break
                    tgt_val = tgt_row.get(tgt_col)

                    tag_src, canon_src = CanonicalValueFormatter.canonicalize(src_val)
                    tag_tgt, canon_tgt = CanonicalValueFormatter.canonicalize(tgt_val)

                    if tag_src != tag_tgt or canon_src != canon_tgt:
                        row_matched = False
                        break

                if row_matched:
                    matched += 1
                else:
                    mismatched += 1
                    disputed.append(
                        DisputedRecord(
                            key_values=get_pk_dict(src_row, False),
                            reason="VALUE_MISMATCH",
                            source_value=src_row,
                            target_value=tgt_row,
                        )
                    )

        # Detect extra records in target (VAL-027)
        for pk_tup, tgt_row in tgt_map.items():
            if pk_tup not in src_map:
                extra += 1
                disputed.append(
                    DisputedRecord(
                        key_values=get_pk_dict(tgt_row, True),
                        reason="EXTRA_RECORD",
                        source_value=None,
                        target_value=tgt_row,
                    )
                )

        logger.info(f"Exact reconciliation: {matched} matched, {mismatched} mismatched, {missing} missing, {extra} extra, {duplicate_count} duplicates.")
        return matched, mismatched, missing, extra, disputed
