import os
import io
import json
import zipfile
import tempfile
import hashlib
import unittest

from akaal.reporting.engine.canonical_reporting import CanonicalReportingAuthority
from akaal.reporting.engine.export_service import CanonicalReportExportService
from akaal.reporting.models.canonical_models import (
    CanonicalReport,
    CanonicalReportType,
    CertificationOutcome,
    CertificationArtifact,
)
from akaal.validation.domain.reconciliation import (
    ReconciliationEvidence,
    TableReconciliationSummary,
    DatabaseReconciliationSummary,
    ValidationExecutionMode,
)
from akaal.gateway.engine_gateway import EngineGateway


class TestP2121ExportDeliverySemanticAcceptance(unittest.TestCase):
    """
    P2.12.1 Dedicated Hostile Acceptance Suite:
    Export Delivery, Evidence Packaging, Security Redaction, Path Traversal & Evidence Binding Audit.
    """

    def setUp(self):
        self.authority = CanonicalReportingAuthority()
        self.exporter = CanonicalReportExportService(self.authority)

        db_summary = DatabaseReconciliationSummary(
            tables_validated=10,
            tables_matched=10,
            tables_mismatched=0,
            tables_unsupported=0,
            tables_indeterminate=0,
            tables_failed=0,
            total_rows_evaluated=100000,
            total_source_only_rows=0,
            total_target_only_rows=0,
            total_value_mismatch_rows=0,
            final_status="MATCHED",
        )

        rec_evidence = ReconciliationEvidence(
            validation_id="VAL-JOB-ALPHA-RUN-1",
            execution_mode=ValidationExecutionMode.MIGRATION_VALIDATION,
            serialization_version="AKAAL-CANONICAL-V1",
            hash_algorithm="SHA-256",
            table_summaries=[
                TableReconciliationSummary(
                    table_name="accounts",
                    source_rows=100000,
                    target_rows=100000,
                    matched_count=100000,
                    source_only_count=0,
                    target_only_count=0,
                    value_mismatch_count=0,
                    unsupported_count=0,
                    indeterminate_count=0,
                    error_count=0,
                    mismatched_chunks_count=0,
                    status="MATCHED",
                )
            ],
            database_summary=db_summary,
            evidence_fingerprint="1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
        )

        self.valid_report = self.authority.generate_canonical_report(
            report_id="REP-ALPHA-01",
            job_id="JOB-ALPHA",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION_AND_VALIDATION,
            source_info={"engine": "Oracle 19c", "password": "hostile_oracle_password_888"},
            target_info={"engine": "PostgreSQL 16", "token": "hostile_pg_token_777"},
            execution_summary={"status": "COMPLETED"},
            reconciliation_evidence=rec_evidence,
            governance_approval_required=True,
            governance_approval_approved=True,
        )

    def test_01_not_certified_export_cannot_upgrade_to_certified(self):
        """1. NOT_CERTIFIED canonical report cannot produce a CERTIFIED export artifact."""
        fail_report = self.authority.generate_canonical_report(
            report_id="REP-FAIL-01",
            job_id="JOB-FAIL",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION,
            source_info={"engine": "Oracle"},
            target_info={"engine": "PostgreSQL"},
            execution_summary={"status": "FAILED"},
            errors=["Deep reconciliation checksum mismatch"],
        )
        pdf_bytes = self.exporter.export_pdf_dossier(fail_report)
        self.assertIn(b"CERTIFICATION OUTCOME: NOT_CERTIFIED", pdf_bytes)
        self.assertNotIn(b"CERTIFICATION OUTCOME: CERTIFIED\n", pdf_bytes)

    def test_02_cross_job_substitution_attack_fails_closed(self):
        """2. Cross-job artifact substitution in ZIP package fails verification with INVALID."""
        zip_bytes = self.exporter.export_evidence_package(self.valid_report)
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as r_zip:
            with zipfile.ZipFile(zip_buffer, "w") as w_zip:
                for item in r_zip.infolist():
                    content = r_zip.read(item.filename)
                    if item.filename == "evidence/manifest.json":
                        m = json.loads(content.decode("utf-8"))
                        m["job_id"] = "JOB-ATTACKER-VICTIM-SUBSTITUTE"
                        content = json.dumps(m).encode("utf-8")
                    w_zip.writestr(item, content)

        res = self.exporter.verify_evidence_package(zip_buffer.getvalue())
        self.assertEqual(res["status"], "INVALID")
        self.assertIn("hash mismatch", res["reason"].lower())

    def test_03_cross_run_substitution_attack_fails_closed(self):
        """3. Cross-run artifact substitution where manifest is altered fails verification."""
        zip_bytes = self.exporter.export_evidence_package(self.valid_report)
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as r_zip:
            manifest_obj = json.loads(r_zip.read("evidence/manifest.json").decode("utf-8"))
            manifest_obj["run_id"] = "RUN-SUBSTITUTED-99"
            manifest_bytes = json.dumps(manifest_obj).encode("utf-8")

            with zipfile.ZipFile(zip_buffer, "w") as w_zip:
                checksum_lines = []
                for item in r_zip.infolist():
                    if item.filename == "integrity/checksums.sha256":
                        continue
                    content = manifest_bytes if item.filename == "evidence/manifest.json" else r_zip.read(item.filename)
                    h = hashlib.sha256(content).hexdigest()
                    checksum_lines.append(f"{h}  {item.filename}")
                    w_zip.writestr(item.filename, content)

                w_zip.writestr("integrity/checksums.sha256", "\n".join(checksum_lines).encode("utf-8"))

        res = self.exporter.verify_evidence_package(zip_buffer.getvalue())
        self.assertEqual(res["status"], "INVALID")
        self.assertIn("Run ID mismatch", res["reason"])

    def test_04_zip_path_traversal_attack_fails_closed(self):
        """4. ZIP containing path traversal entries (../, absolute paths) is rejected as INVALID."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as z:
            z.writestr("../../../etc/passwd", "root:x:0:0:")
            z.writestr("evidence/manifest.json", "{}")
            z.writestr("integrity/checksums.sha256", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  evidence/manifest.json")

        res = self.exporter.verify_evidence_package(zip_buffer.getvalue())
        self.assertEqual(res["status"], "INVALID")
        self.assertIn("Path traversal attempt detected", res["reason"])

    def test_05_zip_unmanifested_extra_artifact_fails_closed(self):
        """5. ZIP containing unmanifested extra file is rejected as INVALID."""
        zip_bytes = self.exporter.export_evidence_package(self.valid_report)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as r_zip:
            with zipfile.ZipFile(zip_buffer, "w") as w_zip:
                for item in r_zip.infolist():
                    w_zip.writestr(item, r_zip.read(item.filename))
                w_zip.writestr("evidence/unauthorized_payload.exe", b"malware_bytes")

        res = self.exporter.verify_evidence_package(zip_buffer.getvalue())
        self.assertEqual(res["status"], "INVALID")
        self.assertIn("Unmanifested extra artifact detected", res["reason"])

    def test_06_zip_duplicate_checksum_declarations_fail_closed(self):
        """6. ZIP containing duplicate checksum declarations is rejected as INVALID."""
        zip_bytes = self.exporter.export_evidence_package(self.valid_report)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as r_zip:
            with zipfile.ZipFile(zip_buffer, "w") as w_zip:
                for item in r_zip.infolist():
                    content = r_zip.read(item.filename)
                    if item.filename == "integrity/checksums.sha256":
                        lines = content.decode("utf-8").strip().split("\n")
                        lines.append(lines[0])  # Duplicate entry
                        content = "\n".join(lines).encode("utf-8")
                    w_zip.writestr(item, content)

        res = self.exporter.verify_evidence_package(zip_buffer.getvalue())
        self.assertEqual(res["status"], "INVALID")
        self.assertIn("Duplicate checksum entry", res["reason"])

    def test_07_secrets_redaction_across_all_export_formats(self):
        """7. Plaintext credentials cannot leak into exported JSON, PDF, or evidence ZIP packages."""
        json_rep = self.exporter.export_json_report(self.valid_report)
        self.assertNotIn("hostile_oracle_password_888", json_rep)
        self.assertNotIn("hostile_pg_token_777", json_rep)
        self.assertIn("[REDACTED_SECRET]", json_rep)

        pdf_bytes = self.exporter.export_pdf_dossier(self.valid_report)
        self.assertNotIn(b"hostile_oracle_password_888", pdf_bytes)
        self.assertNotIn(b"hostile_pg_token_777", pdf_bytes)

        zip_bytes = self.exporter.export_evidence_package(self.valid_report)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
            rep_json_in_zip = z.read("report/canonical-report.json").decode("utf-8")
            self.assertNotIn("hostile_oracle_password_888", rep_json_in_zip)
            self.assertNotIn("hostile_pg_token_777", rep_json_in_zip)

    def test_08_privacy_boundaries_zero_raw_rows_or_lobs(self):
        """8. Raw customer rows and LOB contents are absent from exports."""
        json_rep = self.exporter.export_json_report(self.valid_report)
        parsed = json.loads(json_rep)
        self.assertNotIn("raw_rows", parsed)
        self.assertNotIn("raw_lobs", parsed)
        self.assertNotIn("sql_bodies", parsed)

    def test_09_validation_only_semantics_preserved(self):
        """9. Validation-only disclaimer present across JSON, PDF, and ZIP packages."""
        val_report = self.authority.generate_canonical_report(
            report_id="REP-VAL-SEMANTICS",
            job_id="JOB-VAL-ONLY",
            run_id="RUN-1",
            report_type=CanonicalReportType.VALIDATION_ONLY,
            source_info={"engine": "MySQL"},
            target_info={"engine": "MSSQL"},
            execution_summary={"status": "VALIDATED"},
        )
        pdf_bytes = self.exporter.export_pdf_dossier(val_report)
        self.assertIn(b"VALIDATION-ONLY ASSESSMENT", pdf_bytes)

        zip_bytes = self.exporter.export_evidence_package(val_report)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
            manifest = json.loads(z.read("evidence/manifest.json").decode("utf-8"))
            self.assertEqual(manifest["report_type"], "VALIDATION_ONLY")

    def test_10_safe_filepath_save_path_traversal_prevented(self):
        """10. save_export_to_file rejects dangerous path traversal targets."""
        ok = self.exporter.save_export_to_file("{}", "../../../dangerous_overwrite.json")
        self.assertFalse(ok)

    def test_11_engine_gateway_export_capability_invocations(self):
        """11. EngineGateway exports capabilities through IPC interface cleanly."""
        gateway = EngineGateway()
        res_json = gateway.export_canonical_report({"report_id": "REP-ALPHA-01"})
        self.assertEqual(res_json["status"], "SUCCESS")

        res_pdf = gateway.export_pdf_dossier({"report_id": "REP-ALPHA-01"})
        self.assertEqual(res_pdf["status"], "SUCCESS")
        self.assertEqual(res_pdf["format"], "PDF")

        res_zip = gateway.export_evidence_package({"report_id": "REP-ALPHA-01"})
        self.assertEqual(res_zip["status"], "SUCCESS")
        self.assertEqual(res_zip["format"], "ZIP")

        res_verify = gateway.verify_evidence_package({"payload_b64": res_zip["payload_b64"]})
        self.assertEqual(res_verify["status"], "VALID")

    def test_12_no_fake_digital_signature_claims(self):
        """12. Export artifacts explicitly clarify SHA-256 fingerprint is not an X.509 signature."""
        pdf_cert = self.exporter.export_pdf_certificate(self.valid_report.certification)
        self.assertIn(b"not an X.509", pdf_cert)


if __name__ == "__main__":
    unittest.main()
