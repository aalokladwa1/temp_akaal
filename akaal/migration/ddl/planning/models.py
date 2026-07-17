"""
Akaal — Identity Migration Planning Models
===========================================
Defines immutable data models, type-safe enums, and fingerprint/readiness
validation rules for Checkpoint 7.
"""

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple, Any
from akaal.migration.models import ObjectType, MigrationObject


class DatabaseDialect(str, Enum):
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    MSSQL = "mssql"
    MYSQL = "mysql"


class PlanReadinessStatus(str, Enum):
    READY = "READY"
    PREVIEW_ONLY = "PREVIEW_ONLY"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    REQUIRES_FALLBACK = "REQUIRES_FALLBACK"
    REQUIRES_RECONSTRUCTION = "REQUIRES_RECONSTRUCTION"
    INCOMPLETE_METADATA = "INCOMPLETE_METADATA"
    UNRESOLVED_DEPENDENCY = "UNRESOLVED_DEPENDENCY"
    CYCLIC = "CYCLIC"
    BLOCKED_UNSAFE = "BLOCKED_UNSAFE"
    UNSUPPORTED = "UNSUPPORTED"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"


class ObjectOrigin(str, Enum):
    CREATED_BY_PLAN = "CREATED_BY_PLAN"
    PRE_EXISTING = "PRE_EXISTING"
    UNKNOWN = "UNKNOWN"


class MutationState(str, Enum):
    MODIFIED = "MODIFIED"
    UNMODIFIED = "UNMODIFIED"
    DELETED = "DELETED"


class PriorStateAvailability(str, Enum):
    CAPTURED = "CAPTURED"
    STALE = "STALE"
    ABSENT = "ABSENT"


class NamingProvenance(str, Enum):
    DISCOVERED = "DISCOVERED"
    USER_SUPPLIED = "USER_SUPPLIED"
    GENERATED = "GENERATED"
    REUSED = "REUSED"


class ApprovalState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


class SafetyClassification(str, Enum):
    SAFE = "SAFE"
    SAFE_RESEED = "SAFE_RESEED"
    UNSAFE_REBUILD = "UNSAFE_REBUILD"
    BLOCKED_UNSUPPORTED = "BLOCKED_UNSUPPORTED"


