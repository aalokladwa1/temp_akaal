"""
akaalEngine.data_processing.batching.sizer
===========================================
AdaptiveBatchSizer dynamically computing optimal row and byte batch boundaries.
Mined from `akaal/advisor/analyzers/batch_analyzer.py`.
"""

import sys
from typing import Any, Mapping, Sequence


class AdaptiveBatchSizer:
    """
    Computes optimal data processing batch sizing based on row width, memory envelope, and latency.
    """

    @classmethod
    def estimate_row_size_bytes(cls, sample_rows: Sequence[Mapping[str, Any]]) -> int:
        if not sample_rows:
            return 1024  # Default 1KB fallback

        total_bytes = 0
        for row in sample_rows[:50]:
            row_bytes = sys.getsizeof(row)
            for k, v in row.items():
                row_bytes += sys.getsizeof(k) + sys.getsizeof(v)
            total_bytes += row_bytes

        avg_bytes = total_bytes // max(1, len(sample_rows[:50]))
        return max(256, avg_bytes)

    @classmethod
    def calculate_optimal_batch_size(
        cls,
        sample_rows: Sequence[Mapping[str, Any]],
        target_memory_envelope_bytes: int = 16 * 1024 * 1024,  # Default 16MB per batch
        min_rows: int = 100,
        max_rows: int = 50000,
    ) -> int:
        avg_row_bytes = cls.estimate_row_size_bytes(sample_rows)
        calculated_rows = target_memory_envelope_bytes // avg_row_bytes
        return max(min_rows, min(max_rows, calculated_rows))
