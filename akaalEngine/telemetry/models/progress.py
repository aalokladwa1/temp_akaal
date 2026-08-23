"""
akaalEngine.telemetry.models.progress
======================================
Progress models with truthful UNKNOWN denominator handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Truthful UNKNOWN sentinel constant
UNKNOWN_TOTAL = -1


@dataclass(frozen=True)
class ProgressSnapshot:
    """
    Immutable progress snapshot for a migration or job.
    Strictly reports UNKNOWN when total counts are mathematically unknown.
    """
    migration_id: str
    objects_completed: int = 0
    objects_total: int = UNKNOWN_TOTAL
    rows_processed: int = 0
    rows_total: int = UNKNOWN_TOTAL
    bytes_processed: int = 0
    bytes_total: int = UNKNOWN_TOTAL
    chunks_completed: int = 0
    chunks_total: int = UNKNOWN_TOTAL
    elapsed_seconds: float = 0.0
    rows_per_second: float = 0.0
    bytes_per_second: float = 0.0
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def rows_remaining(self) -> Optional[int]:
        if self.rows_total == UNKNOWN_TOTAL:
            return None
        return max(0, self.rows_total - self.rows_processed)

    @property
    def percentage(self) -> Optional[float]:
        if self.rows_total == UNKNOWN_TOTAL or self.rows_total <= 0:
            return None
        return min(100.0, round((self.rows_processed / float(self.rows_total)) * 100.0, 2))

    @property
    def eta_seconds(self) -> Optional[float]:
        rem = self.rows_remaining
        if rem is None or self.rows_per_second <= 0:
            return None
        return round(rem / self.rows_per_second, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "objects_completed": self.objects_completed,
            "objects_total": None if self.objects_total == UNKNOWN_TOTAL else self.objects_total,
            "rows_processed": self.rows_processed,
            "rows_total": None if self.rows_total == UNKNOWN_TOTAL else self.rows_total,
            "rows_remaining": self.rows_remaining,
            "bytes_processed": self.bytes_processed,
            "bytes_total": None if self.bytes_total == UNKNOWN_TOTAL else self.bytes_total,
            "chunks_completed": self.chunks_completed,
            "chunks_total": None if self.chunks_total == UNKNOWN_TOTAL else self.chunks_total,
            "elapsed_seconds": self.elapsed_seconds,
            "rows_per_second": self.rows_per_second,
            "bytes_per_second": self.bytes_per_second,
            "percentage": self.percentage,
            "eta_seconds": self.eta_seconds,
            "updated_at": self.updated_at,
        }
