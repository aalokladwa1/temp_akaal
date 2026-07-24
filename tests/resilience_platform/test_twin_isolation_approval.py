"""Tests: Resilience Platform — Digital Twin, Cost, Confidence, Replay, Maturity, Isolation, Approval, Versioning, Resources."""

import pytest
from akaal.resilience_eng.digital_twin.fidelity import DigitalTwinEngine, DigitalTwinFidelityManager, InfrastructureDriftDetector
from akaal.resilience_eng.cost.estimator import ExperimentCostEstimator
from akaal.resilience_eng.confidence.engine import ConfidenceEngine
from akaal.resilience_eng.replay.replay_engine import ExperimentReplayEngine
from akaal.resilience_eng.maturity.assessment import ResilienceMaturityEngine
from akaal.resilience_eng.isolation.experiment_context import ExperimentIsolationContext
from akaal.resilience_eng.approval.workflow import ApprovalWorkflowEngine
from akaal.resilience_eng.versioning.version_manager import ExperimentVersionManager
from akaal.resilience_eng.resources.reservation_engine import ResourceReservationEngine


class TestDigitalTwinEngine:
    def test_simulate_experiment_preflight(self):
        eng = DigitalTwinEngine()
        res = eng.simulate_experiment_preflight("exp_001")
        assert res["simulation_passed"] is True
        assert res["fidelity_assessment"]["fidelity_score"] == 100.0

    def test_fidelity_manager_no_drift(self):
        mgr = DigitalTwinFidelityManager()
        nodes = {"n1": "healthy", "n2": "healthy"}
        res = mgr.evaluate_fidelity(nodes, nodes)
        assert res["fidelity_score"] == 100.0
        assert res["simulation_reliability_rating"] == "HIGH"

    def test_drift_detector_detects_drift(self):
        det = InfrastructureDriftDetector()
        twin = {"n1": "healthy"}
        live = {"n1": "healthy", "n2": "degraded"}
        res = det.detect_drift(twin, live)
        assert res["drift_detected"] is True
        assert res["drift_score"] > 0.0


class TestExperimentCostEstimator:
    def test_estimate_cost(self):
        est = ExperimentCostEstimator()
        res = est.estimate_experiment_cost(60.0, 4)
        assert res["estimated_cost_usd"] == 0.05
        assert res["estimated_downtime_risk"] == "ZERO_DOWNTIME"
        assert "estimated_cpu_hours" in res


class TestConfidenceEngine:
    def test_compute_confidence_all_pass(self):
        eng = ConfidenceEngine()
        res = eng.compute_confidence(True, True, True)
        assert res.overall_confidence >= 95.0
        assert res.recovery_confidence == 99.0

    def test_compute_confidence_partial_fail(self):
        eng = ConfidenceEngine()
        res = eng.compute_confidence(False, False, False)
        assert res.overall_confidence < 70.0


class TestExperimentReplayEngine:
    def test_replay_experiment(self):
        eng = ExperimentReplayEngine()
        events = [{"event": "inject_fault"}, {"event": "recovery"}, {"event": "validate"}]
        res = eng.replay_experiment("exp_001", events)
        assert res["is_reproducible"] is True
        assert res["original_vs_replay"]["replayed_events_count"] == 3


class TestResilienceMaturityEngine:
    def test_evaluate_maturity(self):
        eng = ResilienceMaturityEngine()
        report = eng.evaluate_maturity()
        assert report.overall_maturity_level == "OPTIMIZED_LEVEL_5"
        assert report.reliability_score >= 90.0
        assert len(report.recommendations) >= 1


class TestExperimentIsolationContext:
    def test_context_manager_lifecycle(self):
        ctx = ExperimentIsolationContext()
        with ctx as iso:
            assert iso.sandbox.is_active is True
        assert ctx.sandbox.is_active is False


class TestApprovalWorkflowEngine:
    def test_submit_and_approve(self):
        eng = ApprovalWorkflowEngine()
        appr = eng.submit_and_approve("exp_001", "ENGINEER", "SECURITY_OFFICER")
        assert appr.status == "APPROVED"
        assert eng.is_approved("exp_001") is True


class TestExperimentVersionManager:
    def test_create_and_get_version(self):
        mgr = ExperimentVersionManager()
        ver = mgr.create_version("exp_001", "1.0.0", "Initial release", {"scenario": "DB_Failure"})
        assert ver.version == "1.0.0"
        latest = mgr.get_latest_version("exp_001")
        assert latest is not None
        assert latest.version == "1.0.0"


class TestResourceReservationEngine:
    def test_reserve_and_release(self):
        eng = ResourceReservationEngine()
        res = eng.reserve_resources("exp_001", cores=2, memory_mb=1024)
        assert res is not None
        assert res.experiment_id == "exp_001"
        eng.release_reservation("exp_001")
