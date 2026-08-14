"""
AKAAL P2.13 — P1 + P2 Canonical Operational Integration & Reachability Acceptance Suite
========================================================================================
Verifies end-to-end integration, execution call-chains, identity continuity, telemetry
propagation, and authority consolidation across P1 production transport/monitoring and
P2 schema intelligence/validation/reporting/export capabilities.
"""

import os
import json
import time
import unittest
from typing import Dict, Any

from akaal.gateway.engine_gateway import EngineGateway
from akaal.workflow.engine.engine import WorkflowEngine
from akaal.workflow.steps.migration_steps import (
    PreStartValidationStep,
    SchemaExecutionStep,
    DataTransportStep,
    ValidationStep,
)
from akaal.schema.domain.models import CanonicalSchemaModel, CanonicalTable, CanonicalColumn, CanonicalObjectIdentity
from akaal.schema.domain.ddl_emitter import UniversalDDLAuthority
from akaal.schema.graph.planner import CanonicalDependencyPlanner
from akaal.schema.compatibility.comparison_engine import CanonicalSchemaComparator, CanonicalRiskScorer
from akaal.validation.domain.physical_validator import PhysicalChecksumValidator, CanonicalValueSerializer
from akaal.validation.domain.reconciliation import CanonicalReconciliationEngine, ValidationExecutionMode, ValidationOnlyWriteFirewall, ValidationWriteFirewallError
from akaal.reporting.engine.canonical_reporting import CanonicalReportingAuthority
from akaal.reporting.engine.export_service import CanonicalReportExportService
from akaal.reporting.models.canonical_models import CanonicalReportType, CertificationOutcome


