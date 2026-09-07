"""akaalEngine.intelligence.anomaly.detectors
================================================
Pure, deterministic statistical detectors (P7C brief: "primary machinery must
be deterministic/statistical, not prose generation"). No I/O, no model calls.
Uses robust statistics (median/MAD) rather than mean/stddev so a single
outlier sample cannot dominate the baseline.
"""

from __future__ import annotations

import enum
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Sequence


MIN_SAMPLES_FOR_BASELINE = 3


class AnomalyStatus(str, enum.Enum):
    NONE = "NONE"
    ANOMALOUS = "ANOMALOUS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class BottleneckClass(str, enum.Enum):
    SOURCE_BOUND = "SOURCE_BOUND"
    TARGET_BOUND = "TARGET_BOUND"
    NETWORK_BOUND = "NETWORK_BOUND"
    CPU_BOUND = "CPU_BOUND"
    MEMORY_BOUND = "MEMORY_BOUND"
    STORAGE_BOUND = "STORAGE_BOUND"
    WORKER_BOUND = "WORKER_BOUND"
    CDC_CAPTURE_BOUND = "CDC_CAPTURE_BOUND"
    CDC_APPLY_BOUND = "CDC_APPLY_BOUND"
    VALIDATION_BOUND = "VALIDATION_BOUND"
    PROVIDER_THROTTLED = "PROVIDER_THROTTLED"
    MULTI_FACTOR = "MULTI_FACTOR"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DetectionResult:
    status: AnomalyStatus
    metric: str
    current_value: Optional[float]
    baseline_median: Optional[float] = None
    baseline_mad: Optional[float] = None
    sample_count: int = 0
    detail: str = ""
    bottleneck: BottleneckClass = BottleneckClass.UNKNOWN

    def to_dict(self) -> dict:
        return {
            "status": self.status.value, "metric": self.metric, "current_value": self.current_value,
            "baseline_median": self.baseline_median, "baseline_mad": self.baseline_mad,
            "sample_count": self.sample_count, "detail": self.detail, "bottleneck": self.bottleneck.value,
        }


def _median(values: Sequence[float]) -> float:
    return statistics.median(values)


def _mad(values: Sequence[float], med: float) -> float:
    """Median Absolute Deviation -- robust to outliers, unlike stddev."""
    deviations = [abs(v - med) for v in values]
    return statistics.median(deviations)


def detect_throughput_collapse(
    historical_rows_per_sec: Sequence[float],
    current_rows_per_sec: Optional[float],
    *,
    collapse_ratio: float = 0.4,
    degradation_ratio: float = 0.7,
) -> DetectionResult:
    """Real historical baseline: median/MAD of THIS migration's own recent
    throughput samples -- never a cross-migration or fabricated global
    baseline. `collapse_ratio`/`degradation_ratio` are fractions of the
    baseline median below which current throughput is flagged."""
    if current_rows_per_sec is None:
        return DetectionResult(AnomalyStatus.NOT_APPLICABLE, "throughput_rows_per_sec", None, detail="No current throughput observation supplied.")
    samples = [v for v in historical_rows_per_sec if v is not None]
    if len(samples) < MIN_SAMPLES_FOR_BASELINE:
        return DetectionResult(
            AnomalyStatus.INSUFFICIENT_DATA, "throughput_rows_per_sec", current_rows_per_sec,
            sample_count=len(samples),
            detail=f"Only {len(samples)} historical sample(s); need >= {MIN_SAMPLES_FOR_BASELINE} for a baseline. "
            "This is NOT evidence of a healthy migration -- absence of a baseline is not absence of an anomaly.",
        )
    med = _median(samples)
    mad = _mad(samples, med)
    if med <= 0:
        return DetectionResult(
            AnomalyStatus.INSUFFICIENT_DATA, "throughput_rows_per_sec", current_rows_per_sec,
            baseline_median=med, baseline_mad=mad, sample_count=len(samples),
            detail="Baseline median throughput is non-positive; a meaningful collapse ratio cannot be computed.",
        )
    ratio = current_rows_per_sec / med
    if ratio <= collapse_ratio:
        return DetectionResult(
            AnomalyStatus.ANOMALOUS, "throughput_rows_per_sec", current_rows_per_sec, med, mad, len(samples),
            detail=f"Current throughput {current_rows_per_sec:.2f}/s is {ratio:.0%} of this migration's own "
            f"recent baseline median {med:.2f}/s -- abrupt collapse.",
            bottleneck=BottleneckClass.MULTI_FACTOR,
        )
    if ratio <= degradation_ratio:
        return DetectionResult(
            AnomalyStatus.ANOMALOUS, "throughput_rows_per_sec", current_rows_per_sec, med, mad, len(samples),
            detail=f"Current throughput {current_rows_per_sec:.2f}/s is {ratio:.0%} of baseline median "
            f"{med:.2f}/s -- gradual degradation.",
            bottleneck=BottleneckClass.MULTI_FACTOR,
        )
    return DetectionResult(AnomalyStatus.NONE, "throughput_rows_per_sec", current_rows_per_sec, med, mad, len(samples))


