from enum import Enum
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Tuple, Optional, Union, Dict, List, Set, Any

class CanonicalDataType(str, Enum):
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP"
    TIMESTAMP_TZ = "TIMESTAMP_TZ"
    STRING = "STRING"
    BINARY = "BINARY"
    BOOLEAN = "BOOLEAN"

class BoundarySpecialType(str, Enum):
    NORMAL = "NORMAL"
    NULL = "NULL"
    MINVALUE = "MINVALUE"
    MAXVALUE = "MAXVALUE"
    DEFAULT = "DEFAULT"

@dataclass(frozen=True)
class CanonicalScalarValue:
    data_type: CanonicalDataType
    special_type: BoundarySpecialType = BoundarySpecialType.NORMAL
    int_val: Optional[int] = None
    decimal_val: Optional[Decimal] = None
    date_val: Optional[date] = None
    ts_val: Optional[datetime] = None
    str_val: Optional[str] = None
    bin_val: Optional[bytes] = None
    bool_val: Optional[bool] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    timezone_offset_seconds: Optional[int] = None
    collation: Optional[str] = None
    char_set: Optional[str] = None

    def __post_init__(self):
        if self.special_type != BoundarySpecialType.NORMAL:
            if any([
                self.int_val is not None,
                self.decimal_val is not None,
                self.date_val is not None,
                self.ts_val is not None,
                self.str_val is not None,
                self.bin_val is not None,
                self.bool_val is not None
            ]):
                raise ValueError("Special boundaries cannot define scalar values.")
            return

        if self.data_type == CanonicalDataType.INTEGER:
            if not isinstance(self.int_val, int) or isinstance(self.int_val, bool):
                raise TypeError("INTEGER requires an int payload.")
        elif self.data_type == CanonicalDataType.DECIMAL:
            if not isinstance(self.decimal_val, Decimal):
                raise TypeError("DECIMAL requires a Decimal payload.")
        elif self.data_type == CanonicalDataType.DATE:
            if not isinstance(self.date_val, date) or isinstance(self.date_val, datetime):
                raise TypeError("DATE requires a date payload.")
        elif self.data_type == CanonicalDataType.TIMESTAMP:
            if not isinstance(self.ts_val, datetime) or self.ts_val.tzinfo is not None:
                raise TypeError("TIMESTAMP requires timezone-naive datetime.")
        elif self.data_type == CanonicalDataType.TIMESTAMP_TZ:
            if not isinstance(self.ts_val, datetime) or self.ts_val.tzinfo is None:
                raise TypeError("TIMESTAMP_TZ requires timezone-aware datetime.")
        elif self.data_type == CanonicalDataType.STRING:
            if not isinstance(self.str_val, str):
                raise TypeError("STRING requires a string payload.")
        elif self.data_type == CanonicalDataType.BINARY:
            if not isinstance(self.bin_val, bytes):
                raise TypeError("BINARY requires a bytes payload.")
        elif self.data_type == CanonicalDataType.BOOLEAN:
            if not isinstance(self.bool_val, bool):
                raise TypeError("BOOLEAN requires a bool payload.")

    def serialize(self) -> str:
        if self.special_type != BoundarySpecialType.NORMAL:
            return f"SPECIAL:{self.special_type.value}"

        if self.data_type == CanonicalDataType.INTEGER:
            return f"I:{self.int_val}"
        elif self.data_type == CanonicalDataType.DECIMAL:
            sign, digits, exponent = self.decimal_val.normalize().as_tuple()
            return f"D:{sign}_{digits}_{exponent}"
        elif self.data_type == CanonicalDataType.DATE:
            return f"DA:{self.date_val.isoformat()}"
        elif self.data_type == CanonicalDataType.TIMESTAMP:
            return f"TS:{self.ts_val.isoformat()}"
        elif self.data_type == CanonicalDataType.TIMESTAMP_TZ:
            utc_iso = self.ts_val.astimezone(timezone.utc).isoformat()
            return f"TZ:{utc_iso}:{self.timezone_offset_seconds or 0}"
        elif self.data_type == CanonicalDataType.STRING:
            import unicodedata
            nfc_str = unicodedata.normalize("NFC", self.str_val)
            return f"S:{nfc_str}"
        elif self.data_type == CanonicalDataType.BINARY:
            import base64
            b64_str = base64.b64encode(self.bin_val).decode("utf-8")
            return f"B:{b64_str}"
        elif self.data_type == CanonicalDataType.BOOLEAN:
            return "BO:1" if self.bool_val else "BO:0"
        return "UNKNOWN"

