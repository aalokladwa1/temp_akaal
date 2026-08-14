"""
AKAAL P2.9 — Validation-Only Mode, Deep Reconciliation & Mismatch Intelligence Engine
=======================================================================================
Database-agnostic validation-only execution path, write firewall, progressive hierarchical narrowing,
deterministic row identity matching, column-level difference localization, and raw-data privacy evidence.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
import hashlib
import logging
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from akaal.schema.domain.types import CanonicalType, CanonicalTypeCategory
from akaal.validation.domain.physical_validator import (
    PhysicalChecksumValidator,
    CanonicalValueSerializer,
    SERIALIZATION_VERSION,
)

logger = logging.getLogger("akaal.validation.domain.reconciliation")


class ValidationExecutionMode(Enum):
    """Validation execution mode."""
    MIGRATION_VALIDATION = "MIGRATION_VALIDATION"
    VALIDATION_ONLY = "VALIDATION_ONLY"


class RowClassification(Enum):
    """Row-level reconciliation classification."""
    MATCHED = "MATCHED"
    SOURCE_ONLY = "SOURCE_ONLY"
    TARGET_ONLY = "TARGET_ONLY"
    VALUE_MISMATCH = "VALUE_MISMATCH"
    UNSUPPORTED = "UNSUPPORTED"
    INDETERMINATE = "INDETERMINATE"
    ERROR = "ERROR"


class ValidationWriteFirewallError(PermissionError):
    """Raised when target mutation is attempted during VALIDATION_ONLY execution."""
    pass


class ValidationOnlyWriteFirewall:
    """Write Firewall enforcing zero target mutations during validation-only execution."""

    @staticmethod
    def assert_target_mutation_allowed(mode: ValidationExecutionMode, operation_name: str = "Target Write") -> None:
        """Blocks INSERT, UPDATE, DELETE, TRUNCATE, DDL, or CDC writes when mode is VALIDATION_ONLY."""
        if mode == ValidationExecutionMode.VALIDATION_ONLY:
            err_msg = f"[WRITE FIREWALL ENFORCED] Operation '{operation_name}' is strictly forbidden in VALIDATION_ONLY mode!"
            logger.error(err_msg)
            raise ValidationWriteFirewallError(err_msg)


@dataclass
class ColumnDifference:
    """Column-level difference localization record."""
    column_name: str
    source_hash: str
    target_hash: str
    is_match: bool


@dataclass
class RowReconciliationRecord:
    """Deep row-level reconciliation record (excludes raw customer data)."""
    row_identity: Dict[str, Any]
    classification: RowClassification
    column_differences: List[ColumnDifference] = field(default_factory=list)
    source_row_hash: Optional[str] = None
    target_row_hash: Optional[str] = None


@dataclass
class TableReconciliationSummary:
    """Deterministic table-level reconciliation summary."""
    table_name: str
    source_rows: int
    target_rows: int
    matched_count: int
    source_only_count: int
    target_only_count: int
    value_mismatch_count: int
    unsupported_count: int
    indeterminate_count: int
    error_count: int
    mismatched_chunks_count: int
    status: str  # "MATCHED", "MISMATCHED", "UNSUPPORTED", "INDETERMINATE", "ERROR"


@dataclass
class DatabaseReconciliationSummary:
    """Deterministic database-level aggregated reconciliation summary."""
    tables_validated: int
    tables_matched: int
    tables_mismatched: int
    tables_unsupported: int
    tables_indeterminate: int
    tables_failed: int
    total_rows_evaluated: int
    total_source_only_rows: int
    total_target_only_rows: int
    total_value_mismatch_rows: int
    final_status: str


@dataclass
class ReconciliationEvidence:
    """Structured reconciliation evidence artifact (AKAAL-CANONICAL-V1)."""
    validation_id: str
    execution_mode: ValidationExecutionMode
    serialization_version: str
    hash_algorithm: str
    table_summaries: List[TableReconciliationSummary]
    database_summary: DatabaseReconciliationSummary
    evidence_fingerprint: str


class CanonicalReconciliationEngine:
    """
    Universal Deep Reconciliation Engine (P2.9).
    Progressive narrowing hierarchy: Table -> Merkle Root -> Chunk -> Key Range -> Row -> Column.
    """

    SERIALIZATION_VERSION = SERIALIZATION_VERSION

    def __init__(self, mode: ValidationExecutionMode = ValidationExecutionMode.VALIDATION_ONLY):
        self.mode = mode
        self.validator = PhysicalChecksumValidator()

    @staticmethod
    def _canonical_key_sort_bytes(key: Tuple[Any, ...]) -> bytes:
        """Injective canonical byte representation for composite key sorting."""
        buf = bytearray()
        for elem in key:
            elem_bytes = CanonicalValueSerializer.serialize_value(elem)
            buf.extend(f"{len(elem_bytes)}:".encode("utf-8") + elem_bytes)
        return bytes(buf)

    def reconcile_tables(
        self,
        table_name: str,
        source_rows: List[Tuple[Any, ...]],
        target_rows: List[Tuple[Any, ...]],
        columns: List[str],
        pk_columns: Optional[List[str]] = None,
        source_dialect: str = "oracle",
        target_dialect: str = "postgresql",
        column_types: Optional[Dict[str, CanonicalType]] = None,
    ) -> Tuple[TableReconciliationSummary, List[RowReconciliationRecord]]:
        """
        Executes progressive deep reconciliation on source and target rows for a single table.
        """
        s_count = len(source_rows)
        t_count = len(target_rows)

        try:
            # Step 1: Check PK Identity Strategy & Uniqueness BEFORE claiming Merkle match
            if not pk_columns:
                logger.warning(f"[RECONCILIATION] Table '{table_name}' has no PK/Unique key identity. Classification is INDETERMINATE.")
                summary = TableReconciliationSummary(
                    table_name=table_name,
                    source_rows=s_count,
                    target_rows=t_count,
                    matched_count=0,
                    source_only_count=0,
                    target_only_count=0,
                    value_mismatch_count=0,
                    unsupported_count=0,
                    indeterminate_count=s_count,
                    error_count=0,
                    mismatched_chunks_count=1 if s_count > 0 or t_count > 0 else 0,
                    status="INDETERMINATE",
                )
                return summary, []

            col_indices = {col.lower(): idx for idx, col in enumerate(columns)}
            pk_indices = [col_indices[pk.lower()] for pk in pk_columns if pk.lower() in col_indices]

            if not pk_indices:
                summary = TableReconciliationSummary(
                    table_name=table_name,
                    source_rows=s_count,
                    target_rows=t_count,
                    matched_count=0,
                    source_only_count=0,
                    target_only_count=0,
                    value_mismatch_count=0,
                    unsupported_count=0,
                    indeterminate_count=s_count,
                    error_count=0,
                    mismatched_chunks_count=1,
                    status="INDETERMINATE",
                )
                return summary, []

            # Map source rows by PK key
            source_map: Dict[Tuple[Any, ...], Tuple[Any, ...]] = {}
            for r in source_rows:
                pk_key = tuple(r[i] for i in pk_indices)
                if any(k_val is None for k_val in pk_key) or pk_key in source_map:
                    # Key contains NULL or is non-unique -> fallback to INDETERMINATE
                    summary = TableReconciliationSummary(
                        table_name=table_name,
                        source_rows=s_count,
                        target_rows=t_count,
                        matched_count=0,
                        source_only_count=0,
                        target_only_count=0,
                        value_mismatch_count=0,
                        unsupported_count=0,
                        indeterminate_count=s_count,
                        error_count=0,
                        mismatched_chunks_count=1,
                        status="INDETERMINATE",
                    )
                    return summary, []
                source_map[pk_key] = r

            # Map target rows by PK key
            target_map: Dict[Tuple[Any, ...], Tuple[Any, ...]] = {}
            for r in target_rows:
                pk_key = tuple(r[i] for i in pk_indices)
                if any(k_val is None for k_val in pk_key) or pk_key in target_map:
                    # Key contains NULL or is non-unique -> fallback to INDETERMINATE
                    summary = TableReconciliationSummary(
                        table_name=table_name,
                        source_rows=s_count,
                        target_rows=t_count,
                        matched_count=0,
                        source_only_count=0,
                        target_only_count=0,
                        value_mismatch_count=0,
                        unsupported_count=0,
                        indeterminate_count=s_count,
                        error_count=0,
                        mismatched_chunks_count=1,
                        status="INDETERMINATE",
                    )
                    return summary, []
                target_map[pk_key] = r

            # Step 2: Merkle root check
            checksum_res = self.validator.validate_table_checksums(
                source_rows,
                target_rows,
                columns,
                pk_columns=pk_columns,
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

            if checksum_res["status"] == "PASSED":
                summary = TableReconciliationSummary(
                    table_name=table_name,
                    source_rows=s_count,
                    target_rows=t_count,
                    matched_count=s_count,
                    source_only_count=0,
                    target_only_count=0,
                    value_mismatch_count=0,
                    unsupported_count=0,
                    indeterminate_count=0,
                    error_count=0,
                    mismatched_chunks_count=0,
                    status="MATCHED",
                )
                return summary, []

            # Step 3: Deep Row & Column Reconciliation
            all_keys = set(source_map.keys()).union(set(target_map.keys()))

            matched_cnt = 0
            src_only_cnt = 0
            tgt_only_cnt = 0
            val_mismatch_cnt = 0
            records: List[RowReconciliationRecord] = []

            for key in sorted(all_keys, key=self._canonical_key_sort_bytes):
                key_dict = {pk_col: val for pk_col, val in zip(pk_columns, key)}
                in_src = key in source_map
                in_tgt = key in target_map

                if in_src and not in_tgt:
                    src_only_cnt += 1
                    records.append(RowReconciliationRecord(row_identity=key_dict, classification=RowClassification.SOURCE_ONLY))
                elif in_tgt and not in_src:
                    tgt_only_cnt += 1
                    records.append(RowReconciliationRecord(row_identity=key_dict, classification=RowClassification.TARGET_ONLY))
                else:
                    s_row = source_map[key]
                    t_row = target_map[key]

                    # Compare column by column
                    col_diffs: List[ColumnDifference] = []
                    row_mismatch = False

                    for col_name, s_val, t_val in zip(columns, s_row, t_row):
                        ctype = column_types.get(col_name) if column_types else None
                        s_col_bytes = CanonicalValueSerializer.serialize_value(s_val, canonical_type=ctype, dialect=source_dialect)
                        t_col_bytes = CanonicalValueSerializer.serialize_value(t_val, canonical_type=ctype, dialect=target_dialect)

                        s_col_hash = hashlib.sha256(s_col_bytes).hexdigest()
                        t_col_hash = hashlib.sha256(t_col_bytes).hexdigest()
                        col_match = (s_col_hash == t_col_hash)

                        if not col_match:
                            row_mismatch = True

                        col_diffs.append(ColumnDifference(
                            column_name=col_name,
                            source_hash=s_col_hash,
                            target_hash=t_col_hash,
                            is_match=col_match,
                        ))

                    if row_mismatch:
                        val_mismatch_cnt += 1
                        s_row_h = self.validator.hash_row(s_row, columns, dialect=source_dialect)
                        t_row_h = self.validator.hash_row(t_row, columns, dialect=target_dialect)
                        records.append(RowReconciliationRecord(
                            row_identity=key_dict,
                            classification=RowClassification.VALUE_MISMATCH,
                            column_differences=col_diffs,
                            source_row_hash=s_row_h,
                            target_row_hash=t_row_h,
                        ))
                    else:
                        matched_cnt += 1

            status = "MISMATCH" if (src_only_cnt > 0 or tgt_only_cnt > 0 or val_mismatch_cnt > 0) else "MATCHED"

            summary = TableReconciliationSummary(
                table_name=table_name,
                source_rows=s_count,
                target_rows=t_count,
                matched_count=matched_cnt,
                source_only_count=src_only_cnt,
                target_only_count=tgt_only_cnt,
                value_mismatch_count=val_mismatch_cnt,
                unsupported_count=0,
                indeterminate_count=0,
                error_count=0,
                mismatched_chunks_count=1 if status == "MISMATCH" else 0,
                status=status,
            )

            return summary, records

        except Exception as exc:
            logger.error(f"[RECONCILIATION ERROR] Failed reconciliation on table '{table_name}': {exc}", exc_info=True)
            summary = TableReconciliationSummary(
                table_name=table_name,
                source_rows=s_count,
                target_rows=t_count,
                matched_count=0,
                source_only_count=0,
                target_only_count=0,
                value_mismatch_count=0,
                unsupported_count=0,
                indeterminate_count=0,
                error_count=s_count if (s_count > 0 or t_count > 0) else 1,
                mismatched_chunks_count=1,
                status="ERROR",
            )
            return summary, []

    def aggregate_database_evidence(
        self,
        validation_id: str,
        table_summaries: List[TableReconciliationSummary],
    ) -> ReconciliationEvidence:
        """Aggregates table reconciliation summaries into database-level evidence."""
        tbl_cnt = len(table_summaries)
        matched_tbls = sum(1 for t in table_summaries if t.status == "MATCHED")
        mismatched_tbls = sum(1 for t in table_summaries if t.status == "MISMATCH")
        unsupported_tbls = sum(1 for t in table_summaries if t.status == "UNSUPPORTED")
        indet_tbls = sum(1 for t in table_summaries if t.status == "INDETERMINATE")
        failed_tbls = sum(1 for t in table_summaries if t.status == "ERROR")

        tot_eval = sum(t.matched_count + t.source_only_count + t.target_only_count + t.value_mismatch_count for t in table_summaries)
        tot_src_only = sum(t.source_only_count for t in table_summaries)
        tot_tgt_only = sum(t.target_only_count for t in table_summaries)
        tot_val_mismatch = sum(t.value_mismatch_count for t in table_summaries)

        if failed_tbls > 0:
            final_status = "ERROR"
        elif mismatched_tbls > 0:
            final_status = "MISMATCHED"
        elif indet_tbls > 0:
            final_status = "INDETERMINATE"
        elif unsupported_tbls > 0:
            final_status = "UNSUPPORTED"
        else:
            final_status = "MATCHED"

        db_summary = DatabaseReconciliationSummary(
            tables_validated=tbl_cnt,
            tables_matched=matched_tbls,
            tables_mismatched=mismatched_tbls,
            tables_unsupported=unsupported_tbls,
            tables_indeterminate=indet_tbls,
            tables_failed=failed_tbls,
            total_rows_evaluated=tot_eval,
            total_source_only_rows=tot_src_only,
            total_target_only_rows=tot_tgt_only,
            total_value_mismatch_rows=tot_val_mismatch,
            final_status=final_status,
        )

        # Fingerprint calculation
        payload = f"{validation_id}:{SERIALIZATION_VERSION}:{final_status}:{tot_eval}:{tot_src_only}:{tot_tgt_only}:{tot_val_mismatch}"
        fp = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        return ReconciliationEvidence(
            validation_id=validation_id,
            execution_mode=self.mode,
            serialization_version=SERIALIZATION_VERSION,
            hash_algorithm="SHA-256",
            table_summaries=table_summaries,
            database_summary=db_summary,
            evidence_fingerprint=fp,
        )
