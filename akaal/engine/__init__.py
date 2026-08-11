"""
AKAAL Enterprise Migration Engine — Canonical Production Package
==================================================================
Native Python execution core for air-gapped database discovery,
planning, partitioning, parallel transport, WAL checkpointing,
physical validation, and audit certification.
"""

from akaal.engine.api import AkaalMigrationEngine
from akaal.engine.facade import (
    AkaalSuperEngine,
    SuperEngineError,
    ApprovalRequiredError,
    PlanFingerprintMissingError,
    PlanFingerprintMismatchError,
    PhysicalExecutionContractError,
    PhysicalValidationContractError,
)
from akaal.engine.spec import (
    MigrationSpecification,
    ExecutionPlan,
    TransportPartition,
    PartitionStrategy,
    PartitionState,
    BatchState,
    BatchMetadata,
    TuningPolicy,
    ValidationPolicy,
    RecoveryPolicy,
    MigrationState,
    ValidationLevel,
)

__all__ = [
    "AkaalSuperEngine",
    "SuperEngineError",
    "ApprovalRequiredError",
    "PlanFingerprintMissingError",
    "PlanFingerprintMismatchError",
    "PhysicalExecutionContractError",
    "PhysicalValidationContractError",
    "AkaalMigrationEngine",
    "MigrationSpecification",
    "ExecutionPlan",
    "TransportPartition",
    "PartitionStrategy",
    "PartitionState",
    "BatchState",
    "BatchMetadata",
    "TuningPolicy",
    "ValidationPolicy",
    "RecoveryPolicy",
    "MigrationState",
    "ValidationLevel",
]
