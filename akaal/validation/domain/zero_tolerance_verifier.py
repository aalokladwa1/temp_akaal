"""
AKAAL Zero-Tolerance Parity Verifier
===================================
Enforces strict 100.0000% mathematical equivalence between source and target schemas.
Performs row-by-row SHA-256 canonical hashing and identifies exact delta discrepancies
(missing PKs, corrupted PKs, extra PKs) for targeted in-place self-healing.
"""

from dataclasses import dataclass, field
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

from akaal.validation.domain.canonical_checksum import canonical_hash_row

logger = logging.getLogger("akaal.validation.zero_tolerance")


@dataclass
class ZeroToleranceVerificationResult:
    """Dataclass encapsulating zero-tolerance parity verification metrics."""
    table_name: str
    source_row_count: int
    target_row_count: int
    exact_parity_percentage: float
    zero_tolerance_satisfied: bool
    missing_pks: List[Any] = field(default_factory=list)
    corrupted_pks: List[Any] = field(default_factory=list)
    extra_pks: List[Any] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


class ZeroToleranceParityVerifier:
    """
    Absolute Zero-Tolerance Data Equivalence Verifier.
    Performs physical row-by-row canonical SHA-256 hash comparison across source
    and target tables to ensure 100.0000% exact parity with zero data loss or drift.
    """

    def verify_table_parity(
        self,
        table_name: str,
        source_records: List[Dict[str, Any]],
        target_records: List[Dict[str, Any]],
        primary_key_col: str = "id"
    ) -> ZeroToleranceVerificationResult:
        """
        Compares source and target record sets row-by-row using canonical SHA-256 hashing.
        Returns a ZeroToleranceVerificationResult detailing exact parity percentage and delta PKs.
        """
        issues: List[str] = []
        source_count = len(source_records)
        target_count = len(target_records)

        # Index source records by PK and compute canonical row hashes
        source_map: Dict[Any, Tuple[Dict[str, Any], str]] = {}
        for idx, rec in enumerate(source_records):
            pk_val = rec.get(primary_key_col, idx)
            chash = canonical_hash_row(rec)
            source_map[pk_val] = (rec, chash)

        # Index target records by PK and compute canonical row hashes
        target_map: Dict[Any, Tuple[Dict[str, Any], str]] = {}
        for idx, rec in enumerate(target_records):
            pk_val = rec.get(primary_key_col, idx)
            chash = canonical_hash_row(rec)
            target_map[pk_val] = (rec, chash)

        source_pks: Set[Any] = set(source_map.keys())
        target_pks: Set[Any] = set(target_map.keys())

        missing_pks = sorted(list(source_pks - target_pks), key=lambda x: str(x))
        extra_pks = sorted(list(target_pks - source_pks), key=lambda x: str(x))

        # Check for corrupted rows (PK present in both, but canonical SHA-256 hash differs)
        common_pks = source_pks.intersection(target_pks)
        corrupted_pks: List[Any] = []
        for pk in common_pks:
            _, s_hash = source_map[pk]
            _, t_hash = target_map[pk]
            if s_hash != t_hash:
                corrupted_pks.append(pk)

        corrupted_pks = sorted(corrupted_pks, key=lambda x: str(x))

        if missing_pks:
            issues.append(f"Missing {len(missing_pks)} rows in target table '{table_name}': PKs {missing_pks[:5]}...")
        if extra_pks:
            issues.append(f"Found {len(extra_pks)} extra rows in target table '{table_name}': PKs {extra_pks[:5]}...")
        if corrupted_pks:
            issues.append(f"Found {len(corrupted_pks)} corrupted/mismatched rows in target table '{table_name}': PKs {corrupted_pks[:5]}...")

        # Calculate exact parity percentage
        total_eval_pks = source_pks.union(target_pks)
        total_pks_count = len(total_eval_pks)

        if total_pks_count == 0:
            parity_percentage = 100.0
            zero_tolerance_satisfied = True
        else:
            matching_pks_count = len(common_pks) - len(corrupted_pks)
            parity_percentage = round((matching_pks_count / float(source_count if source_count > 0 else total_pks_count)) * 100.0, 4)
            # Strict Zero Tolerance requirement: EXACTLY 100.0000% parity with zero issues
            zero_tolerance_satisfied = (
                source_count == target_count and
                len(missing_pks) == 0 and
                len(extra_pks) == 0 and
                len(corrupted_pks) == 0 and
                parity_percentage == 100.0
            )

        logger.info(
            f"[ZeroToleranceVerifier] Table '{table_name}': Parity={parity_percentage:.4f}%, "
            f"Satisfied={zero_tolerance_satisfied}, Missing={len(missing_pks)}, "
            f"Corrupted={len(corrupted_pks)}, Extra={len(extra_pks)}"
        )

        return ZeroToleranceVerificationResult(
            table_name=table_name,
            source_row_count=source_count,
            target_row_count=target_count,
            exact_parity_percentage=parity_percentage,
            zero_tolerance_satisfied=zero_tolerance_satisfied,
            missing_pks=missing_pks,
            corrupted_pks=corrupted_pks,
            extra_pks=extra_pks,
            issues=issues
        )