class DependencyType(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    OPTIONAL = "OPTIONAL"
    VALIDATION = "VALIDATION"
    ROLLBACK = "ROLLBACK"
    APPROVAL = "APPROVAL"


class DependencyStatus(str, Enum):
    PENDING = "PENDING"
    SATISFIED = "SATISFIED"
    BLOCKED = "BLOCKED"


class OperationPhase(str, Enum):
    RECONSTRUCT_PRE = "RECONSTRUCT_PRE"
    DDL_PRE = "DDL_PRE"
    OBJECT_CREATION = "OBJECT_CREATION"
    OBJECT_BINDING = "OBJECT_BINDING"
    DATA_MIGRATION = "DATA_MIGRATION"
    DDL_POST = "DDL_POST"
    VALIDATION = "VALIDATION"
    CLEANUP = "CLEANUP"


class RollbackClassification(str, Enum):
    EXACT = "EXACT"
    COMPENSATING = "COMPENSATING"
    BEST_EFFORT = "BEST_EFFORT"
    REQUIRES_BACKUP = "REQUIRES_BACKUP"
    REQUIRES_RECONSTRUCTION = "REQUIRES_RECONSTRUCTION"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class DiagnosticSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class DiagnosticCode(str, Enum):
    INCOMPLETE_METADATA = "INCOMPLETE_METADATA"
    UNRESOLVED_DEPENDENCY = "UNRESOLVED_DEPENDENCY"
    APPROVAL_MISSING = "APPROVAL_MISSING"
    APPROVAL_INVALIDATED = "APPROVAL_INVALIDATED"
    OWNERSHIP_AMBIGUITY = "OWNERSHIP_AMBIGUITY"
    UNSAFE_CONFLICT = "UNSAFE_CONFLICT"
    UNSUPPORTED_SEMANTICS = "UNSUPPORTED_SEMANTICS"
    ROLLBACK_UNAVAILABLE = "ROLLBACK_UNAVAILABLE"
    NAMING_COLLISION = "NAMING_COLLISION"
    GRAPH_CYCLE = "GRAPH_CYCLE"
    DUPLICATE_NODE = "DUPLICATE_NODE"
    CONTRADICTORY_METADATA = "CONTRADICTORY_METADATA"


class ReconstructionStageType(str, Enum):
    VALIDATE_INVENTORY = "VALIDATE_INVENTORY"
    VERIFY_BACKUP = "VERIFY_BACKUP"
    PLAN_SHADOW_OBJECT = "PLAN_SHADOW_OBJECT"
    SUSPEND_DEPENDENCIES = "SUSPEND_DEPENDENCIES"
    PLAN_DATA_COPY = "PLAN_DATA_COPY"
    VALIDATE_ROW_COUNT = "VALIDATE_ROW_COUNT"
    VALIDATE_KEYS = "VALIDATE_KEYS"
    VALIDATE_REFERENTIAL_INTEGRITY = "VALIDATE_REFERENTIAL_INTEGRITY"
    SWAP_APPROVAL_GATE = "SWAP_APPROVAL_GATE"
    SWAP_PREVIEW = "SWAP_PREVIEW"
    POST_SWAP_VALIDATE = "POST_SWAP_VALIDATE"
    CLEANUP_RETAINED_ORIGINAL = "CLEANUP_RETAINED_ORIGINAL"
    PREPARE_ROLLBACK = "PREPARE_ROLLBACK"


@dataclass(frozen=True)
class ObjectIdentity:
    schema: str
    name: str
    object_type: ObjectType

    def __post_init__(self):
        if not self.schema or not self.name:
            raise ValueError("Schema and name must be non-empty strings.")
        if "." in self.schema or "." in self.name:
            raise ValueError("Identifier components must not contain dots.")

    def to_dict(self) -> Dict[str, str]:
        return {"schema": self.schema, "name": self.name, "type": self.object_type.value}


@dataclass(frozen=True)
class ObjectInventory:
    inventory_map: Dict[ObjectIdentity, MigrationObject]
    complete_assurance: bool = False

    def __post_init__(self):
        # Defensive copy of mapping
        object.__setattr__(self, "inventory_map", dict(self.inventory_map))


@dataclass(frozen=True)
class SequenceFallbackPlan:
    identity: ObjectIdentity
    dialect: DatabaseDialect
    db_version: str
    start: int
    increment: int
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    cycle: bool = False
    cache: int = 1

    def __post_init__(self):
        if self.increment == 0:
            raise ValueError("Sequence increment cannot be zero.")
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValueError("min_value cannot be greater than max_value.")

    def calculate_fingerprint(self) -> str:
        data = {
            "identity": self.identity.to_dict(),
            "dialect": self.dialect.value,
            "db_version": self.db_version,
            "start": self.start,
            "increment": self.increment,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "cycle": self.cycle,
            "cache": self.cache
        }
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(f"akaal_v1_planning:{serialized}".encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TriggerFallbackPlan:
    identity: ObjectIdentity
    referenced_sequence: ObjectIdentity
    timing: str
    event: str
    generated_value_condition: Optional[str] = None

    def __post_init__(self):
        if self.timing != "BEFORE" or self.event != "INSERT":
            raise ValueError("Trigger timing must be BEFORE and event must be INSERT.")


@dataclass(frozen=True)
class IdentityDiagnostic:
    code: DiagnosticCode
    severity: DiagnosticSeverity
    safe_message: str
    affected_node: Optional[str] = None
    affected_object: Optional[ObjectIdentity] = None
    metadata_path: Optional[str] = None
    blocking: bool = True
    remediation_guidance: str = ""


@dataclass(frozen=True)
class CycleDiagnostic:
    cycle_detected: bool
    participating_node_ids: Tuple[str, ...] = field(default_factory=tuple)
    involved_objects: Tuple[ObjectIdentity, ...] = field(default_factory=tuple)

    def __post_init__(self):
        object.__setattr__(self, "participating_node_ids", tuple(self.participating_node_ids))
        object.__setattr__(self, "involved_objects", tuple(self.involved_objects))


@dataclass(frozen=True)
class UnresolvedDependencyDiagnostic:
    node_id: str
    missing_prerequisite_id: str


@dataclass(frozen=True)
class ReconstructionStage:
    stage_id: str
    stage_type: ReconstructionStageType
    required_metadata: Dict[str, Any] = field(default_factory=dict)
    prerequisites: Tuple[str, ...] = field(default_factory=tuple)
    readiness_status: PlanReadinessStatus = PlanReadinessStatus.READY
    safety_level: SafetyClassification = SafetyClassification.SAFE
    approval_state: ApprovalState = ApprovalState.PENDING
    backup_requirement: bool = False
    validation_gates: Tuple[str, ...] = field(default_factory=tuple)
    rollback_ref: Optional[str] = None
    command_preview: Optional[str] = None

    def __post_init__(self):
        object.__setattr__(self, "required_metadata", dict(self.required_metadata))
        object.__setattr__(self, "prerequisites", tuple(self.prerequisites))
        object.__setattr__(self, "validation_gates", tuple(self.validation_gates))


@dataclass(frozen=True)
class IdentityReconstructionPlan:
    reason: str
    schema: str
    table: str
    column: str
    stages: Tuple[ReconstructionStage, ...] = field(default_factory=tuple)
    validation_gates: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        object.__setattr__(self, "stages", tuple(self.stages))
        object.__setattr__(self, "validation_gates", tuple(self.validation_gates))


@dataclass(frozen=True)
class DependencyNode:
    node_id: str
    ordering_key: str
    operation_phase: OperationPhase
    prerequisites: Tuple[str, ...] = field(default_factory=tuple)
    readiness_status: PlanReadinessStatus = PlanReadinessStatus.READY
    dependency_status: DependencyStatus = DependencyStatus.PENDING
    approval_state: ApprovalState = ApprovalState.PENDING
    provenance: ObjectOrigin = ObjectOrigin.UNKNOWN
    rollback_ref: Optional[str] = None
    diagnostics: Tuple[IdentityDiagnostic, ...] = field(default_factory=tuple)
    fingerprint_contrib: str = ""

    def __post_init__(self):
        object.__setattr__(self, "prerequisites", tuple(self.prerequisites))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))


