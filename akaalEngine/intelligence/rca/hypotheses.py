"""akaalEngine.intelligence.rca.hypotheses
============================================
Pure, deterministic causal-hypothesis heuristics over already-computed P7C.14
anomaly facts and P7C.13 dimension statuses. No I/O, no model calls. Never
converts temporal correlation into certainty: every hypothesis carries
explicit support/contradiction/alternatives and an invalidation condition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Mapping


@dataclass(frozen=True)
class Hypothesis:
    label: str
    support: List[str] = field(default_factory=list)
    confidence_basis: str = ""


@dataclass(frozen=True)
class RCAConclusion:
    primary: Hypothesis
    alternatives: List[Hypothesis] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    invalidation_condition: str = ""

    def to_dict(self) -> dict:
        return {
            "primary_hypothesis": self.primary.label,
            "primary_support": self.primary.support,
            "primary_confidence_basis": self.primary.confidence_basis,
            "alternatives": [{"label": h.label, "support": h.support, "confidence_basis": h.confidence_basis} for h in self.alternatives],
            "contradictions": self.contradictions,
            "missing_evidence": self.missing_evidence,
            "invalidation_condition": self.invalidation_condition,
        }


def build_rca_conclusion(
    *,
    overall_anomaly_status: str,
    bottleneck: str,
    detections: Mapping[str, Mapping],
    fabric_status: str,
    validation_status: str,
) -> RCAConclusion:
    """Deterministic rule ladder. Each branch states its own support and
    invalidation condition -- never a bare label with no evidence."""

    throughput = detections.get("throughput_rows_per_sec", {})
    backlog = detections.get("cdc_backlog_size", {})
    lag = detections.get("cdc_lag_seconds", {})

    # Rule 1: canonical ownership/lease invalidation always dominates -- this
    # is a FACT-backed governance conclusion, not an inferred performance
    # cause, and it can never be displaced by a performance hypothesis.
    if fabric_status == "CRITICAL":
        return RCAConclusion(
            primary=Hypothesis(
                label="Canonical P7B Fabric ownership/lease is invalid (expired, stale, or fenced).",
                support=[f"FABRIC dimension status = CRITICAL (canonical OwnershipManager read)."],
                confidence_basis="Direct canonical fact, not inferred from correlation.",
            ),
            alternatives=[],
            missing_evidence=[],
            invalidation_condition="FABRIC dimension returns to a non-CRITICAL canonical status.",
        )

    if validation_status == "CRITICAL":
        return RCAConclusion(
            primary=Hypothesis(
                label="Validation #11 reports a failed/critical state for this migration.",
                support=["VALIDATION dimension status = CRITICAL (canonical Validation #11 readout)."],
                confidence_basis="Direct canonical fact, not inferred from correlation.",
            ),
            alternatives=[],
            missing_evidence=[],
            invalidation_condition="VALIDATION dimension returns to a non-CRITICAL canonical status.",
        )

    if overall_anomaly_status != "ANOMALOUS":
        return RCAConclusion(
            primary=Hypothesis(
                label="No anomaly currently requires root-cause analysis." if overall_anomaly_status == "NONE"
                else "Insufficient historical data to perform root-cause analysis.",
                support=[f"P7C.14 overall_status = {overall_anomaly_status}"],
                confidence_basis="Direct read of P7C.14's own detection result.",
            ),
            missing_evidence=(
                ["No RCA warranted without an anomaly to explain."] if overall_anomaly_status == "NONE"
                else ["Not enough historical samples exist yet for any detector to establish a baseline."]
            ),
            invalidation_condition="A future request reports overall_status=ANOMALOUS.",
        )

    backlog_anomalous = backlog.get("status") == "ANOMALOUS"
    throughput_anomalous = throughput.get("status") == "ANOMALOUS"
    lag_anomalous = lag.get("status") == "ANOMALOUS"

    if backlog_anomalous and not throughput_anomalous:
        return RCAConclusion(
            primary=Hypothesis(
                label="Target-side CDC apply is falling behind source-side capture (apply-bound saturation).",
                support=[
                    backlog.get("detail", "CDC backlog growing."),
                    "Source-side transport throughput remains within its own historical baseline (no source-side degradation observed).",
                ],
                confidence_basis="Backlog growth correlated with otherwise-stable transport throughput; "
                "genuine capture-vs-apply rate telemetry is not canonically available (see P7C.13 CDC "
                "dimension limitation), so this remains a hypothesis, not a proven cause.",
            ),
            alternatives=[
                Hypothesis(
                    label="Network congestion between source and target.",
                    support=[],
                    confidence_basis="No canonical network/latency telemetry is available to support or refute this alternative -- UNKNOWN, not ruled out.",
                ),
                Hypothesis(
                    label="Worker/capacity shortage on the apply side.",
                    support=[],
                    confidence_basis="No migration-scoped canonical worker read exists (P7C.13 WORKERS is always "
                    "UNKNOWN) -- this alternative can be neither supported nor refuted from available facts.",
                ),
            ],
            contradictions=[],
            missing_evidence=[
                "True per-second CDC capture/apply rates (only cumulative totals are canonically exposed today).",
                "Migration-scoped worker/task health.",
                "Network/provider latency telemetry.",
            ],
            invalidation_condition="CDC backlog trend returns to non-growing (stable or decreasing) while transport throughput remains stable.",
        )

    if throughput_anomalous and not backlog_anomalous:
        return RCAConclusion(
            primary=Hypothesis(
                label="Source-side transport throughput has degraded relative to this migration's own baseline.",
                support=[throughput.get("detail", "Throughput below baseline.")],
                confidence_basis="Deterministic collapse-ratio detection against this migration's own historical median.",
            ),
            alternatives=[
                Hypothesis(
                    label="Worker/capacity shortage.",
                    support=[],
                    confidence_basis="No migration-scoped canonical worker read exists -- cannot be confirmed or ruled out.",
                ),
                Hypothesis(
                    label="Source-side provider throttling.",
                    support=[],
                    confidence_basis="No canonical provider-throttle telemetry is available for this migration.",
                ),
            ],
            missing_evidence=["Migration-scoped worker/task health.", "Source provider throttle/quota telemetry."],
            invalidation_condition="Throughput returns to within its own historical baseline range.",
        )

    if throughput_anomalous and backlog_anomalous:
        return RCAConclusion(
            primary=Hypothesis(
                label="Multiple concurrent degradations (throughput collapse and CDC backlog growth) -- no single dominant cause is evidenced.",
                support=[throughput.get("detail", ""), backlog.get("detail", "")],
                confidence_basis="Co-occurrence of two independent detectors' anomalous findings; co-occurrence "
                "is not itself proof of a shared cause.",
            ),
            alternatives=[
                Hypothesis(label="A single upstream cause (e.g. source outage) affecting both transport and CDC.", support=[], confidence_basis="Plausible but unconfirmed without direct source-health telemetry."),
            ],
            missing_evidence=["Source-system health telemetry.", "Migration-scoped worker/task health."],
            invalidation_condition="Either detector alone returns to NONE while the other remains ANOMALOUS, narrowing the cause.",
        )

    if lag_anomalous:
        return RCAConclusion(
            primary=Hypothesis(
                label="Replication lag has spiked relative to this migration's own baseline.",
                support=[lag.get("detail", "")],
                confidence_basis="Deterministic threshold detection against this migration's own historical median/MAD.",
            ),
            missing_evidence=["True per-second CDC capture/apply rates to distinguish capture-side from apply-side lag."],
            invalidation_condition="Replication lag returns to within its own historical baseline.",
        )

    return RCAConclusion(
        primary=Hypothesis(
            label=f"Anomaly detected (bottleneck={bottleneck}) but no deterministic rule matched the specific detector combination.",
            support=[f"detections={list(detections.keys())}"],
            confidence_basis="Fallback: the anomaly is real (P7C.14 overall_status=ANOMALOUS) but this rule ladder "
            "does not yet have a specific heuristic for this exact combination -- reported honestly rather than guessed.",
        ),
        missing_evidence=["No matching deterministic causal rule for this detector combination."],
        invalidation_condition="A future request matches an existing rule branch.",
    )
