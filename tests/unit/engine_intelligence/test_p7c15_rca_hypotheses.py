"""tests/unit/engine_intelligence/test_p7c15_rca_hypotheses.py
==================================================================
P7C.15 pure hypothesis-ladder tests: governance precedence, apply-bound vs
source-bound distinction, honest UNKNOWN alternatives (worker/network),
non-fabrication of certainty, and the "no rule matched" honest fallback.
"""

from __future__ import annotations

from akaalEngine.intelligence.rca.hypotheses import build_rca_conclusion


def _detections(**overrides):
    base = {
        "throughput_rows_per_sec": {"status": "NONE"},
        "cdc_backlog_size": {"status": "NONE"},
        "cdc_lag_seconds": {"status": "NONE"},
    }
    base.update(overrides)
    return base


class TestGovernancePrecedence:
    def test_fabric_critical_dominates_even_with_anomalies_present(self):
        conclusion = build_rca_conclusion(
            overall_anomaly_status="ANOMALOUS", bottleneck="MULTI_FACTOR",
            detections=_detections(throughput_rows_per_sec={"status": "ANOMALOUS", "detail": "collapse"}),
            fabric_status="CRITICAL", validation_status="UNKNOWN",
        )
        assert "Fabric ownership/lease is invalid" in conclusion.primary.label
        assert conclusion.alternatives == []

    def test_validation_critical_dominates_when_fabric_healthy(self):
        conclusion = build_rca_conclusion(
            overall_anomaly_status="ANOMALOUS", bottleneck="UNKNOWN",
            detections=_detections(), fabric_status="HEALTHY", validation_status="CRITICAL",
        )
        assert "Validation #11" in conclusion.primary.label


class TestNoAnomalyVsInsufficientData:
    def test_none_status_yields_no_rca_needed(self):
        conclusion = build_rca_conclusion(overall_anomaly_status="NONE", bottleneck="UNKNOWN", detections=_detections(), fabric_status="UNKNOWN", validation_status="UNKNOWN")
        assert "No anomaly" in conclusion.primary.label

    def test_insufficient_data_is_not_conflated_with_no_anomaly(self):
        conclusion = build_rca_conclusion(overall_anomaly_status="INSUFFICIENT_DATA", bottleneck="UNKNOWN", detections=_detections(), fabric_status="UNKNOWN", validation_status="UNKNOWN")
        assert "Insufficient historical data" in conclusion.primary.label


class TestApplyBoundVsSourceBound:
    def test_backlog_growth_with_stable_throughput_is_apply_bound_hypothesis(self):
        conclusion = build_rca_conclusion(
            overall_anomaly_status="ANOMALOUS", bottleneck="UNKNOWN",
            detections=_detections(cdc_backlog_size={"status": "ANOMALOUS", "detail": "backlog grew"}),
            fabric_status="UNKNOWN", validation_status="UNKNOWN",
        )
        assert "apply is falling behind" in conclusion.primary.label
        alt_labels = [a.label for a in conclusion.alternatives]
        assert any("Worker" in a for a in alt_labels)
        assert "workers" in " ".join(a.confidence_basis for a in conclusion.alternatives).lower() or \
               "UNKNOWN" in " ".join(a.confidence_basis for a in conclusion.alternatives)

    def test_throughput_collapse_alone_is_source_bound_hypothesis(self):
        conclusion = build_rca_conclusion(
            overall_anomaly_status="ANOMALOUS", bottleneck="MULTI_FACTOR",
            detections=_detections(throughput_rows_per_sec={"status": "ANOMALOUS", "detail": "collapse"}),
            fabric_status="UNKNOWN", validation_status="UNKNOWN",
        )
        assert "transport throughput has degraded" in conclusion.primary.label

    def test_worker_alternative_never_claims_confirmed(self):
        conclusion = build_rca_conclusion(
            overall_anomaly_status="ANOMALOUS", bottleneck="UNKNOWN",
            detections=_detections(cdc_backlog_size={"status": "ANOMALOUS", "detail": "x"}),
            fabric_status="UNKNOWN", validation_status="UNKNOWN",
        )
        worker_alt = next(a for a in conclusion.alternatives if "Worker" in a.label)
        assert "cannot" in worker_alt.confidence_basis.lower() or "UNKNOWN" in worker_alt.confidence_basis


class TestCorrelationNeverBecomesProvenCausation:
    """Owner-review Blocker 17 closure: even the CLEAREST-looking single-cause
    scenario still discloses missing evidence and never claims proof --
    correlation (backlog growth co-occurring with stable throughput) is
    reported as a hypothesis with an explicit confidence_basis caveat, not a
    certainty."""

    def test_apply_bound_hypothesis_never_claims_proof_even_when_clear_cut(self):
        conclusion = build_rca_conclusion(
            overall_anomaly_status="ANOMALOUS", bottleneck="UNKNOWN",
            detections=_detections(cdc_backlog_size={"status": "ANOMALOUS", "detail": "backlog grew monotonically"}),
            fabric_status="HEALTHY", validation_status="HEALTHY",
        )
        # Missing evidence is NEVER empty for a correlation-based hypothesis --
        # true capture/apply rates and worker/network telemetry are always
        # absent from this repository's canonical surface today.
        assert len(conclusion.missing_evidence) >= 2
        assert "hypothesis" in conclusion.primary.confidence_basis.lower() or "not" in conclusion.primary.confidence_basis.lower()
        # The primary label itself is phrased as an inference, not a fact.
        assert "is falling behind" in conclusion.primary.label  # descriptive of the pattern
        assert conclusion.invalidation_condition  # a falsification path must always be stated

    def test_alternatives_are_never_silently_dropped_when_a_primary_is_found(self):
        conclusion = build_rca_conclusion(
            overall_anomaly_status="ANOMALOUS", bottleneck="UNKNOWN",
            detections=_detections(cdc_backlog_size={"status": "ANOMALOUS", "detail": "x"}),
            fabric_status="UNKNOWN", validation_status="UNKNOWN",
        )
        assert len(conclusion.alternatives) >= 2


class TestMultiFactor:
    def test_both_anomalous_yields_multi_factor_no_false_single_cause(self):
        conclusion = build_rca_conclusion(
            overall_anomaly_status="ANOMALOUS", bottleneck="MULTI_FACTOR",
            detections=_detections(
                throughput_rows_per_sec={"status": "ANOMALOUS", "detail": "collapse"},
                cdc_backlog_size={"status": "ANOMALOUS", "detail": "growth"},
            ),
            fabric_status="UNKNOWN", validation_status="UNKNOWN",
        )
        assert "no single dominant cause" in conclusion.primary.label
