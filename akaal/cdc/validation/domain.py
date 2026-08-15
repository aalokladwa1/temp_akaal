"""
AKAAL CDC Validation, Reconciliation & Remediation Domain Models.
================================================================
Strongly typed domain models for CDC-aware validation runs, consistent validation windows,
progressive validation levels (1-5), divergence classification, reconciliation records,
and safe remediation/repair actions.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import datetime

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.positions import CDCSourcePosition


class CDCValidationLevel(str, Enum):
    """Progressive validation levels for CDC streams."""
    LEVEL_1_ROW_COUNT = "LEVEL_1_ROW_COUNT"
    LEVEL_2_TABLE_CHECKSUM = "LEVEL_2_TABLE_CHECKSUM"
    LEVEL_3_ROW_RECONCILIATION = "LEVEL_3_ROW_RECONCILIATION"
    LEVEL_4_COLUMN_DIAGNOSIS = "LEVEL_4_COLUMN_DIAGNOSIS"
    LEVEL_5_POST_REPAIR_REVALIDATION = "LEVEL_5_POST_REPAIR_REVALIDATION"


class CDCValidationStatus(str, Enum):
    """Evaluation status for CDC validation runs."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    MATCHED = "MATCHED"
    MISMATCHED = "MISMATCHED"
    INDETERMINATE = "INDETERMINATE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class CDCDivergenceClass(str, Enum):
    """Classification of data divergence detected during validation."""
    NONE = "NONE"
    MISSING_TARGET_ROW = "MISSING_TARGET_ROW"
    EXTRA_TARGET_ROW = "EXTRA_TARGET_ROW"
    VALUE_MISMATCH = "VALUE_MISMATCH"
    COLUMN_COUNT_MISMATCH = "COLUMN_COUNT_MISMATCH"
    SCHEMA_VERSION_MISMATCH = "SCHEMA_VERSION_MISMATCH"
    UNAPPLIED_CDC_TX = "UNAPPLIED_CDC_TX"
    QUARANTINED_ENTITY_DIVERGENCE = "QUARANTINED_ENTITY_DIVERGENCE"
    CAUSAL_HOLE_DIVERGENCE = "CAUSAL_HOLE_DIVERGENCE"


class CDCRepairActionType(str, Enum):
    """Governed remediation/repair action classification."""
    REPLAY_TRANSACTION = "REPLAY_TRANSACTION"
    REAPPLY_SOURCE_VALUE = "REAPPLY_SOURCE_VALUE"
    REPAIR_MISSING_ROW = "REPAIR_MISSING_ROW"
    REMOVE_DUPLICATE = "REMOVE_DUPLICATE"
    MANUAL_GOVERNANCE_REQUIRED = "MANUAL_GOVERNANCE_REQUIRED"


class CDCRepairStatus(str, Enum):
    """Status of reconciliation repair execution."""
    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    REVALIDATED = "REVALIDATED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass
class CDCConsistentValidationWindow:
    """
    Consistency boundary for CDC validation.
    Ensures validation compares source and target at a logically frozen, consistent point.
    """
    source_position: str
    target_applied_position: str
    checkpoint_position: str
    schema_version: int = 1
    has_causal_holes: bool = False
    is_consistent: bool = True
    consistency_reason: str = "Consistent frozen position established"
    established_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCConsistentValidationWindow':
        return cls(**data)


@dataclass
class CDCTableValidationResult:
    """Table-level validation outcome."""
    table_name: str
    level: CDCValidationLevel
    status: CDCValidationStatus
    source_row_count: int = 0
    target_row_count: int = 0
    source_checksum: Optional[str] = None
    target_checksum: Optional[str] = None
    mismatch_count: int = 0
    divergence_classes: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["level"] = self.level.value if isinstance(self.level, Enum) else self.level
        res["status"] = self.status.value if isinstance(self.status, Enum) else self.status
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCTableValidationResult':
        d = dict(data)
        if "level" in d and isinstance(d["level"], str):
            d["level"] = CDCValidationLevel(d["level"])
        if "status" in d and isinstance(d["status"], str):
            d["status"] = CDCValidationStatus(d["status"])
        return cls(**d)


@dataclass
class CDCReconciliationRecord:
    """Detailed row-level reconciliation record for mismatch diagnosis."""
    reconciliation_id: str
    table_name: str
    entity_key_fingerprint: str
    mismatch_class: CDCDivergenceClass
    migration_id: Optional[str] = None
    run_id: Optional[str] = None
    source_fingerprint: Optional[str] = None
    target_fingerprint: Optional[str] = None
    first_seen_position: Optional[str] = None
    column_mismatches: List[str] = field(default_factory=list)
    resolution_state: str = "UNRESOLVED"
    repair_action: Optional[CDCRepairActionType] = None
    repair_status: CDCRepairStatus = CDCRepairStatus.PLANNED
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["mismatch_class"] = self.mismatch_class.value if isinstance(self.mismatch_class, Enum) else self.mismatch_class
        if self.repair_action:
            res["repair_action"] = self.repair_action.value if isinstance(self.repair_action, Enum) else self.repair_action
        res["repair_status"] = self.repair_status.value if isinstance(self.repair_status, Enum) else self.repair_status
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCReconciliationRecord':
        d = dict(data)
        if "mismatch_class" in d and isinstance(d["mismatch_class"], str):
            d["mismatch_class"] = CDCDivergenceClass(d["mismatch_class"])
        if "repair_action" in d and isinstance(d["repair_action"], str):
            d["repair_action"] = CDCRepairActionType(d["repair_action"])
        if "repair_status" in d and isinstance(d["repair_status"], str):
            d["repair_status"] = CDCRepairStatus(d["repair_status"])
        return cls(**d)


@dataclass
class CDCValidationRun:
    """Identity-bound CDC validation run model."""
    validation_run_id: str
    identity: CDCEventIdentity
    level: CDCValidationLevel
    status: CDCValidationStatus
    window: CDCConsistentValidationWindow
    tables_validated: List[CDCTableValidationResult] = field(default_factory=list)
    reconciliations: List[CDCReconciliationRecord] = field(default_factory=list)
    total_tables: int = 0
    matched_tables: int = 0
    mismatched_tables: int = 0
    indeterminate_tables: int = 0
    total_mismatches: int = 0
    reconciliation_completed: bool = False
    evidence_reference: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["identity"] = self.identity.to_dict()
        res["level"] = self.level.value if isinstance(self.level, Enum) else self.level
        res["status"] = self.status.value if isinstance(self.status, Enum) else self.status
        res["window"] = self.window.to_dict()
        res["tables_validated"] = [t.to_dict() for t in self.tables_validated]
        res["reconciliations"] = [r.to_dict() for r in self.reconciliations]
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDCValidationRun':
        d = dict(data)
        if "identity" in d and isinstance(d["identity"], dict):
            d["identity"] = CDCEventIdentity.from_dict(d["identity"])
        if "level" in d and isinstance(d["level"], str):
            d["level"] = CDCValidationLevel(d["level"])
        if "status" in d and isinstance(d["status"], str):
            d["status"] = CDCValidationStatus(d["status"])
        if "window" in d and isinstance(d["window"], dict):
            d["window"] = CDCConsistentValidationWindow.from_dict(d["window"])
        if "tables_validated" in d and isinstance(d["tables_validated"], list):
            d["tables_validated"] = [CDCTableValidationResult.from_dict(t) for t in d["tables_validated"]]
        if "reconciliations" in d and isinstance(d["reconciliations"], list):
            d["reconciliations"] = [CDCReconciliationRecord.from_dict(r) for r in d["reconciliations"]]
        return cls(**d)
