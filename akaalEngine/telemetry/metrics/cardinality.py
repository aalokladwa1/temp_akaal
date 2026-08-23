"""
akaalEngine.telemetry.metrics.cardinality
==========================================
CardinalityGuard enforcing label cardinality bounds and dynamic identifier filtering.
Prevents memory explosion under large-scale workloads (600M+ rows).
"""

import logging
from threading import RLock
from typing import Dict, Mapping, Optional, Tuple, Set

from akaalEngine.telemetry.models.errors import MetricCardinalityExceededError

logger = logging.getLogger("akaalEngine.telemetry.metrics.cardinality")

# High-cardinality dynamic identifiers forbidden in metric labels by default
_FORBIDDEN_LABEL_KEYS: Set[str] = {
    "row_id", "chunk_id", "task_id", "attempt_id", "migration_id", "run_id", "trace_id", "execution_id"
}


class CardinalityGuard:
    """
    Enforces metric label cardinality bounds and dynamic identifier filtering.
    """

    def __init__(self, max_cardinality_per_metric: int = 100) -> None:
        self.max_cardinality_per_metric = max_cardinality_per_metric
        self._tracked_combinations: Dict[str, Set[Tuple[Tuple[str, str], ...]]] = {}
        self._overflow_counts: Dict[str, int] = {}
        self._lock = RLock()

    def filter_labels(self, raw_labels: Optional[Mapping[str, str]]) -> Dict[str, str]:
        """Filters out high-cardinality dynamic identifier keys from metric labels."""
        if not raw_labels:
            return {}
        return {k: str(v) for k, v in raw_labels.items() if k.lower() not in _FORBIDDEN_LABEL_KEYS}

    def check_and_register(self, metric_name: str, labels: Mapping[str, str]) -> Dict[str, str]:
        with self._lock:
            safe_labels = self.filter_labels(labels)
            label_tuple = tuple(sorted(safe_labels.items()))

            tracked = self._tracked_combinations.setdefault(metric_name, set())
            if label_tuple not in tracked:
                if len(tracked) >= self.max_cardinality_per_metric:
                    self._overflow_counts[metric_name] = self._overflow_counts.get(metric_name, 0) + 1
                    logger.warning(
                        f"[CardinalityGuard] Metric '{metric_name}' label combination exceeded limit ({self.max_cardinality_per_metric}). Routing to overflow bucket."
                    )
                    return {"overflow": "true"}
                tracked.add(label_tuple)

            return safe_labels

    def get_overflow_count(self, metric_name: str) -> int:
        with self._lock:
            return self._overflow_counts.get(metric_name, 0)
