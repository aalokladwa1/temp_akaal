"""ConcurrentRepairCoordinator for coordinating concurrent repair workers."""

from akaal.healing.conflicts.locks import RepairLockManager
from akaal.healing.conflicts.detector import ConflictDetector
from akaal.healing.conflicts.resolver import ConflictResolver


class ConcurrentRepairCoordinator:
    """Coordinates concurrent repair workers using LockManager."""

    def __init__(self):
        self.lock_mgr = RepairLockManager()
        self.detector = ConflictDetector()
        self.resolver = ConflictResolver()