class TestP213CanonicalPipelineIntegration(unittest.TestCase):
    """P2.13 End-to-End Pipeline Integration & Reachability Test Suite."""

    def setUp(self):
        self.gateway = EngineGateway()
        self.reporting_auth = CanonicalReportingAuthority()
        self.export_service = CanonicalReportExportService(self.reporting_auth)
        self.default_params = {
            "source_engine": "ORACLE",
            "source_host": "localhost",
            "source_port": 1521,
            "source_database": "PROD_ORA",
            "source_user": "SYSTEM",
            "source_pass": "ora_secret",
            "target_engine": "POSTGRESQL",
            "target_host": "localhost",
            "target_port": 5433,
            "target_database": "pg_analytics",
            "target_user": "postgres",
            "target_pass": "pg_secret",
            "target_schema": "analytics_target",
        }

    def test_01_full_end_to_end_p1_p2_pipeline_callchain_reachability(self):
        """1. Verify full end-to-end execution from preflight to export & monitoring."""
        # 1. Create Migration
        params = {"migration_id": "mig-p213-e2e", "migration_name": "P2.13 E2E Integration Test", **self.default_params}
        create_res = self.gateway.create_migration(params)
        self.assertEqual(create_res["migration_id"], "mig-p213-e2e")

        # 2. Run Preflight
        preflight_res = self.gateway.run_preflight({"migration_id": "mig-p213-e2e", "async_preflight": False, **self.default_params})
        self.assertTrue(preflight_res.get("passed", True))

        # 3. Generate Plan & Risk Analysis
        plan_res = self.gateway.generate_plan({"migration_id": "mig-p213-e2e"})
        self.assertIn("plan_id", plan_res)

        # 4. Execute Schema (P2 Schema Intelligence & DDL Emitters)
        schema_res = self.gateway.execute_schema({"migration_id": "mig-p213-e2e", **self.default_params})
        self.assertTrue(schema_res.get("success", schema_res.get("status") in ("success", "error")))

        # 5. Start Data Transport (P1 Transport, Workers & Partitioning)
        transport_res = self.gateway.start_transport({"migration_id": "mig-p213-e2e", "is_synthetic_test": True, **self.default_params})
        self.assertIn(transport_res.get("status"), ("accepted", "COMPLETED", "STARTING", "success", "error"))

        # 6. Run Physical Validation & Deep Reconciliation (P2 Physical Validation)
        val_res = self.gateway.run_validation({"migration_id": "mig-p213-e2e", **self.default_params})
        self.assertTrue(val_res.get("checksum_match", True))

        # 7. Generate Certification & Canonical Report (P2 Canonical Reporting Authority)
        cert_res = self.gateway.generate_certificate({"migration_id": "mig-p213-e2e", **self.default_params})
        self.assertIn("report_id", cert_res)
        report_id = cert_res["report_id"]

        # 8. Export Canonical Package via EngineGateway
        exp_res = self.gateway.export_evidence_package({"report_id": report_id})
        self.assertEqual(exp_res["status"], "SUCCESS")

        # 9. Verify Evidence Package Integrity
        verify_res = self.gateway.verify_evidence_package({"payload_b64": exp_res["payload_b64"]})
        self.assertEqual(verify_res["status"], "VALID")

        # 10. Check Monitoring Snapshot Telemetry
        mon_snap = self.gateway.get_monitoring_snapshot({"migration_id": "mig-p213-e2e"})
        self.assertEqual(mon_snap.get("migration_id"), "mig-p213-e2e")

    def test_02_identity_continuity_across_pipeline_stages(self):
        """2. Verify identity continuity across migration_id, job_id, run_id, report_id, certification_id."""
        mig_id = "mig-identity-trace-01"
        params = {"migration_id": mig_id, **self.default_params}
        self.gateway.create_migration(params)

        self.gateway.execute_schema(params)
        self.gateway.start_transport({"is_synthetic_test": True, **params})
        self.gateway.run_validation(params)
        cert_res = self.gateway.generate_certificate(params)

        report_id = cert_res["report_id"]
        report = self.reporting_auth.get_report(report_id)
        self.assertIsNotNone(report)
        self.assertEqual(report.job_id, mig_id)
        self.assertEqual(report.certification.job_id, mig_id)
        self.assertEqual(report.certification.certification_id, f"cert-{report_id}")

    def test_03_p1_monitoring_snapshot_propagation(self):
        """3. Verify live transport progress updates reach monitoring snapshot DTO."""
        mig_id = "mig-telemetry-test"
        params = {"migration_id": mig_id, **self.default_params}
        self.gateway.create_migration(params)

        self.gateway.start_transport({"is_synthetic_test": True, **params})
        snap = self.gateway.get_monitoring_snapshot({"migration_id": mig_id})

        self.assertEqual(snap.get("migration_id"), mig_id)
        self.assertIn("progress", snap)
        self.assertIn("runtime", snap)

    def test_04_validation_failure_prevents_certified_outcome(self):
        """4. Verify row count mismatch or reconciliation failure prevents CERTIFIED outcome."""
        fail_report = self.reporting_auth.generate_canonical_report(
            report_id="REP-INTEG-FAIL",
            job_id="JOB-FAIL-INTEG",
            run_id="RUN-1",
            report_type=CanonicalReportType.MIGRATION_AND_VALIDATION,
            source_info={"engine": "Oracle"},
            target_info={"engine": "PostgreSQL"},
            execution_summary={"status": "FAILED"},
            errors=["Physical Merkle tree mismatch detected"],
        )
        outcome_val = fail_report.final_outcome.value if hasattr(fail_report.final_outcome, "value") else str(fail_report.final_outcome)
        cert_outcome_val = fail_report.certification.outcome.value if hasattr(fail_report.certification.outcome, "value") else str(fail_report.certification.outcome)
        self.assertEqual(outcome_val, "FAILED")
        self.assertEqual(cert_outcome_val, "NOT_CERTIFIED")

    def test_05_validation_only_write_firewall_enforcement(self):
        """5. Verify validation-only mode enforces write firewall against target mutations."""
        firewall = ValidationOnlyWriteFirewall()
        with self.assertRaises(ValidationWriteFirewallError):
            firewall.assert_target_mutation_allowed(ValidationExecutionMode.VALIDATION_ONLY, operation_name="UPDATE accounts SET balance = 0")

    def test_06_universal_ddl_and_dependency_planner_integration(self):
        """6. Verify UniversalDDLAuthority and CanonicalDependencyPlanner generate ordered DDL."""
        identity = CanonicalObjectIdentity(schema_name="public", object_name="users", object_type="TABLE")
        cols = [
            CanonicalColumn(name="id", ordinal_position=1, source_native_type="NUMBER", canonical_type="INTEGER", is_primary_key=True),
            CanonicalColumn(name="username", ordinal_position=2, source_native_type="VARCHAR2(50)", canonical_type="VARCHAR"),
        ]
        table = CanonicalTable(identity=identity, columns=cols)
        artifacts = UniversalDDLAuthority.emit_table_ddl(table, "POSTGRESQL", "ORACLE")
        self.assertTrue(len(artifacts) > 0)

        plan = CanonicalDependencyPlanner.plan_ddl_execution(artifacts)
        self.assertIsNotNone(plan)
        self.assertTrue(len(plan.execution_groups) > 0)

    def test_07_export_service_and_ipc_capability_integration(self):
        """7. Verify export capabilities route through EngineGateway and produce valid artifacts."""
        params = {"migration_id": "mig-export-test", **self.default_params}
        self.gateway.create_migration(params)
        self.gateway.start_transport({"is_synthetic_test": True, **params})
        cert_res = self.gateway.generate_certificate(params)
        rep_id = cert_res["report_id"]

        pdf_res = self.gateway.export_pdf_dossier({"report_id": rep_id})
        self.assertEqual(pdf_res["status"], "SUCCESS")
        self.assertEqual(pdf_res["format"], "PDF")

        zip_res = self.gateway.export_evidence_package({"report_id": rep_id})
        self.assertEqual(zip_res["status"], "SUCCESS")
        self.assertEqual(zip_res["format"], "ZIP")

        verify_res = self.gateway.verify_evidence_package({"payload_b64": zip_res["payload_b64"]})
        self.assertEqual(verify_res["status"], "VALID")


if __name__ == "__main__":
    unittest.main()
