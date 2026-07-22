"""
Enterprise Health Engine.
Calculates continuous weighted health ratings across platforms, workers, clusters, and migrations.
"""

from typing import Dict, Any
from threading import RLock


class OperationsHealthEngine:
    """Computes weighted platform health and overall system health score."""

    DEFAULT_WEIGHTS = {
        "Platform1": 0.25,  # Workflow Orchestration Engine
        "Platform2": 0.25,  # Distributed Runtime
        "Platform3": 0.20,  # Zero-Copy Streaming
        "Platform5": 0.15,  # Schema Evolution
        "Platform6": 0.15,  # Performance Engine
    }

    def __init__(self, weights: Dict[str, float] = None) -> None:
        self._lock = RLock()
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)
        self.scores: Dict[str, float] = {pid: 100.0 for pid in self.weights}

    def update_score(self, platform_id: str, score: float) -> float:
        with self._lock:
            self.scores[platform_id] = max(0.0, min(100.0, score))
            return self.compute_overall_health()

    def compute_overall_health(self) -> float:
        with self._lock:
            total_weight = sum(self.weights.get(pid, 0.1) for pid in self.scores)
            if total_weight <= 0:
                return 100.0
            
            weighted_sum = sum(
                score * self.weights.get(pid, 0.1)
                for pid, score in self.scores.items()
            )
            return round(weighted_sum / total_weight, 2)

    def get_health_breakdown(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "overall_score": self.compute_overall_health(),
                "platform_scores": dict(self.scores),
                "weights": dict(self.weights)
            }
