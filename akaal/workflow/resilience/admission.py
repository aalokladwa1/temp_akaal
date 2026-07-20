"""Admission Controller for Edge Request Validation and Rate Limiting."""

import threading
from typing import Tuple


class AdmissionController:
    """Edge admission controller validating tenant quotas and platform load prior to execution."""

    def __init__(self, max_concurrent_requests: int = 500) -> None:
        self.max_concurrent_requests = max_concurrent_requests
        self._active_requests: int = 0
        self._lock = threading.Lock()

    def evaluate_request(self, tenant_id: str, priority: int = 40) -> Tuple[bool, str]:
        """Evaluate incoming workflow submission request."""
        with self._lock:
            if self._active_requests >= self.max_concurrent_requests and priority < 80:
                return False, "Platform capacity exceeded. Request rejected by AdmissionController."
            self._active_requests += 1
            return True, "Request admitted."

    def release_request(self) -> None:
        with self._lock:
            if self._active_requests > 0:
                self._active_requests -= 1
