from enum import Enum
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Tuple, Optional, Union, Dict, List, Any
from akaal.migration.models.partition import (
    CanonicalScalarValue,
    CanonicalRangeInterval,
    ObjectIdentity,
    PartitionDiagnostic,
    PartitionApproval
)

class PlanReadinessStatus(str, Enum):
    READY = "READY"
    READY_WITH_APPROVAL = "READY_WITH_APPROVAL"
    READY_WITH_BACKUP = "READY_WITH_BACKUP"
    RECONSTRUCTION_REQUIRED = "RECONSTRUCTION_REQUIRED"
    BLOCKED = "BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"

class DowntimeClassification(str, Enum):
    NONE = "NONE"
    METADATA_LOCK = "METADATA_LOCK"
    EXCLUSIVE_LOCK = "EXCLUSIVE_LOCK"
    OFFLINE = "OFFLINE"

class DataMovementClassification(str, Enum):
    NONE = "NONE"
    METADATA_ONLY = "METADATA_ONLY"
    BATCH_COPY = "BATCH_COPY"
    FULL_TABLE_COPY = "FULL_TABLE_COPY"

class ExecutionPolicy(str, Enum):
    STOP_ON_FAILURE = "STOP_ON_FAILURE"
    BEST_EFFORT = "BEST_EFFORT"
    CONTINUE_SAFE = "CONTINUE_SAFE"

class ActionRetryClassification(str, Enum):
    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    RETRY_WITH_BACKOFF = "RETRY_WITH_BACKOFF"

class ResourceLockType(str, Enum):
    SHARED = "SHARED"
    EXCLUSIVE = "EXCLUSIVE"

class LockCategory(str, Enum):
    DATABASE = "DATABASE"
    SCHEMA = "SCHEMA"
    TABLE = "TABLE"
    PARTITION_FUNCTION = "PARTITION_FUNCTION"
    PARTITION_SCHEME = "PARTITION_SCHEME"
    TABLESPACE = "TABLESPACE"
    FILEGROUP = "FILEGROUP"

@dataclass(frozen=True)
class ResourceLock:
    lock_type: ResourceLockType
    category: LockCategory
    resource_name: str

