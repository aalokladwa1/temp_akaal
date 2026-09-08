"""akaalEngine.intelligence.producers.anomaly_detection
==========================================================
P7C.14 -- Anomaly & Bottleneck Detection. Consumes P7C.13's trusted runtime
health projection (never raw caller claims) plus a bounded, migration-owned
history of past numeric observations (akaalEngine.intelligence.anomaly.store.
HealthSampleStore) to run deterministic/statistical detectors
(akaalEngine.intelligence.anomaly.detectors) -- no generative model in the
primary detection path.

Precedence law preserved from P7C.13: a canonical FABRIC=CRITICAL (ownership/
lease/fencing) or VALIDATION=CRITICAL observation always dominates the
overall anomaly verdict, regardless of how healthy throughput looks --
security/ownership violations outrank performance optimism.

PLATFORM_WIDE_NOT_MIGRATION_SCOPED context (P7C.13's platform_context) is
NEVER read by this module as a migration-scoped signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Mapping, Optional

from akaalEngine.intelligence.anomaly.detectors import (
    AnomalyStatus,
    BottleneckClass,
    DetectionResult,
    detect_cdc_backlog_growth,
    detect_cdc_lag_anomaly,
    detect_throughput_collapse,
)
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    DiagnosticFinding,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)


@dataclass(frozen=True)
class AnomalyDetectionInputs:
    """Bundled, already-resolved inputs -- this producer performs zero
    canonical or historical-store discovery of its own. `current_dimensions`/
    `historical_dimensions` carry only plain numeric facts already produced by
    the P7C.13 projector (never re-derived independently); `runtime_health_
    dimensions` is P7C.13's own per-dimension status map, consulted only for
    the FABRIC/VALIDATION precedence check -- never re-interpreted."""

    tenant_id: str
    migration_id: str
    current_dimensions: Mapping[str, Any] = field(default_factory=dict)
    # Oldest-first list of past observations' `dimensions` dicts (same keys as current_dimensions).
    historical_dimensions: List[Mapping[str, Any]] = field(default_factory=list)
    runtime_health_overall_status: str = "UNKNOWN"
    runtime_health_dimensions: Mapping[str, Any] = field(default_factory=dict)


AnomalyDetectionResolver = Callable[[IntelligenceRequest, IntelligenceContext], AnomalyDetectionInputs]

_SEVERITY_BY_BOTTLENECK_PRESENCE = {True: "HIGH", False: "MEDIUM"}


def make_anomaly_detection_producer(resolver: AnomalyDetectionResolver):
    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        inputs = resolver(request, context)
        if inputs is None:
            raise IntelligenceValidationError(
                "Anomaly detection resolver returned no AnomalyDetectionInputs. Refusing to "
                "fabricate a detection result with no canonical facts."
            )

        hist = inputs.historical_dimensions
        hist_throughput = [d.get("throughput_rows_per_sec") for d in hist]
        hist_backlog = [d.get("cdc_backlog_size") for d in hist]
        hist_lag = [d.get("cdc_lag_seconds") for d in hist]

        throughput_det = detect_throughput_collapse(hist_throughput, inputs.current_dimensions.get("throughput_rows_per_sec"))
        backlog_series = [v for v in hist_backlog if v is not None] + (
            [inputs.current_dimensions["cdc_backlog_size"]] if inputs.current_dimensions.get("cdc_backlog_size") is not None else []
        )
        backlog_det = detect_cdc_backlog_growth(backlog_series)
        lag_det = detect_cdc_lag_anomaly(hist_lag, inputs.current_dimensions.get("cdc_lag_seconds"))

        detections: List[DetectionResult] = [throughput_det, backlog_det, lag_det]

        fabric_status = str(inputs.runtime_health_dimensions.get("FABRIC", {}).get("status", "UNKNOWN"))
        validation_status = str(inputs.runtime_health_dimensions.get("VALIDATION", {}).get("status", "UNKNOWN"))
        ownership_or_validation_critical = fabric_status == "CRITICAL" or validation_status == "CRITICAL"

        findings: List[DiagnosticFinding] = []
        if ownership_or_validation_critical:
            findings.append(
                DiagnosticFinding(
                    code="ANOMALY:GOVERNANCE_CRITICAL_PRECEDENCE",
                    severity="HIGH",
                    message=(
                        f"Canonical FABRIC={fabric_status!r} / VALIDATION={validation_status!r}: a security/ownership "
                        "or validation CRITICAL observation outranks any performance reading and forces the overall "
                        "anomaly verdict regardless of throughput/CDC signals."
                    ),
                    evidence_refs=["FABRIC", "VALIDATION"],
                )
            )

        for det in detections:
            if det.status == AnomalyStatus.ANOMALOUS:
                findings.append(
                    DiagnosticFinding(
                        code=f"ANOMALY:{det.metric.upper()}",
                        severity=_SEVERITY_BY_BOTTLENECK_PRESENCE[det.bottleneck != BottleneckClass.UNKNOWN],
                        message=det.detail,
                        evidence_refs=[det.metric],
                    )
                )

        insufficient = [det for det in detections if det.status == AnomalyStatus.INSUFFICIENT_DATA]
        not_applicable = [det for det in detections if det.status == AnomalyStatus.NOT_APPLICABLE]
        evaluated = [det for det in detections if det.status in (AnomalyStatus.ANOMALOUS, AnomalyStatus.NONE)]

        any_anomalous = any(det.status == AnomalyStatus.ANOMALOUS for det in detections) or ownership_or_validation_critical
        if any_anomalous:
            overall = "ANOMALOUS"
        elif evaluated:
            overall = "NONE"
        else:
            # Every detector was either INSUFFICIENT_DATA or NOT_APPLICABLE --
            # this must NEVER be reported as "no anomaly detected".
            overall = "INSUFFICIENT_DATA"

        anomalous_bottlenecks = {det.bottleneck for det in detections if det.status == AnomalyStatus.ANOMALOUS}
        anomalous_bottlenecks.discard(BottleneckClass.UNKNOWN)
        if ownership_or_validation_critical:
            bottleneck = BottleneckClass.UNKNOWN  # ownership/validation issues are not a performance-bottleneck class
        elif len(anomalous_bottlenecks) > 1:
            bottleneck = BottleneckClass.MULTI_FACTOR
        elif len(anomalous_bottlenecks) == 1:
            bottleneck = next(iter(anomalous_bottlenecks))
        elif overall == "ANOMALOUS":
            bottleneck = BottleneckClass.UNKNOWN
        else:
            bottleneck = BottleneckClass.UNKNOWN

        evidence_coverage = len(evaluated) / len(detections) if detections else 0.0

        summary = (
            f"Anomaly detection for migration {inputs.migration_id!r}: overall={overall}, "
            f"bottleneck={bottleneck.value}, {len(evaluated)}/{len(detections)} detectors evaluated "
            f"({len(insufficient)} insufficient data, {len(not_applicable)} not applicable)."
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.DIAGNOSIS,
            summary=summary,
            explanation=Explanation(
                summary="Deterministic robust-statistics (median/MAD) detection over this migration's own "
                "historical samples; a canonical FABRIC/VALIDATION CRITICAL observation always outranks "
                "performance signals.",
                supporting_facts=[f"{det.metric}: {det.status.value}" for det in detections],
                assumptions=(
                    [
                        "Some detectors lacked enough historical samples to establish a baseline -- this is "
                        "reported as INSUFFICIENT_DATA, never treated as evidence of a healthy migration."
                    ]
                    if insufficient
                    else []
                ),
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=evidence_coverage,
                missing_information=[f"{det.metric}: {det.status.value}" for det in insufficient],
            ),
            findings=findings,
            data={
                "migration_id": inputs.migration_id,
                "overall_status": overall,
                "bottleneck": bottleneck.value,
                "detections": {det.metric: det.to_dict() for det in detections},
                "runtime_health_overall_status": inputs.runtime_health_overall_status,
            },
        )

    return producer
