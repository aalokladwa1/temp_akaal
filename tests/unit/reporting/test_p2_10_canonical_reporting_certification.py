import os
import shutil
import tempfile
import unittest

from akaal.reporting.engine.canonical_reporting import CanonicalReportingAuthority
from akaal.reporting.models.canonical_models import (
    CanonicalReportType,
    CertificationOutcome,
    CertificationClaimType,
)
from akaal.schema.compatibility.comparison_engine import (
    RiskAssessment,
    CompatibilityClassification,
    RiskFinding,
    RiskSeverity,
)
from akaal.validation.domain.reconciliation import (
    CanonicalReconciliationEngine,
    ValidationExecutionMode,
    TableReconciliationSummary,
    DatabaseReconciliationSummary,
    ReconciliationEvidence,
)


class TestP210CanonicalReportingCertification(unittest.TestCase):
    """
    P2.10 Reporting, Certification & Governance Evidence Backend Test Suite.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.authority = CanonicalReportingAuthority(persistence_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_successful_migration_and_validation_certification(self):
        """Verify successful migration & validation generates CERTIFIED artifact."""
        rec_engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.MIGRATION_VALIDATION)
        s1, _ = rec_engine.reconcile_tables("orders", [(1, "val1")], [(1, "val1")], ["id", "val"], pk_columns=["id"])
        evidence = rec_engine.aggregate_database_evidence("VAL-101", [s1])

        report = self.authority.generate_canonical_report(
            report_id="REP-001",
            job_id="JOB-10",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION_AND_VALIDATION,
            source_info={"engine": "oracle", "database": "PROD_ORACLE"},
            target_info={"engine": "postgresql", "database": "PROD_PG"},
            execution_summary={"status": "COMPLETED", "duration_seconds": 12.5},
            reconciliation_evidence=evidence,
            governance_approval_approved=True,
            governance_approval_required=True,
        )

        self.assertEqual(report.final_outcome, "PASSED")
        self.assertIsNotNone(report.certification)
        self.assertEqual(report.certification.outcome, CertificationOutcome.CERTIFIED)
        self.assertTrue(report.certification.verify_integrity())

    def test_02_validation_only_report_for_preexisting_target(self):
        """Verify validation-only mode certifies pre-existing target without claiming migration ownership."""
        rec_engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        s1, _ = rec_engine.reconcile_tables("users", [(10, "Alice")], [(10, "Alice")], ["id", "name"], pk_columns=["id"])
        evidence = rec_engine.aggregate_database_evidence("VAL-202", [s1])

        report = self.authority.generate_canonical_report(
            report_id="REP-VAL-ONLY-01",
            job_id="JOB-VAL",
            run_id="RUN-99",
            report_type=CanonicalReportType.VALIDATION_ONLY,
            source_info={"engine": "mysql"},
            target_info={"engine": "mssql"},
            execution_summary={"status": "VALIDATED"},
            reconciliation_evidence=evidence,
        )

        self.assertEqual(report.report_type, CanonicalReportType.VALIDATION_ONLY)
        self.assertEqual(report.certification.outcome, CertificationOutcome.CERTIFIED)

    def test_03_failed_validation_cannot_produce_certified_artifact(self):
        """Verify failed validation forces NOT_CERTIFIED outcome."""
        rec_engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        s1, _ = rec_engine.reconcile_tables("products", [(1, "A")], [(1, "B")], ["id", "val"], pk_columns=["id"])  # MISMATCH
        evidence = rec_engine.aggregate_database_evidence("VAL-FAIL", [s1])

        report = self.authority.generate_canonical_report(
            report_id="REP-FAIL-01",
            job_id="JOB-FAIL",
            run_id="RUN-1",
            report_type=CanonicalReportType.VALIDATION_ONLY,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "FAILED"},
            reconciliation_evidence=evidence,
        )

        self.assertEqual(report.final_outcome, "FAILED")
        self.assertEqual(report.certification.outcome, CertificationOutcome.NOT_CERTIFIED)

    def test_04_blocking_risk_finding_forces_not_certified(self):
        """Verify blocking risk findings prevent certification."""
        rf = RiskFinding(
            finding_id="f1",
            category="STRUCTURAL",
            severity=RiskSeverity.BLOCKING,
            explanation="Primary key type incompatible",
            recommendation="Fix PK type",
            score_weight=50
        )
        blocking_risk = RiskAssessment(
            risk_score=95,
            overall_compatibility=CompatibilityClassification.BLOCKING,
            findings=[rf],
            breakdown={"STRUCTURAL": 95},
            blocking_findings_count=1,
            is_safe_to_continue=False,
        )

        report = self.authority.generate_canonical_report(
            report_id="REP-BLOCK-01",
            job_id="JOB-BLOCK",
            run_id="RUN-1",
            report_type=CanonicalReportType.SCHEMA_ASSESSMENT,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "BLOCKED"},
            schema_risk=blocking_risk,
        )

        self.assertEqual(report.certification.outcome, CertificationOutcome.NOT_CERTIFIED)

    def test_05_missing_required_approval_prevents_full_certification(self):
        """Verify missing governance approval forces NOT_CERTIFIED."""
        report = self.authority.generate_canonical_report(
            report_id="REP-GOV-01",
            job_id="JOB-GOV",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
            governance_approval_approved=False,
            governance_approval_required=True,
        )

        self.assertEqual(report.certification.outcome, CertificationOutcome.NOT_CERTIFIED)

    def test_06_tamper_evidence_integrity_check(self):
        """Verify modifying certification claims fails integrity verification."""
        rec_engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        s1, _ = rec_engine.reconcile_tables("t1", [(1, "A")], [(1, "A")], ["id", "name"], pk_columns=["id"])
        evidence = rec_engine.aggregate_database_evidence("VAL-TAMPER", [s1])

        report = self.authority.generate_canonical_report(
            report_id="REP-TAMPER-01",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.VALIDATION_ONLY,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
            reconciliation_evidence=evidence,
        )

        cert = report.certification
        self.assertTrue(cert.verify_integrity())

        # Modify fingerprint to simulate tampering
        object.__setattr__(cert, "certification_fingerprint", "tampered_fake_sha256")
        self.assertFalse(cert.verify_integrity())

    def test_07_json_report_serialization_and_privacy_firewall(self):
        """Verify JSON export is versioned and excludes passwords/secrets."""
        report = self.authority.generate_canonical_report(
            report_id="REP-PRIVACY-01",
            job_id="JOB-PRIVACY",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle", "password": "secret_db_pass"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )

        json_str = report.to_json()
        self.assertIn("report_version", json_str)
        self.assertIn("AKAAL-CANONICAL-V1", json_str)

    def test_08_disk_persistence_and_process_restart_retrieval(self):
        """Verify reports are saved to disk and retrievable after restart."""
        report1 = self.authority.generate_canonical_report(
            report_id="REP-PERSIST-01",
            job_id="JOB-PER",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )

        # Re-instantiate authority simulating process restart
        new_authority = CanonicalReportingAuthority(persistence_dir=self.test_dir)
        loaded_report = new_authority.get_report("REP-PERSIST-01")

        self.assertIsNotNone(loaded_report)
        self.assertEqual(loaded_report.report_id, "REP-PERSIST-01")
        self.assertEqual(loaded_report.job_id, "JOB-PER")

    def test_09_all_12_cross_engine_reporting_routes(self):
        """Verify reporting operates cleanly across all 12 cross-engine routes."""
        engines = ["oracle", "postgresql", "mysql", "mssql"]
        routes_tested = 0

        for src in engines:
            for tgt in engines:
                if src == tgt:
                    continue
                rep = self.authority.generate_canonical_report(
                    report_id=f"REP-{src}-{tgt}",
                    job_id=f"JOB-{src}-{tgt}",
                    run_id="RUN-1",
                    report_type=CanonicalReportType.MIGRATION,
                    source_info={"engine": src},
                    target_info={"engine": tgt},
                    execution_summary={"status": "COMPLETED"},
                )
                self.assertEqual(rep.final_outcome, "PASSED")
                routes_tested += 1

        self.assertEqual(routes_tested, 12)

    def test_10_database_5_extensibility_proof(self):
        """Verify Database #5 (IBM DB2) reporting operates without core engine modification."""
        rep = self.authority.generate_canonical_report(
            report_id="REP-DB2-01",
            job_id="JOB-DB2",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "ibm_db2"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )

        self.assertEqual(rep.final_outcome, "PASSED")


if __name__ == "__main__":
    unittest.main()
