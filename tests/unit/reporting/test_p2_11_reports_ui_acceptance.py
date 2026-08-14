import json
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
)


class TestP211ReportsUIAcceptance(unittest.TestCase):
    """
    P2.11 Reports, Validation Results, Certification & Evidence UI Acceptance Test Suite.
    Verifies Truth-Firewall frontend contract requirements.
    """

    def setUp(self):
        self.authority = CanonicalReportingAuthority()

    def test_01_not_certified_cannot_be_represented_as_certified(self):
        """REQ-P2.11-03: NOT_CERTIFIED cannot render as CERTIFIED."""
        report = self.authority.generate_canonical_report(
            report_id="REP-UI-01",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "FAILED"},
            errors=["Validation failed"],
        )

        self.assertEqual(report.certification.outcome, CertificationOutcome.NOT_CERTIFIED)
        self.assertNotEqual(report.certification.outcome, CertificationOutcome.CERTIFIED)

    def test_02_validation_only_does_not_claim_migration_ownership(self):
        """REQ-P2.11-05: Validation-only report does not claim AKAAL performed migration."""
        report = self.authority.generate_canonical_report(
            report_id="REP-UI-VAL-01",
            job_id="JOB-VAL",
            run_id="RUN-1",
            report_type=CanonicalReportType.VALIDATION_ONLY,
            source_info={"engine": "mysql"},
            target_info={"engine": "mssql"},
            execution_summary={"status": "VALIDATED"},
        )

        self.assertEqual(report.report_type, CanonicalReportType.VALIDATION_ONLY)
        self.assertNotEqual(report.report_type, CanonicalReportType.MIGRATION)

    def test_03_blocking_schema_findings_remain_visible(self):
        """REQ-P2.11-06: Blocking schema findings remain visible."""
        rf = RiskFinding(
            finding_id="f1",
            category="STRUCTURAL",
            severity=RiskSeverity.BLOCKING,
            explanation="Primary key type incompatible",
            recommendation="Fix PK type",
            score_weight=50,
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
            report_id="REP-UI-BLOCK",
            job_id="JOB-BLOCK",
            run_id="RUN-1",
            report_type=CanonicalReportType.SCHEMA_ASSESSMENT,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "BLOCKED"},
            schema_risk=blocking_risk,
        )

        self.assertEqual(report.schema_summary["blocking_findings_count"], 1)
        self.assertEqual(report.certification.outcome, CertificationOutcome.NOT_CERTIFIED)

    def test_04_secrets_and_credentials_redacted_from_ui_payload(self):
        """REQ-P2.11-11: Secrets/redacted values are not exposed by Reports UI."""
        report = self.authority.generate_canonical_report(
            report_id="REP-UI-SECRET",
            job_id="JOB-SEC",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle", "password": "super_secret_password_123"},
            target_info={"engine": "postgresql", "api_key": "secret_key"},
            execution_summary={"status": "COMPLETED"},
        )

        json_str = report.to_json()
        self.assertNotIn("super_secret_password_123", json_str)
        self.assertNotIn("secret_key", json_str)
        self.assertIn("[REDACTED_SECRET]", json_str)

    def test_05_integrity_verification_backend_authoritative(self):
        """REQ-P2.11-09 & REQ-P2.11-10: Integrity verification invokes backend authority."""
        report = self.authority.generate_canonical_report(
            report_id="REP-UI-INTEG",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )

        cert = report.certification
        self.assertTrue(self.authority.verify_certification_integrity(cert))

        # Mutate fingerprint to simulate tampering
        object.__setattr__(cert, "certification_fingerprint", "fake_sha256")
        self.assertFalse(self.authority.verify_certification_integrity(cert))


if __name__ == "__main__":
    unittest.main()
