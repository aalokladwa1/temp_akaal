"""
Authority #5 — Durability Engine Package.
"""

from akaalEngine.durability.models import (
    DurabilityConfig,
    StateRecord,
    StateVersion,
    MigrationCheckpoint,
    TableCheckpoint,
    RowPosition,
    RowPositionType,
    OperationRecord,
    JournalBatch,
    QueueMessageRef,
    ClaimLeaseState,
    FencingToken,
    LeaseEpoch,
    ExecutionManifest,
    CDCOffsetDurabilitySeam,
    TransportCheckpointSeam,
    RuntimeFencingSeam,
    ValidationCheckpointSeam,
    DurabilityError,
    DurabilityConfigError,
    StateNotFoundError,
    StateCorruptError,
    StateVersionUnsupportedError,
    BackendUnavailableError,
    BackendBusyError,
    StorageQuotaExceededError,
    DiskReserveViolatedError,
    CheckpointConflictError,
    InvalidCheckpointError,
    InvalidResumePositionError,
    CASConflictError,
    StaleGenerationError,
    FencingViolationError,
    JournalCorruptError,
    JournalSequenceConflictError,
    ReplayDivergenceError,
    SpillCorruptError,
    PartialSegmentError,
    SerializationFailureError,
    TransactionFailureError,
    IntegrityFailureError,
    ManifestError,
    ManifestAlreadyExistsError,
)
from akaalEngine.durability.api import DurabilityAuthority
from akaalEngine.durability.store.base import BaseDurableStorageBackend, StorageBackendCapabilities
from akaalEngine.durability.store.sqlite import SQLiteWalBackend
from akaalEngine.durability.store.cas import StateCasCoordinator
from akaalEngine.durability.checkpoint.position import RowPositionTracker
from akaalEngine.durability.checkpoint.registry import MigrationCheckpointRegistry
from akaalEngine.durability.journal.store import OperationJournalStore
from akaalEngine.durability.journal.compaction import JournalCompactionEngine
from akaalEngine.durability.recovery.idempotency import IdempotencyRegistry, IdempotencyState
from akaalEngine.durability.recovery.inspector import RecoveryStateInspector, DurableRecoverySnapshot
from akaalEngine.durability.spill.spooler import BoundedDiskSpooler, SpilledSegmentRef
from akaalEngine.durability.spill.queue_store import DurableQueueStore
from akaalEngine.durability.fencing.manager import FencingTokenManager
from akaalEngine.durability.integrity.sanitizer import StateIntegritySanitizer
from akaalEngine.durability.integrity.secret_filter import SecretSanitizationFilter
from akaalEngine.durability.integrity.quota import StorageQuotaMonitor

__all__ = [
    "DurabilityAuthority",
    "DurabilityConfig",
    "StateRecord",
    "StateVersion",
    "MigrationCheckpoint",
    "TableCheckpoint",
    "RowPosition",
    "RowPositionType",
    "OperationRecord",
    "JournalBatch",
    "IdempotencyState",
    "SpilledSegmentRef",
    "QueueMessageRef",
    "ClaimLeaseState",
    "FencingToken",
    "LeaseEpoch",
    "ExecutionManifest",
    "DurableRecoverySnapshot",
    "CDCOffsetDurabilitySeam",
    "TransportCheckpointSeam",
    "RuntimeFencingSeam",
    "ValidationCheckpointSeam",
    "BaseDurableStorageBackend",
    "StorageBackendCapabilities",
    "SQLiteWalBackend",
    "StateCasCoordinator",
    "RowPositionTracker",
    "MigrationCheckpointRegistry",
    "OperationJournalStore",
    "JournalCompactionEngine",
    "IdempotencyRegistry",
    "RecoveryStateInspector",
    "BoundedDiskSpooler",
    "DurableQueueStore",
    "FencingTokenManager",
    "StateIntegritySanitizer",
    "SecretSanitizationFilter",
    "StorageQuotaMonitor",
    "DurabilityError",
    "DurabilityConfigError",

    "StateNotFoundError",
    "StateCorruptError",
    "StateVersionUnsupportedError",
    "BackendUnavailableError",
    "BackendBusyError",
    "StorageQuotaExceededError",
    "DiskReserveViolatedError",
    "CheckpointConflictError",
    "InvalidCheckpointError",
    "InvalidResumePositionError",
    "CASConflictError",
    "StaleGenerationError",
    "FencingViolationError",
    "JournalCorruptError",
    "JournalSequenceConflictError",
    "ReplayDivergenceError",
    "SpillCorruptError",
    "PartialSegmentError",
    "SerializationFailureError",
    "TransactionFailureError",
    "IntegrityFailureError",
    "ManifestError",
    "ManifestAlreadyExistsError",
]
