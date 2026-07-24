"""Tests: Resilience Platform — Scenario Orchestration, Scoring, Recovery Validation, Reporting, Learning."""

import pytest
from akaal.resilience_eng.scenario.orchestrator import ScenarioOrchestrationEngine, ExperimentWorkflow, ExperimentStep
from akaal.resilience_eng.scoring.score_engine import ResilienceScoreEngine
from akaal.resilience_eng.validation.recovery_validator import AutomaticRecoveryValidator
from akaal.resilience_eng.reporting.report_generator import EnterpriseResilienceReportGenerator
from akaal.resilience_eng.learning.learning_engine import ContinuousResilienceLearningEngine
from akaal.resilience_eng.library.catalog import ResilienceExperimentLibrary
from akaal.resilience_eng.safety.blast_radius import BlastRadiusController, SafetyGuardrailsEngine
from akaal.resilience_eng.policy.declarations import DeclarativePolicyEngine


class TestScenarioOrchestration:
    def test_execute_workflow(self):
        eng = ScenarioOrchestrationEngine()
        wf = ExperimentWorkflow(
            workflow_id="wf_01",
            workflow_name="DB_Network_Cascade",
            steps=[
                ExperimentStep("s1", "Database Failure"),
                ExperimentStep("s2", "Network Partition"),
                ExperimentStep("s3", "Recovery"),
            ]
        )
        res = eng.execute_workflow(wf)
        assert res["status"] == "WORKFLOW_COMPLETED"
        assert res["executed_steps_count"] == 3


class TestResilienceScoreEngine:
    def test_compute_scores_successful_recovery(self):
        eng = ResilienceScoreEngine()
        scores = eng.compute_scores(True, 50.0)
        assert scores.overall_resilience_score >= 95.0
        assert scores.recovery_score == 99.0

    def test_compute_scores_failed_recovery(self):
        eng = ResilienceScoreEngine()
        scores = eng.compute_scores(False, 100.0)
        assert scores.recovery_score == 50.0


class TestAutomaticRecoveryValidator:
    def test_validate_recovery_all_platforms_healthy(self):
        class MockCtx:
            validation_platform = object()
            self_healing_platform = object()
            replication_platform = object()
            reliability_platform = object()

        validator = AutomaticRecoveryValidator()
        res = validator.validate_post_experiment_recovery(MockCtx())
        assert res["recovery_validated"] is True
        assert res["platform1_validation_passed"] is True
        assert res["no_corruption_detected"] is True


class TestEnterpriseResilienceReporting:
    def test_generate_full_report_suite(self):
        gen = EnterpriseResilienceReportGenerator()
        suite = gen.generate_full_report_suite("exp_001", [], 98.5)
        assert "technical_report" in suite
        assert "executive_report" in suite
        assert suite["executive_report"]["report_type"] == "EXECUTIVE_SUMMARY"
        assert suite["executive_report"]["overall_resilience_posture"] == "EXCELLENT"

    def test_executive_report_score(self):
        gen = EnterpriseResilienceReportGenerator()
        suite = gen.generate_full_report_suite("exp_002", [], 95.0)
        assert suite["executive_report"]["overall_resilience_score"] == 95.0

    def test_export_json(self):
        gen = EnterpriseResilienceReportGenerator()
        suite = gen.generate_full_report_suite("exp_003", [], 98.5)
        assert len(suite["exported_json"]) > 50


class TestContinuousResilienceLearning:
    def test_generate_insights(self):
        eng = ContinuousResilienceLearningEngine()
        insights = eng.generate_learning_insights([])
        assert insights["insights_count"] >= 1
        assert insights["mttr_trend"] == "IMPROVING"
        assert len(insights["recommendations"]) >= 1


class TestExperimentLibrary:
    def test_list_templates(self):
        lib = ResilienceExperimentLibrary()
        templates = lib.list_templates()
        assert len(templates) == 12
        assert "Regional Outage" in templates

    def test_get_specific_template(self):
        lib = ResilienceExperimentLibrary()
        t = lib.get_template("Primary Database Failure")
        assert t is not None
        assert t["version"] == "1.0.0"


class TestBlastRadiusAndSafetyGuardrails:
    def test_blast_radius_within_limit(self):
        ctrl = BlastRadiusController()
        assert ctrl.validate_scope("Service", "Service") is True
        assert ctrl.validate_scope("Worker", "Service") is True

    def test_blast_radius_exceeds_limit(self):
        ctrl = BlastRadiusController()
        assert ctrl.validate_scope("Entire_Environment", "Service") is False

    def test_safety_guardrails_approved(self):
        eng = SafetyGuardrailsEngine()
        res = eng.validate_safety("Service", "Service")
        assert res["safe_to_execute"] is True

    def test_safety_guardrails_rejected(self):
        eng = SafetyGuardrailsEngine()
        res = eng.validate_safety("Entire_Environment", "Service")
        assert res["safe_to_execute"] is False


class TestDeclarativePolicyEngine:
    def test_policy_compliant(self):
        eng = DeclarativePolicyEngine()
        res = eng.validate_experiment_policy("Service", 20.0)
        assert res["compliant"] is True

    def test_policy_exceeds_rto(self):
        eng = DeclarativePolicyEngine()
        res = eng.validate_experiment_policy("Service", 60.0)
        assert res["compliant"] is False
        assert res["reason"] == "EXCEEDS_RTO_LIMIT"
