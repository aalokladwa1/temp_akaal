"""
Akaal — Rulebook Metrics Collector
==================================
Operational metrics collector for Rulebook pipeline execution.
Integrates with akaal.metrics.registry.
"""

from typing import Dict, Any, Optional
from akaal.metrics.registry import MetricsRegistry


class RulebookMetrics:
    """Operational metrics collector for Rulebook Platform."""

    def __init__(self, registry: Optional[MetricsRegistry] = None) -> None:
        self.registry = registry or MetricsRegistry()
        self.registry_size: int = 0
        self.pack_count: int = 0
        self.rules_loaded: int = 0
        self.rules_applied: int = 0
        self.rules_skipped: int = 0
        self.rules_deprecated: int = 0

        self.resolution_latency_ms: float = 0.0
        self.max_resolution_time_ms: float = 0.0
        self.simulation_time_ms: float = 0.0

        self.cache_hits: int = 0
        self.cache_misses: int = 0

        self.dependency_depth: int = 0
        self.inheritance_depth: int = 0
        self.conflict_frequency: int = 0
        self.validation_failures: int = 0

    def record_resolution_time(self, duration_ms: float) -> None:
        self.resolution_latency_ms = duration_ms
        if duration_ms > self.max_resolution_time_ms:
            self.max_resolution_time_ms = duration_ms

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
            "registry_size": self.registry_size,
            "pack_count": self.pack_count,
            "rules_loaded": self.rules_loaded,
            "rules_applied": self.rules_applied,
            "rules_skipped": self.rules_skipped,
            "rules_deprecated": self.rules_deprecated,
            "resolution_latency_ms": round(self.resolution_latency_ms, 2),
            "max_resolution_time_ms": round(self.max_resolution_time_ms, 2),
            "simulation_time_ms": round(self.simulation_time_ms, 2),
            "cache_hit_ratio_percentage": round(self.cache_hit_ratio, 2),
            "dependency_depth": self.dependency_depth,
            "inheritance_depth": self.inheritance_depth,
            "conflict_frequency": self.conflict_frequency,
            "validation_failures": self.validation_failures,
        }
