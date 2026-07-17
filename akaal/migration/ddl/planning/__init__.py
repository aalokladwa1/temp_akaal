"""
Akaal — Identity Migration Planning Package
============================================
Consolidates and exposes all planning, fallback, naming, scheduling,
and rollback interfaces for Checkpoint 7.
"""

from akaal.migration.ddl.planning.models import (
    DatabaseDialect,
    PlanReadinessStatus,
    ObjectOrigin,
    MutationState,
    PriorStateAvailability,
    NamingProvenance,
    ApprovalState,
    SafetyClassification,
    DependencyType,
    DependencyStatus,
    OperationPhase,
    RollbackClassification,
    DiagnosticSeverity,
    DiagnosticCode,
    ReconstructionStageType,
    ObjectIdentity,
    ObjectInventory,
    SequenceFallbackPlan,
    TriggerFallbackPlan,
    IdentityDiagnostic,
    CycleDiagnostic,
    UnresolvedDependencyDiagnostic,
    ReconstructionStage,
    IdentityReconstructionPlan,
    DependencyNode,
    DependencyGraph,
    ScheduledIdentityPlan,
    RollbackNode,
    RollbackPlan,
    ApprovalContext
)

from akaal.migration.ddl.planning.naming import (
    generate_fallback_name,
    split_qualified_identifier,
    clean_unquoted_component,
    get_dialect_byte_limit,
    validate_identifier_safety
)

from akaal.migration.ddl.planning.sequence_fallback import (
    PostgresSequenceFallbackPlanner,
    OracleSequenceFallbackPlanner
)

from akaal.migration.ddl.planning.trigger_fallback import (
    OracleTriggerFallbackPlanner
)

from akaal.migration.ddl.planning.reconstruction import (
    SQLServerReconstructionPlanner,
    MySQLReconstructionPlanner
)

from akaal.migration.ddl.planning.scheduler import (
    DependencyScheduler
)

from akaal.migration.ddl.planning.rollback import (
    RollbackPlanner
)

from akaal.migration.ddl.planning.partition_rollback import (
    PartitionRollbackPlanner
)

from akaal.migration.ddl.planning.partition_scheduler import (
    PartitionDependencyScheduler
)

from akaal.migration.ddl.planning.partition_planner import (
    PartitionMigrationPlanner
)

from akaal.migration.ddl.planning.partition_models import (
    PlanReadinessStatus as PartitionPlanReadinessStatus,
    DowntimeClassification,
    DataMovementClassification,
    ExecutionPolicy,
    ActionRetryClassification,
    ResourceLockType,
    LockCategory,
    ResourceLock,
    PartitionBaseAction,
    CreatePartitionFunctionAction,
    SplitPartitionAction,
    MergePartitionAction,
    CreatePartitionSchemeAction,
    CreatePartitionedTableAction,
    CreateChildPartitionAction,
    AttachPartitionAction,
    DetachPartitionAction,
    SwitchPartitionAction,
    CreateShadowTableAction,
    CopyPartitionDataAction,
    ValidatePartitionRowsAction,
    ValidateConstraintAction,
    CreateLocalIndexAction,
    CreateGlobalIndexAction,
    RebuildIndexAction,
    MoveStorageAction,
    CaptureCheckpointAction,
    RequireApprovalAction,
    RequireBackupAction,
    CutoverAction,
    CleanupAction,
    RollbackPlan as PartitionRollbackPlan,
    PartitionPlan
)

from akaal.migration.ddl.planning.cdc_planner import (
    CDCPlanner
)
