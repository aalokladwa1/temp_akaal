"""
Typed Exception Hierarchy for Authority #5 — Durability.
"""


class DurabilityError(Exception):
    """Base exception for all Durability Authority failures."""
    pass


class DurabilityConfigError(DurabilityError):
    """Raised when configuration parameters or key materials are missing, invalid, or insecure."""
    pass


class StateNotFoundError(DurabilityError):
    """Raised when a requested state key or namespace does not exist."""
    pass


class StateCorruptError(DurabilityError):
    """Raised when state record checksum or payload integrity fails."""
    pass


class StateVersionUnsupportedError(DurabilityError):
    """Raised when state record version is higher than supported engine version."""
    pass


class BackendUnavailableError(DurabilityError):
    """Raised when storage backend cannot be accessed."""
    pass


class BackendBusyError(DurabilityError):
    """Raised when backend operation times out due to lock contention."""
    pass


class StorageQuotaExceededError(DurabilityError):
    """Raised when storage allocation exceeds configured disk quota limits."""
    pass


class DiskReserveViolatedError(DurabilityError):
    """Raised when free disk space falls below minimum reserved margin."""
    pass


class CheckpointConflictError(DurabilityError):
    """Raised when checkpoint update fails due to version or dependency conflict."""
    pass


class InvalidCheckpointError(DurabilityError):
    """Raised when checkpoint structure or position metadata is malformed."""
    pass


class InvalidResumePositionError(DurabilityError):
    """Raised when resume position marker is corrupted or invalid."""
    pass


class CASConflictError(DurabilityError):
    """Raised when compare-and-swap expected version does not match current version."""
    pass


class StaleGenerationError(DurabilityError):
    """Raised when write request contains an outdated fencing epoch."""
    pass


class FencingViolationError(DurabilityError):
    """Raised when fencing token validation fails or token has expired."""
    pass


class JournalCorruptError(DurabilityError):
    """Raised when operation journal hash chain verification fails."""
    pass


class JournalSequenceConflictError(DurabilityError):
    """Raised when operation journal sequence numbers are non-contiguous."""
    pass


class ReplayDivergenceError(DurabilityError):
    """Raised when operation replay payload hash differs from original journal record."""
    pass


class SpillCorruptError(DurabilityError):
    """Raised when binary spill segment header or checksum verification fails."""
    pass


class PartialSegmentError(DurabilityError):
    """Raised when disk spill segment payload is truncated."""
    pass


class SerializationFailureError(DurabilityError):
    """Raised when record serialization or deserialization fails."""
    pass


class TransactionFailureError(DurabilityError):
    """Raised when atomic durability transaction fails and is rolled back."""
    pass


class IntegrityFailureError(DurabilityError):
    """Raised when data integrity validation fails."""
    pass


class ManifestError(DurabilityError):
    """Raised when execution manifest operations fail."""
    pass


class ManifestAlreadyExistsError(ManifestError):
    """Raised when attempting to overwrite an immutable execution manifest."""
    pass

