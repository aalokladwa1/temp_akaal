"""
Akaal — Decoder Metrics Collector
=================================
Operational metrics collector for Decoder Platform pipeline execution.
Integrates with akaal.metrics.registry.
"""

from typing import Dict, Any, Optional
from akaal.metrics.registry import MetricsRegistry


class DecoderMetrics:
    """Operational metrics collector for Decoder Platform."""

    def __init__(self, registry: Optional[MetricsRegistry] = None) -> None:
        self.registry = registry or MetricsRegistry()
        self.objects_normalized: int = 0
        self.types_converted: int = 0
        self.expressions_normalized: int = 0
        self.compatibility_checks: int = 0
        self.warnings_count: int = 0
        self.validation_failures: int = 0

        self.normalization_time_ms: float = 0.0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.dependency_depth: int = 0

    def record_normalization_time(self, duration_ms: float) -> None:
        self.normalization_time_ms = duration_ms

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1

    @property
    def cache_hit_ratio(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objects_normalized": self.objects_normalized,
            "types_converted": self.types_converted,
            "expressions_normalized": self.expressions_normalized,
            "compatibility_checks": self.compatibility_checks,
            "warnings_count": self.warnings_count,
            "validation_failures": self.validation_failures,
            "normalization_time_ms": round(self.normalization_time_ms, 2),
            "cache_hit_ratio_percentage": round(self.cache_hit_ratio, 2),
            "dependency_depth": self.dependency_depth,
        }
