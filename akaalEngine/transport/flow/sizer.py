"""
akaalEngine.transport.flow.sizer
================================
AdaptiveTransportSizer dynamically computing optimal fetch & write batch boundaries.
Mined from `akaal/performance/optimizers/batch.py`.
"""

import sys
from typing import Any, Mapping, Sequence

from akaalEngine.transport.models.spec import TransportTuningPolicy


class AdaptiveTransportSizer:
    """Computes memory-bounded optimal batch size based on row payload size and target memory envelope."""

    @classmethod
    def calculate_optimal_batch_size(
        cls,
        sample_rows: Sequence[Mapping[str, Any]],
        tuning_policy: Optional[TransportTuningPolicy] = None,
    ) -> int:
        policy = tuning_policy or TransportTuningPolicy()
        if not sample_rows:
            return policy.min_rows_per_batch

        total_bytes = 0
        for r in sample_rows[:50]:
            row_b = sys.getsizeof(r)
            for k, v in r.items():
                row_b += sys.getsizeof(k) + sys.getsizeof(v)
            total_bytes += row_b

        avg_bytes = total_bytes // max(1, len(sample_rows[:50]))
        avg_bytes = max(256, avg_bytes)

        calculated_rows = policy.target_batch_bytes // avg_bytes
        return max(policy.min_rows_per_batch, min(policy.max_rows_per_batch, calculated_rows))
