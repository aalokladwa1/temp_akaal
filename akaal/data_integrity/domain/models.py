"""
AKAAL Platform 8 — Enterprise Data Integrity Domain Models.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from akaal.data_integrity.domain.enums import IntegrityStatus, ConsistencyMode


@dataclass(frozen=True)
class ConsistencyReport:
    report_id: str
    source_table: str
    target_table: str
    rows_compared: int
    mismatches_found: int
    status: IntegrityStatus
    mode: ConsistencyMode
    checksum_source: str
    checksum_target: str
    generated_at: str


@dataclass(frozen=True)
class TransactionBoundaryResult:
    transaction_id: str
    is_committed_consistently: bool
    uncommitted_row_count: int
    status: IntegrityStatus


@dataclass(frozen=True)
class ReferentialIntegrityResult:
    foreign_key_name: str
    parent_table: str
    child_table: str
    orphaned_records_count: int
    is_valid: bool
