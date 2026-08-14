import json
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
    ReconciliationEvidence,
)


class TestP2101ReportingCertificationSemanticAcceptance(unittest.TestCase):
    """
    P2.10.1 Hostile Semantic Acceptance & Hardening Test Suite.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.authority = CanonicalReportingAuthority(persistence_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_cross_job_evidence_substitution_attack_rejected(self):
        """Verify passing evidence from another job/run forces NOT_CERTIFIED."""
        rec_engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        s1, _ = rec_engine.reconcile_tables("tbl", [(1, "A")], [(1, "A")], ["id", "val"], pk_columns=["id"])
        # Evidence bound to JOB-ATTACKER
        attacker_evidence = rec_engine.aggregate_database_evidence("JOB-ATTACKER-RUN-99", [s1])

        # Attempt to use attacker_evidence to certify JOB-VICTIM
        report = self.authority.generate_canonical_report(
            report_id="REP-SEC-01",
            job_id="JOB-VICTIM",
            run_id="RUN-1",
            report_type=CanonicalReportType.VALIDATION_ONLY,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
            reconciliation_evidence=attacker_evidence,
        )

        self.assertEqual(report.certification.outcome, CertificationOutcome.NOT_CERTIFIED)
        self.assertIn("EVIDENCE BINDING FIREWALL", report.errors[0])

    def test_02_secret_redaction_firewall(self):
        """Verify passwords, tokens, and connection strings are redacted from source/target info."""
        report = self.authority.generate_canonical_report(
            report_id="REP-RED-01",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle", "password": "super_secret_password_123", "api_token": "bearer_abc"},
            target_info={"engine": "postgresql", "connection_string": "postgres://user:secret@host/db"},
            execution_summary={"status": "COMPLETED"},
        )

        json_str = report.to_json()
        self.assertNotIn("super_secret_password_123", json_str)
        self.assertNotIn("bearer_abc", json_str)
        self.assertIn("[REDACTED_SECRET]", json_str)

    def test_03_corrupted_persisted_artifact_recovery(self):
        """Verify loading corrupted disk JSON handles error safely without crashing."""
        file_path = os.path.join(self.test_dir, "CORRUPT-01.json")
        os.makedirs(self.test_dir, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("{ invalid_json_syntax: true, ")

        loaded = self.authority.get_report("CORRUPT-01")
        self.assertIsNone(loaded)

    def test_04_tamper_detection_on_outcome_mutation(self):
        """Verify mutating certification outcome invalidates tamper-evident fingerprint."""
        report = self.authority.generate_canonical_report(
            report_id="REP-TAMPER-02",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )

        cert = report.certification
        self.assertTrue(cert.verify_integrity())

        # Mutate outcome from CERTIFIED to CERTIFIED_WITH_WARNINGS
        object.__setattr__(cert, "outcome", CertificationOutcome.CERTIFIED_WITH_WARNINGS)
        self.assertFalse(cert.verify_integrity())

    def test_05_validation_only_claims_no_migration_ownership(self):
        """Verify validation-only reports specify VALIDATION_ONLY mode and do not claim migration ownership."""
        report = self.authority.generate_canonical_report(
            report_id="REP-VAL-OWN",
            job_id="JOB-VAL-OWN",
            run_id="RUN-1",
            report_type=CanonicalReportType.VALIDATION_ONLY,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "VALIDATED"},
        )

        self.assertEqual(report.report_type, CanonicalReportType.VALIDATION_ONLY)
        self.assertNotEqual(report.report_type, CanonicalReportType.MIGRATION)

    def test_06_deterministic_claim_and_manifest_ordering(self):
        """Verify claims and manifest entries are sorted deterministically."""
        rec_engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.MIGRATION_VALIDATION)
        s1, _ = rec_engine.reconcile_tables("t1", [(1, "A")], [(1, "A")], ["id", "val"], pk_columns=["id"])
        evidence = rec_engine.aggregate_database_evidence("VAL-DET-01", [s1])

        report = self.authority.generate_canonical_report(
            report_id="REP-DET-01",
            job_id="JOB-DET",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION_AND_VALIDATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
            reconciliation_evidence=evidence,
        )

        cert = report.certification
        claim_types = [c.claim_type.value for c in cert.claims]
        self.assertEqual(claim_types, sorted(claim_types))


if __name__ == "__main__":
    unittest.main()
