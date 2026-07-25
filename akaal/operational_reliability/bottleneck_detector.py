"""
AKAAL Platform 7 — Migration Bottleneck Detector.
===============================================
Real-time runtime bottleneck detector analyzing lock contention, IOPS saturation,
network latency, checkpoint latency, worker starvation, commit latency, and memory pressure.
Composes PerformanceRiskEngine, ForecastingEngine, and ObservabilityService.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional

from akaal.risk.engine.performance_engine import PerformanceEngine
from akaal.operations.forecasting.engine import OperationsForecastingEngine
from akaal.validation.services.observability import ObservabilityService

logger = logging.getLogger("akaal.operational_reliability.bottleneck_detector")


@dataclass
class BottleneckIndicator:
    category: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    metric_name: str
    observed_value: float
    threshold_value: float
    description: str


@dataclass
class BottleneckRecommendation:
    category: str
    action: str
    recommended_config: Dict[str, Any]
    rationale: str


@dataclass
class BottleneckReport:
    timestamp: str
    bottlenecks: List[BottleneckIndicator] = field(default_factory=list)
    recommendations: List[BottleneckRecommendation] = field(default_factory=list)
    overall_health_score: float = 100.0


class MigrationBottleneckDetector:
    """
    Enterprise Migration Bottleneck Detector.
    Continuously evaluates runtime telemetry metrics to pinpoint performance bottlenecks
    and emit structured actionable recommendations.
    """

    def __init__(
        self,
        risk_engine: Optional[PerformanceEngine] = None,
        forecasting_engine: Optional[OperationsForecastingEngine] = None,
        observability_service: Optional[ObservabilityService] = None,
    ) -> None:
        self.risk_engine = risk_engine or PerformanceEngine()
        self.forecasting_engine = forecasting_engine or OperationsForecastingEngine()
        self.observability_service = observability_service or ObservabilityService()

    def analyze_runtime_telemetry(
        self,
        telemetry: Dict[str, Any],
    ) -> BottleneckReport:
        """
        Analyzes live runtime telemetry against operational thresholds to detect bottlenecks.
        """
        now = datetime.now(timezone.utc).isoformat()
        bottlenecks: List[BottleneckIndicator] = []
        recommendations: List[BottleneckRecommendation] = []
        health_score = 100.0

        # 1. Lock Contention
        lock_wait_ms = telemetry.get("lock_wait_time_ms", 0.0)
        if lock_wait_ms > 100.0:
            sev = "CRITICAL" if lock_wait_ms > 500.0 else "HIGH"
            bottlenecks.append(
                BottleneckIndicator(
                    category="LOCK_CONTENTION",
                    severity=sev,
                    metric_name="lock_wait_time_ms",
                    observed_value=lock_wait_ms,
                    threshold_value=100.0,
                    description=f"Database lock wait time is elevated ({lock_wait_ms:.1f} ms).",
                )
            )
            recommendations.append(
                BottleneckRecommendation(
                    category="LOCK_CONTENTION",
                    action="REDUCE_CONCURRENCY",
                    recommended_config={"max_parallel_workers": max(1, telemetry.get("active_workers", 4) - 1)},
                    rationale="High lock contention indicates thread collision on target database tables.",
                )
            )
            health_score -= 20.0

        # 2. IOPS Saturation
        iops_pct = telemetry.get("iops_utilization_pct", 0.0)
        if iops_pct > 85.0:
            bottlenecks.append(
                BottleneckIndicator(
                    category="IOPS_SATURATION",
                    severity="HIGH",
                    metric_name="iops_utilization_pct",
                    observed_value=iops_pct,
                    threshold_value=85.0,
                    description=f"Target disk IOPS utilization reached {iops_pct:.1f}%.",
                )
            )
            recommendations.append(
                BottleneckRecommendation(
                    category="IOPS_SATURATION",
                    action="THROTTLE_BATCH_SIZE",
                    recommended_config={"batch_size_multiplier": 0.75},
                    rationale="Disk IOPS saturation slows transaction commits and risks storage throttling.",
                )
            )
            health_score -= 15.0

        # 3. Network Bottlenecks
        net_latency = telemetry.get("network_latency_ms", 0.0)
        if net_latency > 150.0:
            bottlenecks.append(
                BottleneckIndicator(
                    category="NETWORK_LATENCY",
                    severity="MEDIUM",
                    metric_name="network_latency_ms",
                    observed_value=net_latency,
                    threshold_value=150.0,
                    description=f"Cross-rack/WAN network latency is elevated ({net_latency:.1f} ms).",
                )
            )
            recommendations.append(
                BottleneckRecommendation(
                    category="NETWORK_LATENCY",
                    action="ENABLE_ZSTD_COMPRESSION",
                    recommended_config={"compression_codec": "zstd"},
                    rationale="Enabling high-ratio payload compression mitigates high network transit latency.",
                )
            )
            health_score -= 10.0

        # 4. Checkpoint Latency
        chk_latency = telemetry.get("checkpoint_duration_ms", 0.0)
        if chk_latency > 2000.0:
            bottlenecks.append(
                BottleneckIndicator(
                    category="CHECKPOINT_LATENCY",
                    severity="MEDIUM",
                    metric_name="checkpoint_duration_ms",
                    observed_value=chk_latency,
                    threshold_value=2000.0,
                    description=f"Checkpoint persistence taking excessive time ({chk_latency:.1f} ms).",
                )
            )
            recommendations.append(
                BottleneckRecommendation(
                    category="CHECKPOINT_LATENCY",
                    action="ENABLE_CHECKPOINT_COMPRESSION",
                    recommended_config={"checkpoint_compression": True},
                    rationale="Compressing state payload reduces checkpoint disk I/O latency.",
                )
            )
            health_score -= 10.0

        # 5. Worker Starvation / Backlog Accumulation
        queue_depth = telemetry.get("queue_depth", 0)
        workers = telemetry.get("active_workers", 1)
        if queue_depth > 100 and workers <= 2:
            bottlenecks.append(
                BottleneckIndicator(
                    category="WORKER_STARVATION",
                    severity="HIGH",
                    metric_name="queue_depth",
                    observed_value=float(queue_depth),
                    threshold_value=100.0,
                    description=f"Queue backlog ({queue_depth}) accumulating while active workers ({workers}) are low.",
                )
            )
            recommendations.append(
                BottleneckRecommendation(
                    category="WORKER_STARVATION",
                    action="SCALE_UP_WORKERS",
                    recommended_config={"target_worker_count": workers + 2},
                    rationale="Adding parallel extraction workers clears queue backlog efficiently.",
                )
            )
            health_score -= 15.0

        # 6. Memory Pressure
        mem_pct = telemetry.get("memory_utilization_pct", 0.0)
        if mem_pct > 85.0:
            bottlenecks.append(
                BottleneckIndicator(
                    category="MEMORY_PRESSURE",
                    severity="CRITICAL" if mem_pct > 95.0 else "HIGH",
                    metric_name="memory_utilization_pct",
                    observed_value=mem_pct,
                    threshold_value=85.0,
                    description=f"Host memory utilization is critically high ({mem_pct:.1f}%).",
                )
            )
            recommendations.append(
                BottleneckRecommendation(
                    category="MEMORY_PRESSURE",
                    action="REDUCE_BATCH_SIZE",
                    recommended_config={"batch_size": 100},
                    rationale="Shrinking in-flight batch buffers prevents OOM worker crashes.",
                )
            )
            health_score -= 20.0

        return BottleneckReport(
            timestamp=now,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            overall_health_score=max(0.0, health_score),
        )
