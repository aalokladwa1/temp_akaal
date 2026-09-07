"""tests/unit/engine_intelligence/test_p7c14_anomaly_detectors.py
====================================================================
P7C.14 pure detector math: robust median/MAD baselines, insufficient-data
handling, non-fabrication of certainty from absent history.
"""

from __future__ import annotations

from akaalEngine.intelligence.anomaly.detectors import (
    AnomalyStatus,
    detect_cdc_backlog_growth,
    detect_cdc_lag_anomaly,
    detect_throughput_collapse,
)


class TestThroughputCollapse:
    def test_insufficient_history_is_not_none(self):
        result = detect_throughput_collapse([1000.0], 50.0)
        assert result.status == AnomalyStatus.INSUFFICIENT_DATA

    def test_no_current_observation_is_not_applicable(self):
        result = detect_throughput_collapse([1000.0, 990.0, 1010.0], None)
        assert result.status == AnomalyStatus.NOT_APPLICABLE

    def test_abrupt_collapse_detected_against_own_baseline(self):
        history = [1000.0, 980.0, 1020.0, 990.0, 1010.0]
        result = detect_throughput_collapse(history, 100.0)
        assert result.status == AnomalyStatus.ANOMALOUS
        assert result.baseline_median == 1000.0

    def test_stable_throughput_is_not_anomalous(self):
        history = [1000.0, 980.0, 1020.0, 990.0, 1010.0]
        result = detect_throughput_collapse(history, 1005.0)
        assert result.status == AnomalyStatus.NONE

    def test_non_positive_baseline_does_not_fabricate_ratio(self):
        result = detect_throughput_collapse([0.0, 0.0, 0.0], 5.0)
        assert result.status == AnomalyStatus.INSUFFICIENT_DATA


class TestCDCBacklogGrowth:
    def test_insufficient_samples_not_convergent_claim(self):
        result = detect_cdc_backlog_growth([100.0])
        assert result.status == AnomalyStatus.INSUFFICIENT_DATA

    def test_monotonic_growth_detected(self):
        result = detect_cdc_backlog_growth([1000.0, 5000.0, 20000.0, 60000.0, 90000.0])
        assert result.status == AnomalyStatus.ANOMALOUS
        assert "grew monotonically" in result.detail

    def test_stable_backlog_not_anomalous(self):
        result = detect_cdc_backlog_growth([1000.0, 950.0, 1010.0, 990.0, 1005.0])
        assert result.status == AnomalyStatus.NONE

    def test_single_noisy_uptick_is_not_flagged(self):
        # Not monotonic (one decrease breaks the sustained-growth requirement).
        result = detect_cdc_backlog_growth([1000.0, 5000.0, 800.0, 900.0, 950.0])
        assert result.status == AnomalyStatus.NONE

    def test_zero_baseline_backlog_growth_does_not_crash(self):
        result = detect_cdc_backlog_growth([0.0, 0.0, 100.0, 500.0, 900.0])
        assert result.status == AnomalyStatus.ANOMALOUS


class TestCDCLagAnomaly:
    def test_insufficient_history(self):
        result = detect_cdc_lag_anomaly([5.0], 100.0)
        assert result.status == AnomalyStatus.INSUFFICIENT_DATA

    def test_no_current_lag_not_applicable(self):
        result = detect_cdc_lag_anomaly([5.0, 6.0, 4.0], None)
        assert result.status == AnomalyStatus.NOT_APPLICABLE

    def test_lag_spike_detected(self):
        result = detect_cdc_lag_anomaly([5.0, 6.0, 4.0, 5.5], 500.0)
        assert result.status == AnomalyStatus.ANOMALOUS

    def test_normal_lag_not_anomalous(self):
        result = detect_cdc_lag_anomaly([5.0, 6.0, 4.0, 5.5], 5.2)
        assert result.status == AnomalyStatus.NONE
