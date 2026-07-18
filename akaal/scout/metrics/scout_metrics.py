"""
Akaal — Scout Metrics Collector
================================
Tracks Scout metrics including throughput, latencies, cache hits/misses, failures, policy violations.
Integrates with akaal.metrics.registry.
"""

from typing import Dict, List, Optional
from akaal.metrics.registry import MetricsRegistry


class ScoutMetrics:
    """Collector for Scout discovery operations."""

    def __init__(self, registry: Optional[MetricsRegistry] = None) -> None:
        self.registry = registry or MetricsRegistry()
        self.total_duration_ms: float = 0.0
        self.stage_durations: Dict[str, float] = {}
        self.schemas_discovered: int = 0
        self.objects_discovered: int = 0
        self.metadata_query_count: int = 0
        self.metadata_query_total_ms: float = 0.0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.failures_count: int = 0

        self.stage_retry_count: int = 0
        self.provider_execution_time_ms: float = 0.0
        self.policy_violations: int = 0
        self.skipped_objects: int = 0
        self.skipped_schemas: int = 0
        self.warning_categories: Dict[str, int] = {}

    def record_stage_duration(self, stage_name: str, duration_ms: float) -> None:
        self.stage_durations[stage_name] = duration_ms

    def record_query(self, duration_ms: float) -> None:
        self.metadata_query_count += 1
        self.metadata_query_total_ms += duration_ms

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1

    def record_failure(self) -> None:
        self.failures_count += 1

    def record_skipped_object(self) -> None:
        self.skipped_objects += 1

    def record_policy_violation(self) -> None:
        self.policy_violations += 1

    @property
    def avg_query_latency_ms(self) -> float:
        if self.metadata_query_count == 0:
            return 0.0
        return self.metadata_query_total_ms / self.metadata_query_count

    @property
    def queries_per_sec(self) -> float:
        if self.total_duration_ms <= 0:
            return 0.0
        return (self.metadata_query_count / self.total_duration_ms) * 1000.0

    @property
    def schemas_per_sec(self) -> float:
        if self.total_duration_ms <= 0:
            return 0.0
        return (self.schemas_discovered / self.total_duration_ms) * 1000.0

    @property
    def objects_per_sec(self) -> float:
        if self.total_duration_ms <= 0:
            return 0.0
        return (self.objects_discovered / self.total_duration_ms) * 1000.0

    @property
    def failure_percentage(self) -> float:
        total_stages = len(self.stage_durations)
        if total_stages == 0:
            return 0.0
        return (self.failures_count / total_stages) * 100.0

    @property
    def cache_utilization(self) -> float:
        total_requests = self.cache_hits + self.cache_misses
        if total_requests == 0:
            return 0.0
        return (self.cache_hits / total_requests) * 100.0
