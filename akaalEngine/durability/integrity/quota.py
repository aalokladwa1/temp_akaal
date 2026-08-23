"""
Storage Quota & Capacity State Monitor for Authority #5 — Durability (DUR-012).
"""

import os
import shutil
from typing import Dict, Any, Tuple
from akaalEngine.durability.models.errors import StorageQuotaExceededError, DiskReserveViolatedError


class StorageQuotaMonitor:
    """Monitors storage directory size against quota and reserve limits."""

    def __init__(self, storage_dir: str, quota_bytes: int, reserve_bytes: int) -> None:
        self.storage_dir = storage_dir
        self.quota_bytes = quota_bytes
        self.reserve_bytes = reserve_bytes

    def get_current_storage_usage(self) -> int:
        """Returns total bytes used by files in the storage directory."""
        if not os.path.exists(self.storage_dir):
            return 0
        total_size = 0
        for dirpath, _, filenames in os.walk(self.storage_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def get_free_disk_space(self) -> int:
        """Returns free disk space available on the target storage partition."""
        if not os.path.exists(self.storage_dir):
            parent = os.path.dirname(os.path.abspath(self.storage_dir))
            usage = shutil.disk_usage(parent if os.path.exists(parent) else os.getcwd())
        else:
            usage = shutil.disk_usage(self.storage_dir)
        return usage.free

    def validate_allocation(self, required_bytes: int) -> None:
        """Validates that writing required_bytes will not violate quota or free space reserve."""
        current_usage = self.get_current_storage_usage()
        if current_usage + required_bytes > self.quota_bytes:
            raise StorageQuotaExceededError(
                f"Storage allocation of {required_bytes} bytes exceeds quota limit. "
                f"Used: {current_usage}, Quota: {self.quota_bytes}."
            )

        free_space = self.get_free_disk_space()
        if free_space - required_bytes < self.reserve_bytes:
            raise DiskReserveViolatedError(
                f"Storage allocation of {required_bytes} bytes violates minimum reserve margin. "
                f"Free: {free_space}, Reserve: {self.reserve_bytes}."
            )

    def get_capacity_facts(self) -> Dict[str, Any]:
        """Returns current capacity and usage facts."""
        used = self.get_current_storage_usage()
        free = self.get_free_disk_space()
        return {
            "used_bytes": used,
            "quota_bytes": self.quota_bytes,
            "reserve_bytes": self.reserve_bytes,
            "free_bytes": free,
            "quota_utilized_pct": round((used / self.quota_bytes) * 100.0, 2) if self.quota_bytes > 0 else 0.0,
        }
