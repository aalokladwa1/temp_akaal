"""Distributed Concurrency Lease Locks for Workflow Execution."""

import threading
import time
from akaal.workflow.exceptions import LockAcquisitionException
from akaal.workflow.interfaces.base import IWorkflowLock


class InMemoryLock(IWorkflowLock):
    """In-memory thread-safe workflow lease lock with expiration TTL support."""

    def __init__(self) -> None:
        self._locks: dict[str, float] = {}  # workflow_id -> expiration timestamp
        self._mutex = threading.Lock()

    def acquire_lock(self, workflow_id: str, ttl_seconds: int = 30) -> bool:
        with self._mutex:
            now = time.time()
            expires = self._locks.get(workflow_id)
            if expires is not None and now < expires:
                # Lock is currently held and not expired
                return False

            # Lock acquired
            self._locks[workflow_id] = now + ttl_seconds
            return True

    def release_lock(self, workflow_id: str) -> None:
        with self._mutex:
            self._locks.pop(workflow_id, None)
