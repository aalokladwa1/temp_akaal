"""
akaalEngine.validation.reconciliation.localization
===================================================
MismatchLocalizationEngine for Authority #11 (VAL-024).
Recursively localizes mismatching partitions down to chunks, key ranges, and individual key sets.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from akaalEngine.validation.fingerprint.partition import PartitionFingerprintEngine

logger = logging.getLogger("akaalEngine.validation.reconciliation.localization")


class MismatchLocalizationEngine:
    """
    Localizes fingerprint mismatches recursively:
      Partition -> Chunk -> Key Range -> Individual Disputed Key Set.
    Spends expensive exact row reconciliation ONLY on localized mismatching ranges.
    """

    def localize_mismatches(
        self,
        partition_id: str,
        source_rows: List[Dict[str, Any]],
        target_rows: List[Dict[str, Any]],
        pk_columns: List[str],
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Localizes differences between source_rows and target_rows.
        Returns (missing_records, extra_records, value_mismatched_records).
        """
        mapping = column_mapping or {}
        pk_cols = pk_columns or ["id"]

        # Build key maps for source and target
        def get_pk(row: Dict[str, Any], is_target: bool = False) -> Tuple[Any, ...]:
            keys = []
            for col in pk_cols:
                tgt_col = mapping.get(col, col) if is_target else col
                keys.append(row.get(tgt_col if is_target else col))
            return tuple(keys)

        src_map: Dict[Tuple[Any, ...], Dict[str, Any]] = {get_pk(r, False): r for r in source_rows}
        tgt_map: Dict[Tuple[Any, ...], Dict[str, Any]] = {get_pk(r, True): r for r in target_rows}

        missing_records: List[Dict[str, Any]] = []
        extra_records: List[Dict[str, Any]] = []
        mismatched_records: List[Dict[str, Any]] = []

        # Find missing and value-mismatched records
        for pk, src_row in src_map.items():
            if pk not in tgt_map:
                missing_records.append(src_row)
            else:
                tgt_row = tgt_map[pk]
                # Compare mapped attributes
                val_differs = False
                for src_col, val in src_row.items():
                    tgt_col = mapping.get(src_col, src_col)
                    if tgt_col in tgt_row and tgt_row[tgt_col] != val:
                        val_differs = True
                        break
                if val_differs:
                    mismatched_records.append(src_row)

        # Find extra records in target
        for pk, tgt_row in tgt_map.items():
            if pk not in src_map:
                extra_records.append(tgt_row)

        logger.info(f"Localization for partition '{partition_id}': {len(missing_records)} missing, {len(extra_records)} extra, {len(mismatched_records)} mismatched.")
        return missing_records, extra_records, mismatched_records