class BoundInclusivity(str, Enum):
    INCLUSIVE = "INCLUSIVE"
    EXCLUSIVE = "EXCLUSIVE"

@dataclass(frozen=True)
class CanonicalDomainStep:
    value_type: CanonicalDataType
    step_value: Union[int, Decimal, float, None]
    source_precision: Optional[int] = None
    source_scale: Optional[int] = None

@dataclass(frozen=True)
class CanonicalRangeBound:
    values: Tuple[CanonicalScalarValue, ...]
    inclusivity: BoundInclusivity
    unbounded: bool

    def __post_init__(self):
        if self.unbounded and len(self.values) > 0:
            raise ValueError("Unbounded bounds cannot define scalar values.")

@dataclass(frozen=True)
class CanonicalRangeInterval:
    lower: CanonicalRangeBound
    upper: CanonicalRangeBound

    def __post_init__(self):
        if not self.lower.unbounded and not self.upper.unbounded:
            if len(self.lower.values) != len(self.upper.values):
                raise ValueError("Composite range bound arities must match.")

@dataclass(frozen=True)
class ObjectIdentity:
    schema: str
    name: str
    object_type: str

class PartitionStrategy(str, Enum):
    RANGE = "RANGE"
    LIST = "LIST"
    HASH = "HASH"
    KEY = "KEY"
    NONE = "NONE"

@dataclass(frozen=True)
class CanonicalStoragePlacement:
    tablespace_name: Optional[str] = None
    filegroup_name: Optional[str] = None

@dataclass(frozen=True)
class CanonicalRangePartition:
    object_identity: ObjectIdentity
    partition_name: str
    ordinal: int
    boundary: CanonicalRangeInterval
    storage: Optional[CanonicalStoragePlacement] = None
    subpartition_scheme: Optional['CanonicalPartitionScheme'] = None

@dataclass(frozen=True)
class CanonicalListPartition:
    object_identity: ObjectIdentity
    partition_name: str
    ordinal: int
    values: Tuple[Tuple[CanonicalScalarValue, ...], ...]
    is_default: bool = False
    storage: Optional[CanonicalStoragePlacement] = None
    subpartition_scheme: Optional['CanonicalPartitionScheme'] = None

    def __post_init__(self):
        if not self.is_default and len(self.values) == 0:
            raise ValueError("Non-default LIST partition must specify value tuples.")

@dataclass(frozen=True)
class CanonicalHashPartition:
    object_identity: ObjectIdentity
    partition_name: str
    ordinal: int
    modulus: int
    remainder: int
    storage: Optional[CanonicalStoragePlacement] = None

    def __post_init__(self):
        if self.modulus <= 0:
            raise ValueError("Modulus must be positive.")
        if not (0 <= self.remainder < self.modulus):
            raise ValueError("Remainder must be in range [0, modulus-1].")

@dataclass(frozen=True)
class CanonicalKeyPartition:
    object_identity: ObjectIdentity
    partition_name: str
    ordinal: int
    column_count: int
    storage: Optional[CanonicalStoragePlacement] = None

CanonicalPartitionDefinition = Union[
    CanonicalRangePartition,
    CanonicalListPartition,
    CanonicalHashPartition,
    CanonicalKeyPartition,
]

