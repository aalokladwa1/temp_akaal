"""
AKAAL Platform 5 — Domain Core Module
"""

from akaal.schema.domain.errors import (
    SchemaEvolutionError,
    TransactionError,
    ValidationError,
    ReplayError,
    RecoveryError,
    MetadataError,
    ConcurrencyError,
    JournalIntegrityError,
    VersionConflictError,
    IncompatibleSchemaError,
    ExecutionError,
)
from akaal.schema.domain.enums import (
    TransactionState,
    RefreshState,
    EvolutionState,
    ReplayState,
    ReplayStatus,
    ChangeType,
    RiskLevel,
    ConstraintType,
    ValidationStage,
    LockType,
    FailureClass,
)
from akaal.schema.domain.identifiers import (
    VersionID,
    SnapshotID,
    TransactionID,
    OperationID,
    CheckpointID,
    SchemaIdentifier,
)
from akaal.schema.domain.changes import BaseSchemaChange, DDLStatement, ValidationResult, AddTable, DropTable, AddColumn, DropColumn
from akaal.schema.domain.journal import OperationRecord, JournalChecksum
from akaal.schema.domain.models import (
    CanonicalObjectIdentity,
    CanonicalColumn,
    CanonicalPrimaryKey,
    CanonicalForeignKey,
    CanonicalUniqueConstraint,
    CanonicalCheckConstraint,
    CanonicalDefault,
    CanonicalIndex,
    CanonicalSequence,
    CanonicalIdentity,
    CanonicalPartition,
    CanonicalView,
    CanonicalMaterializedView,
    CanonicalProcedure,
    CanonicalFunction,
    CanonicalTrigger,
    CanonicalTable,
    CanonicalSchemaModel,
)
from akaal.schema.domain.types import (
    CanonicalTypeCategory,
    ConversionSafety,
    CanonicalType,
    TargetTypeEmission,
)
from akaal.schema.domain.type_registry import CanonicalTypeRegistry
from akaal.schema.domain.ddl_emitter import (
    StructuredDDLArtifact,
    BaseTargetDDLEmitter,
    UniversalDDLAuthority,
)

__all__ = [
    "SchemaEvolutionError",
    "TransactionError",
    "ValidationError",
    "ReplayError",
    "RecoveryError",
    "MetadataError",
    "ConcurrencyError",
    "JournalIntegrityError",
    "VersionConflictError",
    "IncompatibleSchemaError",
    "ExecutionError",
    "TransactionState",
    "RefreshState",
    "EvolutionState",
    "ReplayState",
    "ReplayStatus",
    "ChangeType",
    "RiskLevel",
    "ConstraintType",
    "ValidationStage",
    "LockType",
    "FailureClass",
    "VersionID",
    "SnapshotID",
    "TransactionID",
    "OperationID",
    "CheckpointID",
    "SchemaIdentifier",
    "BaseSchemaChange",
    "DDLStatement",
    "ValidationResult",
    "AddTable",
    "DropTable",
    "AddColumn",
    "DropColumn",
    "OperationRecord",
    "JournalChecksum",
]
