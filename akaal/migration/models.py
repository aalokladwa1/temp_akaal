import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

class ObjectType(str, Enum):
    TABLE = "TABLE"
    COLUMN = "COLUMN"
    CONSTRAINT = "CONSTRAINT"
    INDEX = "INDEX"
    VIEW = "VIEW"
    TRIGGER = "TRIGGER"
    FUNCTION = "FUNCTION"
    PROCEDURE = "PROCEDURE"
    SEQUENCE = "SEQUENCE"
    PARTITION = "PARTITION"
    SYNONYM = "SYNONYM"
    MATERIALIZED_VIEW = "MATERIALIZED_VIEW"

@dataclass
class MigrationObject:
    name: str
    object_type: ObjectType = ObjectType.TABLE
    id: str = ""
    object_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    object_key: str = ""
    schema: Optional[str] = None
    vendor_metadata: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = self.name
        if not self.object_key:
            prefix = f"{self.schema}." if self.schema else ""
            self.object_key = f"{prefix}{self.name}"

@dataclass
class Column(MigrationObject):
    data_type: str = ""
    nullable: bool = True
    default: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.COLUMN

@dataclass
class Constraint(MigrationObject):
    constraint_type: str = ""  # e.g., PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK
    columns: Tuple[str, ...] = field(default_factory=tuple)
    reference_table: Optional[str] = None
    reference_columns: Tuple[str, ...] = field(default_factory=tuple)
    check_clause: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.CONSTRAINT

@dataclass
class Index(MigrationObject):
    columns: Tuple[str, ...] = field(default_factory=tuple)
    unique: bool = False
    index_type: str = "BTREE"

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.INDEX

@dataclass
class Table(MigrationObject):
    columns: List[Column] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    indexes: List[Index] = field(default_factory=list)
    partitions: List[Any] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.TABLE

@dataclass
class View(MigrationObject):
    definition: str = ""
    dependencies: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.VIEW

@dataclass
class MaterializedView(MigrationObject):
    definition: str = ""
    refresh_mode: str = "DEMAND"
    refresh_method: str = "FORCE"
    indexes: List[Index] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.MATERIALIZED_VIEW

@dataclass
class Trigger(MigrationObject):
    table_name: str = ""
    timing: str = "BEFORE"  # BEFORE, AFTER, INSTEAD OF
    event: str = "INSERT"   # INSERT, UPDATE, DELETE
    definition: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.TRIGGER

@dataclass
class Function(MigrationObject):
    parameters: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    return_type: str = ""
    definition: str = ""
    language: str = "SQL"

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.FUNCTION

@dataclass
class Procedure(MigrationObject):
    parameters: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    definition: str = ""
    language: str = "SQL"

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.PROCEDURE

@dataclass
class Sequence(MigrationObject):
    start_value: int = 1
    increment_by: int = 1
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    cycle: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.SEQUENCE

@dataclass
class Partition(MigrationObject):
    table_name: str = ""
    partition_type: str = "RANGE"  # RANGE, LIST, HASH
    expression: str = ""
    values: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.PARTITION

@dataclass
class Synonym(MigrationObject):
    object_name: str = ""
    is_public: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.object_type = ObjectType.SYNONYM

@dataclass
class ComparisonDifference:
    difference_id: str
    diff_type: str  # "ADD", "REMOVE", "MODIFY"
    object_type: ObjectType
    object_name: str
    schema_name: Optional[str] = None
    old_object: Optional[MigrationObject] = None
    new_object: Optional[MigrationObject] = None
    change_details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SchemaComparisonReport:
    source_schema: str
    target_schema: str
    differences: List[ComparisonDifference] = field(default_factory=list)

class OperationType(str, Enum):
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"

@dataclass(frozen=True)
class MigrationOperation:
    operation_id: str
    operation_type: OperationType
    target_object: MigrationObject
    depends_on: Tuple[str, ...] = field(default_factory=tuple)
    priority: int = 1
    stage: str = "STAGE_1"
    can_parallelize: bool = True
    requires_lock: bool = False
    rollback_operation_id: Optional[str] = None
    retryable: bool = True
    destructive: bool = False
    estimated_cost: float = 1.0
    estimated_duration_ms: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class MigrationPlan:
    planner_version: str
    plan_version: str
    generated_at: str
    source_database: str
    target_database: str
    operations: Tuple[MigrationOperation, ...]
    plan_hash: str = ""
    created_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class DDLCommand:
    sql: str
    rollback_sql: Optional[str] = None
    dialect: str = ""
    execution_order: int = 0
    transaction_required: bool = True
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    estimated_duration: float = 0.0
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionContext:
    transaction_required: bool = True
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    metrics_collector: Optional[Any] = None
    audit_context: Dict[str, Any] = field(default_factory=dict)
    lock_manager: Optional[Any] = None

@dataclass
class MigrationResult:
    success: bool
    executed_commands: List[DDLCommand] = field(default_factory=list)
    failed_commands: List[DDLCommand] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    elapsed_time_ms: float = 0.0
    statistics: Dict[str, Any] = field(default_factory=dict)
    rollback_information: Dict[str, Any] = field(default_factory=dict)
