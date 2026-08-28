"""
AKAAL Unit Tests — Super Engine Facade & Immutable Plan Authority (Step 3 Rectification)
==========================================================================================
Tests AkaalSuperEngine bootstrap, EnterpriseGovernancePlatformV6 single approval authority (S3-H7),
real approval path fingerprint persistence (S3-H8), connection identity binding (S3-H9),
post-approval mutation invalidation, and physical execution contract enforcement (H1 & H5).
"""

import os
from typing import Any, Dict, List, Optional
import unittest
from unittest.mock import MagicMock

from akaal.engine.facade import (
    AkaalSuperEngine,
    ApprovalRequiredError,
    PlanFingerprintMissingError,
    PlanFingerprintMismatchError,
    PhysicalExecutionContractError,
    PhysicalValidationContractError,
)
from akaal.governance.facade.platform6 import EnterpriseGovernancePlatformV6
from akaal.core.state.state_store import CentralStateStore


class TestSuperEngineFacade(unittest.TestCase):

    def setUp(self):
        self.workflow_id = "mig-super-engine-test-01"
        self.governance_platform = EnterpriseGovernancePlatformV6()
        self.engine = AkaalSuperEngine()

        # Clear state
        self.engine.state_store.set_state(f"{self.workflow_id}_approval", None, category="governance")
        self.engine.state_store.set_state(f"{self.workflow_id}_status", None, category="runtime")

        self.sample_spec = {
            "migration_id": self.workflow_id,
            "migration_name": "Oracle to PG Migration",
            "selected_scope": {"objects": [{"object_name": "USERS", "schema_name": "SYSTEM"}]},
            "tuning_policy": {"parallelism": 4, "batch_size": 10000},
            "validation_policy": {"level": "CHECKSUM"},
            "source_authority": {
                "system_type": "ORACLE",
                "host": "oracle-prod.internal",
                "port": 1521,
                "database": "FREE",
                "username": "SYSTEM",
                "credentials_ref": "vault:oracle/prod",
                "password": "secret_password_1",
            },
            "target_authority": {
                "system_type": "POSTGRESQL",
                "host": "pg-prod.internal",
                "port": 5432,
                "database": "pg_analytics",
                "username": "postgres",
                "credentials_ref": "vault:pg/prod",
                "password": "secret_password_2",
            },
            "physical_spec": {"selected_scope": {"objects": [{"object_name": "USERS"}]}},
            "physical_validation_context": {"source_rows": [(1, "A")], "target_rows": [(1, "A")]},
        }
        self.sample_dag = {"phases": [{"phase": "schema"}, {"phase": "transport"}]}

    def test_01_super_engine_boots_canonical_composition_root(self):
        self.assertIsNotNone(self.engine.context)
        self.assertIsNotNone(self.engine.context.workflow_engine)

    def test_02_same_execution_artifact_same_fingerprint(self):
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        self.assertEqual(fp1, fp2)

    def test_03_different_selected_scope_different_fingerprint(self):
        spec2 = json_copy(self.sample_spec)
        spec2["selected_scope"] = {"objects": [{"object_name": "ORDERS"}]}
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(spec2, self.sample_dag)
        self.assertNotEqual(fp1, fp2)

    def test_04_different_dag_different_fingerprint(self):
        dag2 = {"phases": [{"phase": "schema"}]}
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, dag2)
        self.assertNotEqual(fp1, fp2)

    def test_05_different_parallelism_different_fingerprint(self):
        spec2 = json_copy(self.sample_spec)
        spec2["tuning_policy"]["parallelism"] = 8
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(spec2, self.sample_dag)
        self.assertNotEqual(fp1, fp2)

    def test_06_different_batch_size_different_fingerprint(self):
        spec2 = json_copy(self.sample_spec)
        spec2["tuning_policy"]["batch_size"] = 50000
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(spec2, self.sample_dag)
        self.assertNotEqual(fp1, fp2)

    def test_07_different_validation_policy_different_fingerprint(self):
        spec2 = json_copy(self.sample_spec)
        spec2["validation_policy"]["level"] = "NONE"
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(spec2, self.sample_dag)
        self.assertNotEqual(fp1, fp2)

    def test_08_secret_password_changes_do_not_enter_fingerprint(self):
        # S3-H9: Password material MUST be excluded
        spec2 = json_copy(self.sample_spec)
        spec2["source_authority"]["password"] = "completely_different_secret_password"
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(spec2, self.sample_dag)
        self.assertEqual(fp1, fp2)

    def test_09_different_source_connection_identity_changes_fingerprint(self):
        # S3-H9: Stable connection identity MUST be fingerprinted
        spec2 = json_copy(self.sample_spec)
        spec2["source_authority"]["host"] = "oracle-disaster-recovery.internal"
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(spec2, self.sample_dag)
        self.assertNotEqual(fp1, fp2)

    def test_10_different_target_connection_identity_changes_fingerprint(self):
        # S3-H9: Target connection identity changes fingerprint
        spec2 = json_copy(self.sample_spec)
        spec2["target_authority"]["database"] = "pg_dw"
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(spec2, self.sample_dag)
        self.assertNotEqual(fp1, fp2)

    def test_11_governance_v6_real_approval_path_persists_fingerprint(self):
        # S3-H7 & S3-H8: Real Governance V6 approval authority persists fingerprint
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        rec = self.governance_platform.approve_migration_with_fingerprint(self.workflow_id, fp)

        self.assertEqual(rec["status"], "approved")
        self.assertEqual(rec["approved_plan_fingerprint"], fp)

        # SuperEngine reads and verifies this real governance approval record
        verified_fp = self.engine.verify_governance_authorization(self.workflow_id, self.sample_spec, self.sample_dag)
        self.assertEqual(fp, verified_fp)

    def test_12_legacy_approved_record_without_fingerprint_fails_closed(self):
        # S3-H8: Legacy approval records without fingerprint fail closed
        self.engine.state_store.set_state(
            f"{self.workflow_id}_approval",
            {"status": "approved"},  # Legacy record missing approved_plan_fingerprint
            category="governance",
        )
        with self.assertRaises(PlanFingerprintMissingError):
            self.engine.verify_governance_authorization(self.workflow_id, self.sample_spec, self.sample_dag)

    def test_13_post_approval_connection_identity_change_rejected(self):
        # S3-H9: Post-approval connection identity mutation rejects execution
        fp = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        self.governance_platform.approve_migration_with_fingerprint(self.workflow_id, fp)

        mutated_spec = json_copy(self.sample_spec)
        mutated_spec["source_authority"]["username"] = "UNAUTHORIZED_USER"

        with self.assertRaises(PlanFingerprintMismatchError):
            self.engine.verify_governance_authorization(self.workflow_id, mutated_spec, self.sample_dag)

    def test_14_physical_migration_without_physical_spec_fails_closed(self):
        # H1
        spec_no_physical = json_copy(self.sample_spec)
        del spec_no_physical["physical_spec"]

        with self.assertRaises(PhysicalExecutionContractError):
            self.engine.validate_execution_contracts(spec_no_physical, is_physical=True)

    def test_15_physical_validation_required_without_context_fails_closed(self):
        # H5
        spec_no_val_ctx = json_copy(self.sample_spec)
        del spec_no_val_ctx["physical_validation_context"]

        with self.assertRaises(PhysicalValidationContractError):
            self.engine.validate_execution_contracts(spec_no_val_ctx, is_physical=True)

    def test_16_explicit_synthetic_unit_test_mode_functional(self):
        spec_no_physical = json_copy(self.sample_spec)
        del spec_no_physical["physical_spec"]

        # Should not raise when synthetic test mode is True
        self.engine.validate_execution_contracts(spec_no_physical, is_physical=True, is_synthetic_test=True)


def json_copy(d: Dict[str, Any]) -> Dict[str, Any]:
    import json
    return json.loads(json.dumps(d))


if __name__ == "__main__":
    unittest.main()
