"""
Distributed / Local Idempotency Engine for Write API Protection.
"""

from typing import Any, Dict, Optional, Tuple
import time

from akaal.api.contracts.errors import IdempotencyError


class IdempotencyManager:
    """Manages Idempotency Locks and Cached Write Responses."""

    def __init__(self, lock_ttl_seconds: int = 60, result_ttl_seconds: int = 86400) -> None:
        self.lock_ttl_seconds = lock_ttl_seconds
        self.result_ttl_seconds = result_ttl_seconds
        # Key -> {"status": "IN_PROGRESS" | "COMPLETED", "created_at": float, "response": (status_code, body)}
        self._store: Dict[str, Dict[str, Any]] = {}

    def acquire_or_get_cached(self, key: str) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Check idempotency key state.
        If COMPLETED -> returns cached (status_code, response_dict).
        If IN_PROGRESS -> raises IdempotencyError (409 Conflict).
        If new -> locks key as IN_PROGRESS and returns None.
        """
        now = time.time()
        if key in self._store:
            entry = self._store[key]
            status = entry["status"]
            created_at = entry["created_at"]

            if status == "IN_PROGRESS":
                if now - created_at < self.lock_ttl_seconds:
                    raise IdempotencyError(
                        f"Idempotency key '{key}' is currently being processed by a concurrent request.",
                        details={"idempotency_key": key},
                    )
                else:
                    # Lock expired, reset
                    pass
            elif status == "COMPLETED":
                if now - created_at < self.result_ttl_seconds:
                    return entry["response"]

        # Register IN_PROGRESS lock
        self._store[key] = {"status": "IN_PROGRESS", "created_at": now, "response": None}
        return None

    def save_response(self, key: str, status_code: int, response_data: Dict[str, Any]) -> None:
        """Store completed write response against idempotency key."""
        self._store[key] = {
            "status": "COMPLETED",
            "created_at": time.time(),
            "response": (status_code, response_data),
        }
