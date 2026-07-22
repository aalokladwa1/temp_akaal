"""
Policy Engine for Platform 6.
Enforces administrative boundaries (maximum CPU, RAM, concurrency, allowed compression).
"""

from typing import Dict, Any, List, Optional
from threading import RLock


class EnterprisePolicy:
    """Represents a policy gate configuration."""
    def __init__(
        self,
        policy_id: str,
        version: str,
        max_cpu_percent: float = 90.0,
        max_ram_bytes: int = 1024 * 1024 * 1024 * 8,  # 8 GB
        max_workers: int = 16,
        parallelism_allowed: bool = True,
        compression_allowed: bool = True,
        regulatory_restrictions: Optional[List[str]] = None
    ) -> None:
        self.policy_id = policy_id
        self.version = version
        self.max_cpu_percent = max_cpu_percent
        self.max_ram_bytes = max_ram_bytes
        self.max_workers = max_workers
        self.parallelism_allowed = parallelism_allowed
        self.compression_allowed = compression_allowed
        self.regulatory_restrictions = regulatory_restrictions or []


class PolicyEngine:
    """Evaluates recommendations against active enterprise policies."""

    def __init__(self, default_policy: Optional[EnterprisePolicy] = None) -> None:
        self._lock = RLock()
        self._active_policy = default_policy or EnterprisePolicy("policy_default", "1.0")

    def get_active_policy(self) -> EnterprisePolicy:
        with self._lock:
            return self._active_policy

    def update_policy(self, policy: EnterprisePolicy) -> None:
        with self._lock:
            self._active_policy = policy

    def is_permitted(self, recommendation_type: str, requested_params: Dict[str, Any]) -> bool:
        """Determines whether recommended values are permitted under active limits."""
        with self._lock:
            policy = self._active_policy

            # 1. CPU bounds
            cpu_req = requested_params.get("cpu_percent")
            if cpu_req is not None and cpu_req > policy.max_cpu_percent:
                return False

            # 2. RAM limits
            ram_req = requested_params.get("ram_bytes")
            if ram_req is not None and ram_req > policy.max_ram_bytes:
                return False

            # 3. Worker thread count
            workers_req = requested_params.get("worker_count")
            if workers_req is not None and workers_req > policy.max_workers:
                return False

            # 4. Compression allowed check
            if recommendation_type == "compression" and not policy.compression_allowed:
                return False

            # 5. Parallelism allowed check
            if recommendation_type == "parallelism" and not policy.parallelism_allowed:
                return False

            return True
