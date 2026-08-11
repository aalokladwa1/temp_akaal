"""
AKAAL Unit Tests — Super Engine Facade & Immutable Plan Authority (Step 3 Verification)
========================================================================================
Tests AkaalSuperEngine bootstrap, SHA-256 plan fingerprinting, governance approval gates,
post-approval mutation invalidation, and physical execution contract enforcement (H1 & H5).
"""

import os
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
from akaal.core.state.state_store import CentralStateStore


class TestSuperEngineFacade(unittest.TestCase):

    def setUp(self):
        self.state_store = CentralStateStore()
        self.workflow_id = "mig-super-engine-test-01"
        self.state_store.set_state(f"{self.workflow_id}_approval", None, category="governance")
        self.state_store.set_state(f"{self.workflow_id}_status", None, category="runtime")

        self.sample_spec = {
            "migration_id": self.workflow_id,
            "migration_name": "Oracle to PG Migration",
            "selected_scope": {"objects": [{"object_name": "USERS", "schema_name": "SYSTEM"}]},
            "tuning_policy": {"parallelism": 4, "batch_size": 10000},
            "validation_policy": {"level": "CHECKSUM"},
            "source_authority": {"host": "127.0.0.1", "port": 1521, "password": "secret_password"},
            "target_authority": {"host": "127.0.0.1", "port": 5432, "password": "secret_password"},
            "physical_spec": {"selected_scope": {"objects": [{"object_name": "USERS"}]}},
            "physical_validation_context": {"source_rows": [(1, "A")], "target_rows": [(1, "A")]},
        }
        self.sample_dag = {"phases": [{"phase": "schema"}, {"phase": "transport"}]}

    def test_01_super_engine_boots_canonical_composition_root(self):
        engine = AkaalSuperEngine()
        self.assertIsNotNone(engine.context)
        self.assertIsNotNone(engine.context.workflow_engine)

    def test_02_same_execution_artifact_same_fingerprint(self):
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        self.assertEqual(fp1, fp2)

    def test_03_different_selected_scope_different_fingerprint(self):
        spec2 = dict(self.sample_spec)
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

    def test_08_different_cdc_policy_different_fingerprint(self):
        spec1 = json_copy(self.sample_spec)
        spec1["enable_cdc"] = False
        spec2 = json_copy(self.sample_spec)
        spec2["enable_cdc"] = True
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(spec1, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(spec2, self.sample_dag)
        self.assertNotEqual(fp1, fp2)

    def test_09_secret_password_changes_do_not_enter_fingerprint(self):
        spec2 = json_copy(self.sample_spec)
        spec2["source_authority"]["password"] = "completely_different_password"
        fp1 = AkaalSuperEngine.compute_plan_fingerprint(self.sample_spec, self.sample_dag)
        fp2 = AkaalSuperEngine.compute_plan_fingerprint(spec2, self.sample_dag)
        self.assertEqual(fp1, fp2)

    def test_10_missing_approval_rejected(self):
        engine = AkaalSuperEngine()
        with self.assertRaises(ApprovalRequiredError):
            engine.verify_governance_authorization(self.workflow_id, self.sample_spec, self.sample_dag)

    def test_11_denied_revoked_approval_rejected(self):
        engine = AkaalSuperEngine()
        engine.state_store.set_state(f"{self.workflow_id}_approval", {"status": "rejected"}, category="governance")
        with self.assertRaises(ApprovalRequiredError):
            engine.verify_governance_authorization(self.workflow_id, self.sample_spec, self.sample_dag)

    def test_12_missing_approved_fingerprint_rejected(self):
        engine = AkaalSuperEngine()
        engine.state_store.set_state(f"{self.workflow_id}_approval", {"status": "approved"}, category="governance")
        with self.assertRaises(PlanFingerprintMissingError):
            engine.verify_governance_authorization(self.workflow_id, self.sample_spec, self.sample_dag)

    def test_13_fingerprint_mismatch_rejected(self):
        engine = AkaalSuperEngine()
        engine.state_store.set_state(
            f"{self.workflow_id}_approval",
            {"status": "approved", "approved_plan_fingerprint": "wrong_fingerprint_123"},
            category="governance",
        )
        with self.assertRaises(PlanFingerprintMismatchError):
            engine.verify_governance_authorization(self.workflow_id, self.sample_spec, self.sample_dag)

    def test_14_matching_approved_fingerprint_authorization_succeeds(self):
        engine = AkaalSuperEngine()
        fp = engine.record_governance_approval(self.workflow_id, self.sample_spec, self.sample_dag)
        verified_fp = engine.verify_governance_authorization(self.workflow_id, self.sample_spec, self.sample_dag)
        self.assertEqual(fp, verified_fp)

    def test_15_post_approval_config_mutation_rejected(self):
        engine = AkaalSuperEngine()
        engine.record_governance_approval(self.workflow_id, self.sample_spec, self.sample_dag)

        mutated_spec = json_copy(self.sample_spec)
        mutated_spec["tuning_policy"]["parallelism"] = 16  # Mutated after approval

        with self.assertRaises(PlanFingerprintMismatchError):
            engine.verify_governance_authorization(self.workflow_id, mutated_spec, self.sample_dag)

    def test_16_post_approval_scope_mutation_rejected(self):
        engine = AkaalSuperEngine()
        engine.record_governance_approval(self.workflow_id, self.sample_spec, self.sample_dag)

        mutated_spec = json_copy(self.sample_spec)
        mutated_spec["selected_scope"]["objects"].append({"object_name": "PAYMENTS"})  # Mutated after approval

        with self.assertRaises(PlanFingerprintMismatchError):
            engine.verify_governance_authorization(self.workflow_id, mutated_spec, self.sample_dag)

    def test_17_physical_migration_without_physical_spec_fails_closed(self):
        engine = AkaalSuperEngine()
        spec_no_physical = json_copy(self.sample_spec)
        del spec_no_physical["physical_spec"]

        with self.assertRaises(PhysicalExecutionContractError):
            engine.validate_execution_contracts(spec_no_physical, is_physical=True)

    def test_18_physical_validation_required_without_context_fails_closed(self):
        engine = AkaalSuperEngine()
        spec_no_val_ctx = json_copy(self.sample_spec)
        del spec_no_val_ctx["physical_validation_context"]

        with self.assertRaises(PhysicalValidationContractError):
            engine.validate_execution_contracts(spec_no_val_ctx, is_physical=True)

    def test_19_explicit_synthetic_unit_test_mode_functional(self):
        engine = AkaalSuperEngine()
        spec_no_physical = json_copy(self.sample_spec)
        del spec_no_physical["physical_spec"]

        # Should not raise when synthetic test mode is True
        engine.validate_execution_contracts(spec_no_physical, is_physical=True, is_synthetic_test=True)


def json_copy(d: Dict[str, Any]) -> Dict[str, Any]:
    import json
    return json.loads(json.dumps(d))


if __name__ == "__main__":
    unittest.main()
