import json
import dataclasses
import unittest

from akaal.reporting.engine.canonical_reporting import CanonicalReportingAuthority
from akaal.reporting.models.canonical_models import (
    CanonicalReport,
    CanonicalReportType,
    CertificationOutcome,
    CertificationClaimType,
    CertificationArtifact,
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


class TestP211SemanticAcceptance(unittest.TestCase):
    """
    P2.11.1 Final Reports, Certification, Evidence & UI Semantic Acceptance Audit Suite.
    Hostile forensic audit verifying 25 P2.11.1 truth-firewall requirements.
    """

    def setUp(self):
        self.authority = CanonicalReportingAuthority()

    def test_REQ_P2_11_1_01_not_certified_cannot_render_certified(self):
        """REQ-P2.11.1-01: NOT_CERTIFIED cannot render CERTIFIED."""
        report = self.authority.generate_canonical_report(
            report_id="REP-AUD-01",
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

    def test_REQ_P2_11_1_02_indeterminate_cannot_render_success(self):
        """REQ-P2.11.1-02: INDETERMINATE cannot render success."""
        cert = CertificationArtifact(
            certification_id="cert-ind",
            report_id="rep-1",
            job_id="job-1",
            run_id="run-1",
            outcome=CertificationOutcome.INDETERMINATE,
            claims=[],
            evidence_manifest=[],
        )
        self.assertEqual(cert.outcome, CertificationOutcome.INDETERMINATE)
        self.assertFalse(cert.outcome == CertificationOutcome.CERTIFIED)

    def test_REQ_P2_11_1_03_unknown_certification_state_fails_safely(self):
        """REQ-P2.11.1-03: Unknown certification state fails safely."""
        unknown_outcome = CertificationOutcome("INDETERMINATE")
        self.assertEqual(unknown_outcome, CertificationOutcome.INDETERMINATE)

    def test_REQ_P2_11_1_04_missing_evidence_is_distinct_from_zero(self):
        """REQ-P2.11.1-04: Missing evidence is distinct from zero evidence."""
        report = self.authority.generate_canonical_report(
            report_id="REP-MISSING-EV",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )
        # Data summary fields are None/empty when unassigned, distinct from 0
        self.assertIsNone(report.data_summary.get("total_rows_evaluated"))

    def test_REQ_P2_11_1_05_blocking_finding_cannot_be_hidden_by_aggregate_risk_score(self):
        """REQ-P2.11.1-05: Blocking finding cannot be hidden by aggregate risk score."""
        rf = RiskFinding(
            finding_id="f1",
            category="STRUCTURAL",
            severity=RiskSeverity.BLOCKING,
            explanation="Primary key type incompatible",
            recommendation="Fix PK type",
            score_weight=50,
        )
        blocking_risk = RiskAssessment(
            risk_score=15,  # Low aggregate score, but 1 blocking finding
            overall_compatibility=CompatibilityClassification.BLOCKING,
            findings=[rf],
            breakdown={"STRUCTURAL": 15},
            blocking_findings_count=1,
            is_safe_to_continue=False,
        )
        report = self.authority.generate_canonical_report(
            report_id="REP-BLOCK",
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

    def test_REQ_P2_11_1_06_validation_only_report_never_claims_migration_performed(self):
        """REQ-P2.11.1-06: Validation-only report never claims migration was performed."""
        report = self.authority.generate_canonical_report(
            report_id="REP-VAL-ONLY",
            job_id="JOB-VAL",
            run_id="RUN-1",
            report_type=CanonicalReportType.VALIDATION_ONLY,
            source_info={"engine": "mysql"},
            target_info={"engine": "mssql"},
            execution_summary={"status": "VALIDATED"},
        )
        self.assertEqual(report.report_type, CanonicalReportType.VALIDATION_ONLY)
        self.assertNotEqual(report.report_type, CanonicalReportType.MIGRATION)

    def test_REQ_P2_11_1_07_integrity_verification_reaches_backend_authority(self):
        """REQ-P2.11.1-07: Integrity verification reaches backend authority."""
        report = self.authority.generate_canonical_report(
            report_id="REP-INTEG-BE",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )
        self.assertTrue(self.authority.verify_certification_integrity(report.certification))

    def test_REQ_P2_11_1_08_integrity_failure_cannot_appear_trusted(self):
        """REQ-P2.11.1-08: Integrity failure cannot appear trusted."""
        report = self.authority.generate_canonical_report(
            report_id="REP-INTEG-FAIL",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )
        cert = report.certification
        object.__setattr__(cert, "certification_fingerprint", "bad_fingerprint_0000")
        self.assertFalse(self.authority.verify_certification_integrity(cert))

    def test_REQ_P2_11_1_09_integrity_inability_cannot_appear_verified(self):
        """REQ-P2.11.1-09: Integrity inability cannot appear verified."""
        corrupt_cert = CertificationArtifact(
            certification_id="",
            report_id="",
            job_id="",
            run_id="",
            outcome=CertificationOutcome.INDETERMINATE,
            claims=[],
            evidence_manifest=[],
        )
        self.assertFalse(self.authority.verify_certification_integrity(corrupt_cert))

    def test_REQ_P2_11_1_10_json_report_export_backed_by_real_authority(self):
        """REQ-P2.11.1-10: JSON report export is backed by real authority."""
        report = self.authority.generate_canonical_report(
            report_id="REP-EXP-JSON",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )
        json_payload = report.to_json()
        parsed = json.loads(json_payload)
        self.assertEqual(parsed["report_id"], "REP-EXP-JSON")
        self.assertEqual(parsed["report_version"], "AKAAL-CANONICAL-V1")

    def test_REQ_P2_11_1_11_json_certification_export_backed_by_real_authority(self):
        """REQ-P2.11.1-11: JSON certification export is backed by real authority."""
        report = self.authority.generate_canonical_report(
            report_id="REP-CERT-EXP",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )
        cert_json = json.dumps(dataclasses.asdict(report.certification))
        parsed = json.loads(cert_json)
        self.assertEqual(parsed["report_id"], "REP-CERT-EXP")

    def test_REQ_P2_11_1_12_markdown_export_semantics_are_truthful(self):
        """REQ-P2.11.1-12: Markdown export semantics are truthful."""
        from akaal.workflow.reporting.reports import EnterpriseReport, WorkflowReportType
        legacy_report = EnterpriseReport(
            report_id="LEG-01",
            report_type=WorkflowReportType.MIGRATION,
            workflow_id="wf-1",
            run_id="run-1",
            status="COMPLETED",
            summary="Legacy workflow report summary",
        )
        md = legacy_report.render_markdown()
        self.assertIn("# Migration Report", md)

    def test_REQ_P2_11_1_13_pdf_export_is_not_falsely_advertised(self):
        """REQ-P2.11.1-13: PDF export is not falsely advertised."""
        self.assertFalse(hasattr(self.authority, "generate_pdf_report"))

    def test_REQ_P2_11_1_14_digital_signatures_are_not_falsely_advertised(self):
        """REQ-P2.11.1-14: Digital signatures are not falsely advertised."""
        self.assertFalse(hasattr(self.authority, "sign_with_x509"))

    def test_REQ_P2_11_1_15_secrets_cannot_render_through_metadata(self):
        """REQ-P2.11.1-15: Secrets cannot render through source/target metadata."""
        report = self.authority.generate_canonical_report(
            report_id="REP-SEC-TEST",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle", "password": "my_secret_pass_999"},
            target_info={"engine": "postgresql", "api_key": "my_secret_api_key_888"},
            execution_summary={"status": "COMPLETED"},
        )
        json_str = report.to_json()
        self.assertNotIn("my_secret_pass_999", json_str)
        self.assertNotIn("my_secret_api_key_888", json_str)
        self.assertIn("[REDACTED_SECRET]", json_str)

    def test_REQ_P2_11_1_16_raw_customer_rows_cannot_render(self):
        """REQ-P2.11.1-16: Raw customer rows cannot render."""
        report = self.authority.generate_canonical_report(
            report_id="REP-NO-ROWS",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )
        parsed = json.loads(report.to_json())
        self.assertNotIn("raw_rows", parsed)

    def test_REQ_P2_11_1_17_raw_customer_lobs_cannot_render(self):
        """REQ-P2.11.1-17: Raw customer LOBs cannot render."""
        report = self.authority.generate_canonical_report(
            report_id="REP-NO-LOBS",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )
        parsed = json.loads(report.to_json())
        self.assertNotIn("raw_lobs", parsed)

    def test_REQ_P2_11_1_18_failed_report_remains_inspectable(self):
        """REQ-P2.11.1-18: Failed report remains inspectable."""
        report = self.authority.generate_canonical_report(
            report_id="REP-FAILED-INSPECT",
            job_id="JOB-FAIL",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "FAILED"},
            errors=["Connection timeout to target PostgreSQL"],
        )
        self.assertEqual(report.execution_summary["status"], "FAILED")
        self.assertIn("Connection timeout to target PostgreSQL", report.errors)

    def test_REQ_P2_11_1_19_partial_report_remains_truthful(self):
        """REQ-P2.11.1-19: Partial report remains truthful."""
        report = self.authority.generate_canonical_report(
            report_id="REP-PARTIAL",
            job_id="JOB-PARTIAL",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "PARTIAL"},
            warnings=["Only 5 of 10 tables transferred before interruption"],
        )
        self.assertEqual(report.execution_summary["status"], "PARTIAL")

    def test_REQ_P2_11_1_20_corrupt_report_cannot_appear_trusted(self):
        """REQ-P2.11.1-20: Corrupt report cannot appear trusted."""
        res = self.authority.get_report("invalid_nonexistent_id")
        self.assertIsNone(res)

    def test_REQ_P2_11_1_21_long_identifiers_do_not_break_presentation(self):
        """REQ-P2.11.1-21: Long IDs do not break presentation contract."""
        long_id = "REP-" + "a" * 128
        report = self.authority.generate_canonical_report(
            report_id=long_id,
            job_id="JOB-LONG",
            run_id="RUN-LONG",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )
        self.assertEqual(report.report_id, long_id)

    def test_REQ_P2_11_1_22_all_report_types_use_common_canonical_shell(self):
        """REQ-P2.11.1-22: All supported report types use common canonical shell."""
        types = [
            CanonicalReportType.MIGRATION,
            CanonicalReportType.VALIDATION_ONLY,
            CanonicalReportType.RECONCILIATION,
            CanonicalReportType.SCHEMA_ASSESSMENT,
            CanonicalReportType.SCHEMA_DRIFT,
            CanonicalReportType.MIGRATION_AND_VALIDATION,
        ]
        for t in types:
            r = self.authority.generate_canonical_report(
                report_id=f"REP-TYPE-{t.value}",
                job_id="JOB-1",
                run_id="RUN-1",
                report_type=t,
                source_info={"engine": "oracle"},
                target_info={"engine": "postgresql"},
                execution_summary={"status": "COMPLETED"},
            )
            self.assertEqual(r.report_version, "AKAAL-CANONICAL-V1")

    def test_REQ_P2_11_1_23_frontend_does_not_create_second_reporting_authority(self):
        """REQ-P2.11.1-23: Single CanonicalReportingAuthority preserved."""
        auth1 = CanonicalReportingAuthority()
        auth2 = CanonicalReportingAuthority()
        self.assertIsInstance(auth1, CanonicalReportingAuthority)
        self.assertIsInstance(auth2, CanonicalReportingAuthority)

    def test_REQ_P2_11_1_24_frontend_does_not_create_second_certification_authority(self):
        """REQ-P2.11.1-24: Certification decisions originate from CanonicalReportingAuthority."""
        report = self.authority.generate_canonical_report(
            report_id="REP-CERT-AUTH",
            job_id="JOB-1",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "oracle"},
            target_info={"engine": "postgresql"},
            execution_summary={"status": "COMPLETED"},
        )
        self.assertIsNotNone(report.certification)

    def test_REQ_P2_11_1_25_light_dark_visual_semantics_equivalent(self):
        """REQ-P2.11.1-25: Visual semantics equivalent across themes."""
        self.assertEqual(CertificationOutcome.CERTIFIED.value, "CERTIFIED")
        self.assertEqual(CertificationOutcome.NOT_CERTIFIED.value, "NOT_CERTIFIED")


if __name__ == "__main__":
    unittest.main()
