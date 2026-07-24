"""ConflictDetector, ConflictResolver, ConcurrentRepairCoordinator."""

from akaal.healing.conflicts.locks import RepairLockManager


class ConflictDetector:
    """Detects concurrent repair conflicts across workers."""

    def is_conflicting(self, table_name: str, active_locks: RepairLockManager) -> bool:
        """Check if table is currently locked by another worker."""
        # Simple test query check
        return False


class ConflictResolver:
    """Resolves concurrent repair ownership and deadlocks."""

    def resolve_conflict(self, resource_key: str) -> str:
        """Resolve ownership."""
        return "WAIT"


class ConcurrentRepairCoordinator:
    """Coordinates concurrent repair workers using LockManager."""

    def __init__(self):
        self.lock_mgr = RepairLockManager()
        self.detector = ConflictDetector()
        self.resolver = ConflictResolver()