class MetadataConfidence(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INFERRED = "INFERRED"
    UNAVAILABLE = "UNAVAILABLE"

@dataclass(frozen=True)
class CanonicalColumnPartitionKey:
    column_name: str
    canonical_type: CanonicalDataType
    native_type: str
    position: int
    nullable: bool
    precision: Optional[int] = None
    scale: Optional[int] = None
    length: Optional[int] = None
    ts_precision: Optional[int] = None
    collation: Optional[str] = None
    char_set: Optional[str] = None

class ExpressionNodeType(str, Enum):
    COLUMN_REF = "COLUMN_REF"
    LITERAL = "LITERAL"
    CAST = "CAST"
    FUNCTION_CALL = "FUNCTION_CALL"
    BINARY_OP = "BINARY_OP"

@dataclass(frozen=True)
class CanonicalExpressionNode:
    node_type: ExpressionNodeType
    value: str
    children: Tuple['CanonicalExpressionNode', ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class CanonicalExpressionPartitionKey:
    expression_ast: CanonicalExpressionNode
    result_type: CanonicalDataType
    position: int
    determinism: bool
    referenced_columns: Tuple[str, ...]

@dataclass(frozen=True)
class CanonicalPartitionScheme:
    table_identity: ObjectIdentity
    source_dialect: str
    source_version: str
    confidence: MetadataConfidence
    strategy: PartitionStrategy
    keys: Tuple[Union[CanonicalColumnPartitionKey, CanonicalExpressionPartitionKey], ...]
    partitions: Tuple[CanonicalPartitionDefinition, ...]
    subpartition_strategy: PartitionStrategy = PartitionStrategy.NONE
    partition_function_identity: Optional[str] = None
    partition_scheme_identity: Optional[str] = None
    tablespace_mapping: Dict[str, str] = field(default_factory=dict)
    filegroup_mapping: Dict[str, str] = field(default_factory=dict)
    local_index_aligned: bool = True
    constraint_aligned: bool = True
    source_metadata_fingerprint: str = ""

    def __post_init__(self):
        positions = [k.position for k in self.keys]
        if sorted(positions) != list(range(len(self.keys))):
            raise ValueError("Key positions must be contiguous and start at 0.")

        names = [p.partition_name for p in self.partitions]
        if len(names) != len(set(names)):
            raise ValueError("Partition names must be unique within table scheme.")

class PartitionDiagnosticCode(str, Enum):
    DISCOVERY_PERMISSION_DENIED = "DISCOVERY_PERMISSION_DENIED"
    UNSUPPORTED_DIALECT_VERSION = "UNSUPPORTED_DIALECT_VERSION"
    MALFORMED_CATALOG_METADATA = "MALFORMED_CATALOG_METADATA"
    OVERLAPPING_RANGES = "OVERLAPPING_RANGES"
    RANGE_GAPS_DETECTED = "RANGE_GAPS_DETECTED"
    DUPLICATE_LIST_VALUE = "DUPLICATE_LIST_VALUE"
    INVALID_COMPOSITE_ARITY = "INVALID_COMPOSITE_ARITY"
    INVALID_HASH_MODULUS = "INVALID_HASH_MODULUS"
    INVALID_HASH_REMAINDER = "INVALID_HASH_REMAINDER"
    HASH_ALGORITHM_MISMATCH = "HASH_ALGORITHM_MISMATCH"
    KEY_ALGORITHM_UNSUPPORTED = "KEY_ALGORITHM_UNSUPPORTED"
    EXPRESSION_PARSE_FAILURE = "EXPRESSION_PARSE_FAILURE"
    VOLATILE_EXPRESSION = "VOLATILE_EXPRESSION"
    UNSUPPORTED_EXPRESSION_NODE = "UNSUPPORTED_EXPRESSION_NODE"
    INDEX_ALIGNMENT_CONFLICT = "INDEX_ALIGNMENT_CONFLICT"
    CONSTRAINT_ALIGNMENT_CONFLICT = "CONSTRAINT_ALIGNMENT_CONFLICT"
    FOREIGN_KEY_DEPENDENCY_BLOCK = "FOREIGN_KEY_DEPENDENCY_BLOCK"
    CYCLE_DETECTED = "CYCLE_DETECTED"
    ROLLBACK_UNAVAILABLE = "ROLLBACK_UNAVAILABLE"
    UNSAFE_DESTRUCTIVE_ACTION = "UNSAFE_DESTRUCTIVE_ACTION"
    DATA_MIGRATION_REQUIRED = "DATA_MIGRATION_REQUIRED"
    DOWNTIME_EXPECTED = "DOWNTIME_EXPECTED"

@dataclass(frozen=True)
class PartitionDiagnostic:
    code: PartitionDiagnosticCode
    severity: str
    message: str
    affected_object: ObjectIdentity
    remediation: str
    blocking: bool = True

class PartitionApprovalType(str, Enum):
    LOSSY_TRANSLATION = "LOSSY_TRANSLATION"
    DESTRUCTIVE_CHANGE = "DESTRUCTIVE_CHANGE"
    DATA_MOVEMENT = "DATA_MOVEMENT"
    DOWNTIME = "DOWNTIME"
    BACKUP_CONFIRMATION = "BACKUP_CONFIRMATION"

class PartitionApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

@dataclass(frozen=True)
class PartitionApproval:
    approval_id: str
    approval_type: PartitionApprovalType
    plan_fingerprint: str
    approver_reference: str
    expiration_timestamp: datetime
    status: PartitionApprovalStatus = PartitionApprovalStatus.PENDING

class PartitionDifferenceType(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    MODIFY = "MODIFY"
    RENAME = "RENAME"

class PartitionChangeImpact(str, Enum):
    NONE = "NONE"
    METADATA_ONLY = "METADATA_ONLY"
    REBUILD_INDEX = "REBUILD_INDEX"
    RECONSTRUCT_TABLE = "RECONSTRUCT_TABLE"

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

class PlanReadinessStatus(str, Enum):
    READY = "READY"
    READY_WITH_APPROVAL = "READY_WITH_APPROVAL"
    READY_WITH_BACKUP = "READY_WITH_BACKUP"
    RECONSTRUCTION_REQUIRED = "RECONSTRUCTION_REQUIRED"
    BLOCKED = "BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"

@dataclass(frozen=True)
class PartitionDifference:
    difference_id: str
    difference_type: PartitionDifferenceType
    object_identity: ObjectIdentity
    source_value: str
    target_value: str
    impact: PartitionChangeImpact
    default_partition: bool = False
    severity: str = "ERROR"
    required_action: str = ""
    data_movement_impact: DataMovementClassification = DataMovementClassification.NONE
    approval_impact: str = ""
    rollback_impact: str = ""
    diagnostic: Optional[PartitionDiagnostic] = None

@dataclass(frozen=True)
class PartitionComparisonReport:
    differences: Tuple[PartitionDifference, ...]

@dataclass(frozen=True)
class PartitionCapabilityDecision:
    capability: str
    status: str
    reason: str
    evidence: str
    required_planner_action: str
    approval_requirement: str
    rollback_support: str
    downtime_class: DowntimeClassification
    data_movement: DataMovementClassification
    blocking: bool
    diagnostics: Tuple[PartitionDiagnostic, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class PartitionCompatibilityReport:
    source_scheme_fingerprint: str
    target_dialect: str
    target_version: str
    overall_readiness: PlanReadinessStatus
    decisions: Tuple[PartitionCapabilityDecision, ...]
    data_compatible: bool
    key_compatible: bool
    boundary_compatible: bool
    storage_compatible: bool
    index_compatible: bool
    constraint_compatible: bool
    reconstruction_required: bool
    report_fingerprint: str = ""

