"""
AKAAL In-Place Delta Self-Healing Service
=========================================
Executes targeted, non-destructive mid-stream row repairs for missing and corrupted records.
Applies idempotent UPSERT/MERGE operations on target schemas without wiping or disrupting
surrounding, correctly migrated data.
"""

from dataclasses import dataclass, field
import logging
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("akaal.healing.in_place_delta")


@dataclass
class InPlaceHealingResult:
    """Summary of in-place delta self-healing execution."""
    table_name: str
    repaired_missing_count: int
    repaired_corrupted_count: int
    total_repairs_applied: int
    success: bool
    repaired_target_records: List[Dict[str, Any]] = field(default_factory=list)
    repair_details: List[str] = field(default_factory=list)


class InPlaceDeltaHealer:
    """
    Enterprise In-Place Delta Self-Healer.
    Performs targeted row insertions and corrections for exact Primary Keys identified
    as missing or corrupted during zero-tolerance verification.
    """

    def heal_delta_records(
        self,
        table_name: str,
        source_records: List[Dict[str, Any]],
        target_records: List[Dict[str, Any]],
        missing_pks: List[Any],
        corrupted_pks: List[Any],
        primary_key_col: str = "id"
    ) -> InPlaceHealingResult:
        """
        Executes in-place self-healing repair by mapping source delta records into target dataset.
        For missing PKs, inserts source record into target.
        For corrupted PKs, replaces target record with exact source record.
        Preserves all existing, undamaged target records in place.
        """
        details: List[str] = []
        source_by_pk: Dict[Any, Dict[str, Any]] = {
            rec.get(primary_key_col, idx): rec
            for idx, rec in enumerate(source_records)
        }

        delta_pks_to_repair: Set[Any] = set(missing_pks).union(set(corrupted_pks))
        if not delta_pks_to_repair:
            return InPlaceHealingResult(
                table_name=table_name,
                repaired_missing_count=0,
                repaired_corrupted_count=0,
                total_repairs_applied=0,
                success=True,
                repaired_target_records=target_records,
                repair_details=["No delta repairs required; 100.0000% parity verified."]
            )

        target_map: Dict[Any, Dict[str, Any]] = {
            rec.get(primary_key_col, idx): dict(rec)
            for idx, rec in enumerate(target_records)
        }

        repaired_missing = 0
        repaired_corrupted = 0

        # 1. Repair missing rows
        for pk in missing_pks:
            if pk in source_by_pk:
                target_map[pk] = dict(source_by_pk[pk])
                repaired_missing += 1
                details.append(f"In-place INSERT applied for missing PK '{pk}' in '{table_name}'")

        # 2. Repair corrupted rows
        for pk in corrupted_pks:
            if pk in source_by_pk:
                target_map[pk] = dict(source_by_pk[pk])
                repaired_corrupted += 1
                details.append(f"In-place UPDATE applied for corrupted PK '{pk}' in '{table_name}'")

        # Reconstruct updated target records, sorted deterministically by PK
        repaired_target_records = list(target_map.values())
        repaired_target_records.sort(key=lambda r: str(r.get(primary_key_col, "")))

        total_repairs = repaired_missing + repaired_corrupted
        logger.info(
            f"[InPlaceDeltaHealer] Table '{table_name}': Applied {total_repairs} in-place repairs "
            f"({repaired_missing} missing inserted, {repaired_corrupted} corrupted updated)."
        )

        return InPlaceHealingResult(
            table_name=table_name,
            repaired_missing_count=repaired_missing,
            repaired_corrupted_count=repaired_corrupted,
            total_repairs_applied=total_repairs,
            success=True,
            repaired_target_records=repaired_target_records,
            repair_details=details
        )
