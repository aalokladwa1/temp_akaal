"""Tests: Resilience Platform — Provenance, Security, Certification, Failure Taxonomy, Dependency Graph."""

import pytest
from akaal.resilience_eng.provenance.provenance_manager import ExperimentProvenanceManager
from akaal.resilience_eng.security.authorization import SecurityAuthorizationEngine, DigitalSignatureVerifier, ExecutionIntegrityValidator
from akaal.resilience_eng.certification.recovery_certifier import RecoveryCertificationEngine, RecoveryCertificate
from akaal.resilience_eng.taxonomy.classifier import FailureTaxonomyClassifier, FailureCategory
from akaal.resilience_eng.dependencies.graph import ExperimentDependencyGraph, DependencyResolver, ConcurrentExecutionValidator
from akaal.resilience_eng.pipeline.state_machine import PipelineExecutionStateMachine, PipelineStage


class TestProvenanceSystem:
    def test_record_provenance(self):
        mgr = ExperimentProvenanceManager()
        rec = mgr.record_provenance("exp_001", "Regional_Outage", "1.0.0", ["appr_001"])
        assert rec.experiment_id == "exp_001"
        assert rec.version == "1.0.0"
        assert len(rec.approval_ids) == 1

    def test_get_provenance(self):
        mgr = ExperimentProvenanceManager()
        mgr.record_provenance("exp_002", "DB_Failure", "1.0.0")
        found = mgr.get_provenance("exp_002")
        assert found is not None
        assert found.experiment_id == "exp_002"

    def test_list_lineage(self):
        mgr = ExperimentProvenanceManager()
        for i in range(3):
            mgr.record_provenance(f"exp_{i}", f"Scenario_{i}")
        records = mgr.list_all_lineage()
        assert len(records) == 3


class TestSecurityGovernance:
    def test_authorize_execution_admin(self):
        eng = SecurityAuthorizationEngine()
        assert eng.authorize_execution("RESILIENCE_ADMIN", "Service") is True

    def test_authorize_execution_insufficient_role(self):
        eng = SecurityAuthorizationEngine()
        assert eng.authorize_execution("DEVELOPER", "Service") is False

    def test_authorize_entire_environment_requires_security_officer(self):
        eng = SecurityAuthorizationEngine()
        assert eng.authorize_execution("RESILIENCE_ADMIN", "Entire_Environment") is False
        assert eng.authorize_execution("SECURITY_OFFICER", "Entire_Environment") is True

    def test_signature_verification_valid(self):
        ver = DigitalSignatureVerifier()
        assert ver.verify_signature("payload", "sig_valid_abc") is True

    def test_integrity_validation_no_tamper(self):
        val = ExecutionIntegrityValidator()
        assert val.validate_integrity({"tamper_detected": False}) is True

    def test_integrity_validation_tamper_detected(self):
        val = ExecutionIntegrityValidator()
        assert val.validate_integrity({"tamper_detected": True}) is False


class TestRecoveryCertification:
    def test_certify_recovery(self):
        class MockCtx:
            validation_platform = object()
            self_healing_platform = object()
            replication_platform = object()
            reliability_platform = object()

        engine = RecoveryCertificationEngine()
        cert = engine.certify_recovery("exp_001", MockCtx())
        assert cert.certificate_id.startswith("CERT_")
        assert cert.platform1_validated is True
        assert cert.platform2_healed is True
        assert cert.platform3_replicated is True
        assert cert.platform4_reliable is True
        assert len(cert.signature) == 64  # SHA-256 hex


class TestFailureTaxonomy:
    def test_classify_network_failure(self):
        clf = FailureTaxonomyClassifier()
        cat = clf.classify_failure("network socket timeout")
        assert cat == FailureCategory.NETWORK

    def test_classify_database_failure(self):
        clf = FailureTaxonomyClassifier()
        cat = clf.classify_failure("database connection refused")
        assert cat == FailureCategory.DATABASE

    def test_classify_storage_failure(self):
        clf = FailureTaxonomyClassifier()
        cat = clf.classify_failure("disk io error occurred")
        assert cat == FailureCategory.STORAGE

    def test_classify_performance_failure(self):
        clf = FailureTaxonomyClassifier()
        cat = clf.classify_failure("latency exceeded threshold")
        assert cat == FailureCategory.PERFORMANCE


class TestDependencyGraph:
    def test_no_circular_dependency(self):
        g = ExperimentDependencyGraph()
        g.add_dependency("exp_b", "exp_a")
        assert g.detect_circular_dependencies() is False

    def test_circular_dependency_detected(self):
        g = ExperimentDependencyGraph()
        g.add_dependency("exp_a", "exp_b")
        g.add_dependency("exp_b", "exp_a")
        assert g.detect_circular_dependencies() is True

    def test_concurrent_execution_allowed(self):
        g = ExperimentDependencyGraph()
        val = ConcurrentExecutionValidator()
        assert val.validate_readiness(g, ["exp_a"], "exp_b") is True

    def test_concurrent_execution_blocked_by_exclusion(self):
        g = ExperimentDependencyGraph()
        g.add_mutual_exclusion("exp_b", "exp_a")
        val = ConcurrentExecutionValidator()
        assert val.validate_readiness(g, ["exp_a"], "exp_b") is False


class TestPipelineStateMachine:
    def test_full_lifecycle_advance(self):
        sm = PipelineExecutionStateMachine("exp_001")
        assert sm.current_stage == PipelineStage.REQUESTED
        sm.advance_to_archived()
        assert sm.current_stage == PipelineStage.ARCHIVED
        assert sm.is_complete

    def test_stage_history_count(self):
        sm = PipelineExecutionStateMachine("exp_002")
        sm.advance_to_archived()
        summary = sm.get_state_summary()
        assert summary["stages_completed"] == len(PipelineStage)

    def test_single_advance(self):
        sm = PipelineExecutionStateMachine("exp_003")
        next_stage = sm.advance()
        assert next_stage == PipelineStage.REVIEWED
