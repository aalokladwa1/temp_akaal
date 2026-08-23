"""
akaalEngine.transport.models.capabilities
==========================================
Enums and dataclasses defining capabilities, resumability modes, idempotency modes, and checksum scopes.
"""

from dataclasses import dataclass
from enum import Enum


class ResumabilityMode(str, Enum):
    EXACT_RESUME = "EXACT_RESUME"
    PROVIDER_RESUMABLE = "PROVIDER_RESUMABLE"
    SESSION_LOCAL_ONLY = "SESSION_LOCAL_ONLY"
    RESTART_SOURCE = "RESTART_SOURCE"
    RESTART_LOB = "RESTART_LOB"
    RESTART_FILE = "RESTART_FILE"
    NON_RESUMABLE = "NON_RESUMABLE"
    UNKNOWN = "UNKNOWN"


class IdempotencyMode(str, Enum):
    STATE_IDEMPOTENT = "STATE_IDEMPOTENT"
    OPERATION_IDEMPOTENT = "OPERATION_IDEMPOTENT"
    CONDITIONALLY_IDEMPOTENT = "CONDITIONALLY_IDEMPOTENT"
    NON_IDEMPOTENT = "NON_IDEMPOTENT"
    UNKNOWN = "UNKNOWN"


class CommitOutcomeState(str, Enum):
    NOT_COMMITTED = "NOT_COMMITTED"
    COMMITTED = "COMMITTED"
    UNKNOWN_COMMIT_OUTCOME = "UNKNOWN_COMMIT_OUTCOME"


class CancellationCapability(str, Enum):
    NATIVE_CANCEL = "NATIVE_CANCEL"
    COOPERATIVE_STOP = "COOPERATIVE_STOP"
    CLOSE_CONNECTION = "CLOSE_CONNECTION"
    NOT_SUPPORTED = "NOT_SUPPORTED"


class ChecksumScope(str, Enum):
    SERIALIZED_UNCOMPRESSED_PAYLOAD = "SERIALIZED_UNCOMPRESSED_PAYLOAD"
    SERIALIZED_COMPRESSED_PAYLOAD = "SERIALIZED_COMPRESSED_PAYLOAD"
    OBJECT_PART_BYTES = "OBJECT_PART_BYTES"
    FILE_BYTES = "FILE_BYTES"


class LOBMode(str, Enum):
    TRUE_STREAMING = "TRUE_STREAMING"
    BOUNDED_MATERIALIZATION = "BOUNDED_MATERIALIZATION"
    FULL_MATERIALIZATION = "FULL_MATERIALIZATION"


@dataclass(frozen=True)
class ProviderCapabilities:
    """Capability descriptor for a provider driver."""
    bulk_read: bool = False
    bulk_write: bool = False
    lob_read: LOBMode = LOBMode.BOUNDED_MATERIALIZATION
    lob_write: LOBMode = LOBMode.BOUNDED_MATERIALIZATION
    cancellation: CancellationCapability = CancellationCapability.COOPERATIVE_STOP
    idempotency: IdempotencyMode = IdempotencyMode.NON_IDEMPOTENT
    resumability: ResumabilityMode = ResumabilityMode.SESSION_LOCAL_ONLY