def detect_cdc_backlog_growth(
    historical_backlog_sizes: Sequence[float],
    *,
    min_growth_ratio: float = 1.5,
) -> DetectionResult:
    """Genuine trend detection over THIS migration's own backlog_size history
    (a real instantaneous canonical fact, unlike the mislabeled cumulative
    '*_rate_events_sec' fields -- see P7C.13's CDC-dimension docstring, never
    used here). Flags sustained, non-noise growth: every consecutive pair
    must be non-decreasing, and the overall growth must clear
    `min_growth_ratio` -- a single noisy uptick is not an anomaly."""
    samples = [v for v in historical_backlog_sizes if v is not None]
    if len(samples) < MIN_SAMPLES_FOR_BASELINE:
        return DetectionResult(
            AnomalyStatus.INSUFFICIENT_DATA, "cdc_backlog_size", samples[-1] if samples else None,
            sample_count=len(samples),
            detail=f"Only {len(samples)} historical backlog sample(s); need >= {MIN_SAMPLES_FOR_BASELINE} to "
            "assess a trend. This does not mean CDC is converging.",
        )
    monotonic_non_decreasing = all(b >= a for a, b in zip(samples, samples[1:]))
    first, last = samples[0], samples[-1]
    if first <= 0:
        ratio = float("inf") if last > 0 else 1.0
    else:
        ratio = last / first
    if monotonic_non_decreasing and ratio >= min_growth_ratio and last > first:
        return DetectionResult(
            AnomalyStatus.ANOMALOUS, "cdc_backlog_size", last, sample_count=len(samples),
            detail=f"CDC backlog grew monotonically from {first:.0f} to {last:.0f} events across "
            f"{len(samples)} observations ({ratio:.2f}x) -- sustained backlog growth, not noise.",
            # Cannot distinguish capture-bound from apply-bound without true
            # per-second capture/apply rates, which are not canonically
            # available (P7C.13 correction) -- never guess which side.
            bottleneck=BottleneckClass.UNKNOWN,
        )
    return DetectionResult(AnomalyStatus.NONE, "cdc_backlog_size", last, sample_count=len(samples))


def detect_cdc_lag_anomaly(
    historical_lag_seconds: Sequence[float],
    current_lag_seconds: Optional[float],
    *,
    degradation_ratio: float = 2.0,
) -> DetectionResult:
    if current_lag_seconds is None:
        return DetectionResult(AnomalyStatus.NOT_APPLICABLE, "cdc_lag_seconds", None, detail="No current replication lag observation supplied.")
    samples = [v for v in historical_lag_seconds if v is not None]
    if len(samples) < MIN_SAMPLES_FOR_BASELINE:
        return DetectionResult(
            AnomalyStatus.INSUFFICIENT_DATA, "cdc_lag_seconds", current_lag_seconds, sample_count=len(samples),
            detail=f"Only {len(samples)} historical lag sample(s); need >= {MIN_SAMPLES_FOR_BASELINE} for a baseline.",
        )
    med = _median(samples)
    mad = _mad(samples, med)
    threshold = max(med * degradation_ratio, med + 3 * mad) if med > 0 else (3 * mad if mad > 0 else None)
    if threshold is not None and current_lag_seconds > threshold:
        return DetectionResult(
            AnomalyStatus.ANOMALOUS, "cdc_lag_seconds", current_lag_seconds, med, mad, len(samples),
            detail=f"Replication lag {current_lag_seconds:.1f}s exceeds this migration's own robust threshold "
            f"{threshold:.1f}s (baseline median {med:.1f}s).",
            bottleneck=BottleneckClass.UNKNOWN,
        )
    return DetectionResult(AnomalyStatus.NONE, "cdc_lag_seconds", current_lag_seconds, med, mad, len(samples))