@dataclass(frozen=True)
class PartitionBaseAction:
    action_id: str
    action_type: str
    object_identity: ObjectIdentity
    source_dialect: str
    target_dialect: str
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    resource_locks: Tuple[ResourceLock, ...] = field(default_factory=tuple)
    validation_gates: Tuple[str, ...] = field(default_factory=tuple)
    idempotency_key: str = ""
    retry_class: ActionRetryClassification = ActionRetryClassification.NON_RETRYABLE
    approval_ids: Tuple[str, ...] = field(default_factory=tuple)
    backup_required: bool = False
    expected_postconditions: Tuple[str, ...] = field(default_factory=tuple)
    rollback_action_id: Optional[str] = None
    fingerprint: str = ""
    diagnostics: Tuple[PartitionDiagnostic, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class CreatePartitionFunctionAction(PartitionBaseAction):
    function_name: str = ""
    strategy: str = ""
    boundary_values: Tuple[CanonicalScalarValue, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class SplitPartitionAction(PartitionBaseAction):
    source_partition: str = ""
    new_boundaries: Tuple[CanonicalRangeInterval, ...] = field(default_factory=tuple)
    planner_reason: str = ""
    compatibility_decision: str = ""
    required_validations: Tuple[str, ...] = field(default_factory=tuple)
    estimated_lock: str = "EXCLUSIVE"
    estimated_downtime: float = 0.0

@dataclass(frozen=True)
class MergePartitionAction(PartitionBaseAction):
    source_partitions: Tuple[str, ...] = field(default_factory=tuple)
    target_boundary: Optional[CanonicalRangeInterval] = None
    required_validations: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class CreatePartitionSchemeAction(PartitionBaseAction):
    scheme_name: str = ""
    function_name: str = ""
    filegroups: Tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class CreatePartitionedTableAction(PartitionBaseAction):
    table_name: str = ""
    columns_spec: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class CreateChildPartitionAction(PartitionBaseAction):
    child_table_name: str = ""
    parent_table_name: str = ""
    boundary: Optional[CanonicalRangeInterval] = None

@dataclass(frozen=True)
class AttachPartitionAction(PartitionBaseAction):
    child_table_name: str = ""
    parent_table_name: str = ""
    boundary: Optional[CanonicalRangeInterval] = None

@dataclass(frozen=True)
class DetachPartitionAction(PartitionBaseAction):
    child_table_name: str = ""
    parent_table_name: str = ""

@dataclass(frozen=True)
class SwitchPartitionAction(PartitionBaseAction):
    source_table: str = ""
    target_table: str = ""
    source_partition_id: int = 0
    target_partition_id: int = 0

@dataclass(frozen=True)
class CreateShadowTableAction(PartitionBaseAction):
    shadow_table_name: str = ""
    original_table_name: str = ""

@dataclass(frozen=True)
class CopyPartitionDataAction(PartitionBaseAction):
    source_table: str = ""
    target_table: str = ""
    boundary: Optional[CanonicalRangeInterval] = None

@dataclass(frozen=True)
class ValidatePartitionRowsAction(PartitionBaseAction):
    table_name: str = ""
    boundary: Optional[CanonicalRangeInterval] = None

@dataclass(frozen=True)
class ValidateConstraintAction(PartitionBaseAction):
    table_name: str = ""
    constraint_name: str = ""

@dataclass(frozen=True)
class CreateLocalIndexAction(PartitionBaseAction):
    index_name: str = ""
    table_name: str = ""

@dataclass(frozen=True)
class CreateGlobalIndexAction(PartitionBaseAction):
    index_name: str = ""
    table_name: str = ""

@dataclass(frozen=True)
class RebuildIndexAction(PartitionBaseAction):
    index_name: str = ""
    table_name: str = ""

@dataclass(frozen=True)
class MoveStorageAction(PartitionBaseAction):
    object_name: str = ""
    target_tablespace: str = ""

@dataclass(frozen=True)
class CaptureCheckpointAction(PartitionBaseAction):
    checkpoint_name: str = ""

@dataclass(frozen=True)
class RequireApprovalAction(PartitionBaseAction):
    approval_type: str = ""

@dataclass(frozen=True)
class RequireBackupAction(PartitionBaseAction):
    backup_scope: str = ""

@dataclass(frozen=True)
class CutoverAction(PartitionBaseAction):
    original_table: str = ""
    shadow_table: str = ""

@dataclass(frozen=True)
class CleanupAction(PartitionBaseAction):
    retained_table_name: str = ""

@dataclass(frozen=True)
class RollbackPlan:
    ordered_actions: Tuple[PartitionBaseAction, ...] = field(default_factory=tuple)
    readiness: PlanReadinessStatus = PlanReadinessStatus.READY

@dataclass(frozen=True)
class PartitionPlan:
    plan_id: str
    plan_version: str
    planner_version: str
    schema_version: str
    source_fingerprint: str
    target_fingerprint: str
    policy_fingerprint: str
    ordered_actions: Tuple[PartitionBaseAction, ...]
    dependency_graph: Dict[str, Tuple[str, ...]]
    resource_lock_graph: Dict[str, Tuple[str, ...]]
    validation_graph: Dict[str, Tuple[str, ...]]
    approval_graph: Dict[str, Tuple[str, ...]]
    checkpoint_graph: Dict[str, Tuple[str, ...]]
    estimated_downtime: DowntimeClassification
    reconstruction_flag: bool
    execution_policy: ExecutionPolicy
    idempotency_policy: str
    retry_policy: str
    execution_ordering: Tuple[str, ...]
    planner_metadata: Dict[str, Any]
    unsupported_capability_list: Tuple[str, ...]
    warnings: Tuple[str, ...]
    diagnostics: Tuple[PartitionDiagnostic, ...]
    readiness: PlanReadinessStatus = PlanReadinessStatus.READY
    plan_fingerprint: str = ""

    def __post_init__(self):
        if not self.plan_id:
            raise ValueError("Plan ID must be populated.")
