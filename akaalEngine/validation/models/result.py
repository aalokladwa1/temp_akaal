"""
akaalEngine.validation.models.result
====================================
ValidationResult DTO and VALIDATION_GATE models for Authority #11.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationGateStatus(str, Enum):
    """Fact-based state of VALIDATION_GATE evaluation."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    WITHHELD = "WITHHELD"


@dataclass
class DisputedRecord:
    """Detailed record of a single row/document reconciliation mismatch."""
    key_values: Dict[str, Any]
    reason: str
    source_value: Optional[Dict[str, Any]] = None
    target_value: Optional[Dict[str, Any]] = None
    expected_value: Optional[Dict[str, Any]] = None


@dataclass
class PartitionValidationResult:
    """Validation result for a single bounded partition."""
    partition_id: str
    rows_expected: int
    rows_validated: int
    matched: bool
    source_fingerprint: str
    target_fingerprint: str
    mismatched_keys: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationResult:
    """
    Canonical machine-readable result DTO for Authority #11 (VAL-005).
    Exposes full quantitative facts, gate evaluation status, and execution metrics.
    """
    validation_run_id: str
    migration_id: str
    table_name: str
    status: str  # SUCCESS, FAILED, CANCELLED
    proof_scope: str  # FULL, PARTITIONED_FULL, SAMPLED, UNPROVEN
    validation_gate: ValidationGateStatus
    objects_expected: int = 1
    objects_validated: int = 1
    rows_expected: int = 0
    rows_validated: int = 0
    rows_matched: int = 0
    rows_mismatched: int = 0
    rows_missing: int = 0
    rows_extra: int = 0
    duplicates: int = 0
    schema_mismatches: int = 0
    partitions_total: int = 0
    partitions_matched: int = 0
    partitions_mismatched: int = 0
    source_boundary: Optional[str] = None
    target_boundary: Optional[str] = None
    cdc_boundary_position: Optional[str] = None
    technical_cutover_ready: bool = False
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_sec: float = 0.0
    disputed_records: List[DisputedRecord] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_run_id": self.validation_run_id,
            "migration_id": self.migration_id,
            "table_name": self.table_name,
            "status": self.status,
            "proof_scope": self.proof_scope,
            "validation_gate": self.validation_gate.value,
            "objects_expected": self.objects_expected,
            "objects_validated": self.objects_validated,
            "rows_expected": self.rows_expected,
            "rows_validated": self.rows_validated,
            "rows_matched": self.rows_matched,
            "rows_mismatched": self.rows_mismatched,
            "rows_missing": self.rows_missing,
            "rows_extra": self.rows_extra,
            "duplicates": self.duplicates,
            "schema_mismatches": self.schema_mismatches,
            "partitions_total": self.partitions_total,
            "partitions_matched": self.partitions_matched,
            "partitions_mismatched": self.partitions_mismatched,
            "source_boundary": self.source_boundary,
            "target_boundary": self.target_boundary,
            "cdc_boundary_position": self.cdc_boundary_position,
            "technical_cutover_ready": self.technical_cutover_ready,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_sec": self.duration_sec,
            "errors": list(self.errors),
        }