@dataclass(frozen=True)
class DependencyGraph:
    nodes: Tuple[DependencyNode, ...] = field(default_factory=tuple)
    adjacency_list: Dict[str, Tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "nodes", tuple(self.nodes))
        # Freeze adjacency list values
        frozen_adj = {k: tuple(v) for k, v in self.adjacency_list.items()}
        object.__setattr__(self, "adjacency_list", frozen_adj)


@dataclass(frozen=True)
class ScheduledIdentityPlan:
    ordered_nodes: Tuple[DependencyNode, ...] = field(default_factory=tuple)
    readiness: PlanReadinessStatus = PlanReadinessStatus.READY
    fingerprint: str = ""

    def __post_init__(self):
        object.__setattr__(self, "ordered_nodes", tuple(self.ordered_nodes))


@dataclass(frozen=True)
class RollbackNode:
    rollback_node_id: str
    origin_node_id: str
    revert_command_preview: Optional[str] = None
    prerequisites: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        object.__setattr__(self, "prerequisites", tuple(self.prerequisites))


@dataclass(frozen=True)
class RollbackPlan:
    ordered_rollback_nodes: Tuple[RollbackNode, ...] = field(default_factory=tuple)
    readiness: PlanReadinessStatus = PlanReadinessStatus.READY

    def __post_init__(self):
        object.__setattr__(self, "ordered_rollback_nodes", tuple(self.ordered_rollback_nodes))


@dataclass(frozen=True)
class ApprovalContext:
    state: ApprovalState
    plan_fingerprint: str
    metadata_version: str
    target_dialect: DatabaseDialect
    target_version: str
    rollback_fingerprint: str
    backup_approval: bool = False
    safety_scope: str = ""
    timestamp: str = ""
