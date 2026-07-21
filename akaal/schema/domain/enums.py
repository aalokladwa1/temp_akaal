"""
AKAAL Platform 5 — Enums & State Definitions

Defines formal states, risk levels, change types, lock categories, and failure classes.
"""

from enum import Enum, auto


class TransactionState(str, Enum):
    """Lifecycle states for SchemaTransaction."""
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    EXECUTING = "EXECUTING"
    COMMITTED = "COMMITTED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class RefreshState(str, Enum):
    """Lifecycle states for Dynamic Metadata Refresh."""
    IDLE = "IDLE"
    QUEUED = "QUEUED"
    REFRESHING = "REFRESHING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvolutionState(str, Enum):
    """Lifecycle states for Live Schema Evolution execution."""
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    VALIDATED = "VALIDATED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class ReplayState(str, Enum):
    """Lifecycle states for DDL Replay engine."""
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    REPLAYING = "REPLAYING"
    CHECKPOINTED = "CHECKPOINTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReplayStatus(str, Enum):
    """Execution status for individual journal records."""
    UNEXECUTED = "UNEXECUTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ChangeType(str, Enum):
    """Strongly typed schema change categories."""
    ADD_TABLE = "ADD_TABLE"
    DROP_TABLE = "DROP_TABLE"
    RENAME_TABLE = "RENAME_TABLE"
    TRUNCATE_TABLE = "TRUNCATE_TABLE"
    ADD_COLUMN = "ADD_COLUMN"
    DROP_COLUMN = "DROP_COLUMN"
    RENAME_COLUMN = "RENAME_COLUMN"
    MODIFY_COLUMN = "MODIFY_COLUMN"
    ALTER_NULLABILITY = "ALTER_NULLABILITY"
    ALTER_DEFAULT = "ALTER_DEFAULT"
    CHANGE_PRIMARY_KEY = "CHANGE_PRIMARY_KEY"
    CHANGE_FOREIGN_KEY = "CHANGE_FOREIGN_KEY"
    ADD_UNIQUE_CONSTRAINT = "ADD_UNIQUE_CONSTRAINT"
    DROP_UNIQUE_CONSTRAINT = "DROP_UNIQUE_CONSTRAINT"
    ADD_CHECK_CONSTRAINT = "ADD_CHECK_CONSTRAINT"
    DROP_CHECK_CONSTRAINT = "DROP_CHECK_CONSTRAINT"
    CREATE_INDEX = "CREATE_INDEX"
    DROP_INDEX = "DROP_INDEX"
    RENAME_INDEX = "RENAME_INDEX"
    CREATE_VIEW = "CREATE_VIEW"
    DROP_VIEW = "DROP_VIEW"
    MODIFY_VIEW = "MODIFY_VIEW"
    CREATE_SEQUENCE = "CREATE_SEQUENCE"
    DROP_SEQUENCE = "DROP_SEQUENCE"
    CREATE_TRIGGER = "CREATE_TRIGGER"
    DROP_TRIGGER = "DROP_TRIGGER"


class RiskLevel(str, Enum):
    """Risk severity classifications for schema compatibility analysis."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConstraintType(str, Enum):
    """Database constraint types."""
    PRIMARY_KEY = "PRIMARY_KEY"
    FOREIGN_KEY = "FOREIGN_KEY"
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    NOT_NULL = "NOT_NULL"


class ValidationStage(str, Enum):
    """5-Stage validation pipeline phases."""
    SYNTAX = "SYNTAX"
    DEPENDENCY = "DEPENDENCY"
    COMPATIBILITY = "COMPATIBILITY"
    EXECUTION_PRECHECK = "EXECUTION_PRECHECK"
    POST_EXECUTION = "POST_EXECUTION"


class LockType(str, Enum):
    """Concurrency lock classifications."""
    GLOBAL_SCHEMA = "GLOBAL_SCHEMA"
    TABLE_EXCLUSIVE = "TABLE_EXCLUSIVE"
    TABLE_SHARED = "TABLE_SHARED"
    ADVISORY = "ADVISORY"


class FailureClass(str, Enum):
    """Failure classification for enterprise recovery management."""
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    EXECUTION_FAILURE = "EXECUTION_FAILURE"
    DATABASE_FAILURE = "DATABASE_FAILURE"
    METADATA_FAILURE = "METADATA_FAILURE"
    CONSTRAINT_FAILURE = "CONSTRAINT_FAILURE"
    REPLAY_FAILURE = "REPLAY_FAILURE"
    RECOVERY_FAILURE = "RECOVERY_FAILURE"
