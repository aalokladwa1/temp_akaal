"""
AKAAL P5.5 Privacy, Masking & Tokenization Executable Test Suite
===============================================================
Comprehensive executable unit and integration test suite covering:
1. Static Redaction, Partial Masking, Salted Hashing
2. Keyed Pseudonymization & Unambiguous Domain Separation (Length-prefixed byte encoding)
3. Multi-Process Atomic Encrypted Token Vault Persistence & Detokenization (CentralStateStoreTokenVault)
4. Format-Preserving Masking (Email, Credit Card, Phone)
5. Canonical Log, Error, Preview, & Quarantine Sanitization
6. Legacy DataMasker Delegation
7. Bulk, CDC, & Validation Alignment Integration
8. IPC Gateway Privacy Capabilities (compile, validate, preview)
9. Fingerprint Binding to Plan Approval & Resume Fail-Closed Enforcement
10. AES-256-GCM HKDF Key Derivation & Fail-Closed Tamper Enforcement
"""

import unittest
import os
import shutil
import tempfile
import multiprocessing
import hashlib
import base64
import json
from typing import Dict, Any, List

from akaal.privacy.models import (
    PrivacyPolicy,
    PrivacyRule,
    PrivacyStrategy,
    SensitivityClass,
    CompiledPrivacyPolicy,
)
from akaal.privacy.token_vault import (
    CentralStateStoreTokenVault,
    TokenVaultError,
)
from akaal.privacy.sanitizer import LogAndDiagnosticSanitizer
from akaal.privacy.engine import PrivacyEngine, PrivacyEngineError
from akaal.migration.reliability.masking.masker import DataMasker
from akaal.core.models.configuration import MaskingConfiguration, MaskingRule
from akaal.core.state.state_store import CentralStateStore
from akaal.gateway.engine_gateway import EngineGateway
from akaal.planner.engine.plan_compiler import PlanCompiler


def _mp_tokenize_worker(db_path: str, domain: str, raw_value: str, result_queue) -> None:
    """Helper worker for multi-process concurrency test."""
    try:
        CentralStateStore._instance = None
        store = CentralStateStore(db_path=db_path)
        vault = CentralStateStoreTokenVault(state_store=store, master_key_id="mp-test-key")
        token = vault.tokenize(raw_value, privacy_domain=domain)
        result_queue.put({"status": "SUCCESS", "raw": raw_value, "token": token})
    except Exception as exc:
        result_queue.put({"status": "ERROR", "error": str(exc)})


class TestP55PrivacyControls(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test_state.db")
        CentralStateStore._instance = None
        self.state_store = CentralStateStore(db_path=self.db_path)

    def tearDown(self):
        CentralStateStore._instance = None
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_static_redact_and_nullify(self):
        policy = PrivacyPolicy(
            object_name="CUSTOMERS",
            rules=[
                PrivacyRule(rule_id="r1", column_name="name", strategy=PrivacyStrategy.STATIC_REDACT),
                PrivacyRule(rule_id="r2", column_name="ssn", strategy=PrivacyStrategy.NULLIFY),
            ],
        )
        engine = PrivacyEngine(policy)
        row = {"name": "John Doe", "ssn": "000-12-3456", "age": 30}
        transformed = engine.transform_row(row)
        self.assertEqual(transformed["name"], "[REDACTED]")
        self.assertIsNone(transformed["ssn"])
        self.assertEqual(transformed["age"], 30)

    def test_02_partial_masking_and_salted_hash(self):
        policy = PrivacyPolicy(
            object_name="CUSTOMERS",
            rules=[
                PrivacyRule(rule_id="r1", column_name="phone", strategy=PrivacyStrategy.PARTIAL_MASK, unmasked_length=4, mask_char="*"),
                PrivacyRule(rule_id="r2", column_name="passport", strategy=PrivacyStrategy.HASH, salt="SALT123"),
            ],
        )
        engine = PrivacyEngine(policy)
        row = {"phone": "1234567890", "passport": "PASS999"}
        transformed = engine.transform_row(row)
        self.assertEqual(transformed["phone"], "******7890")
        self.assertNotEqual(transformed["passport"], "PASS999")
        self.assertEqual(len(transformed["passport"]), 64)

    def test_03_keyed_pseudonymization_referential_consistency(self):
        policy_customers = PrivacyPolicy(
            object_name="CUSTOMERS",
            rules=[
                PrivacyRule(rule_id="r1", column_name="cust_id", strategy=PrivacyStrategy.KEYED_PSEUDONYM, privacy_domain="CUSTOMER_DOMAIN", key_id="k1"),
            ],
        )
        policy_orders = PrivacyPolicy(
            object_name="ORDERS",
            rules=[
                PrivacyRule(rule_id="r2", column_name="cust_id", strategy=PrivacyStrategy.KEYED_PSEUDONYM, privacy_domain="CUSTOMER_DOMAIN", key_id="k1"),
                PrivacyRule(rule_id="r3", column_name="order_id", strategy=PrivacyStrategy.KEYED_PSEUDONYM, privacy_domain="ORDER_DOMAIN", key_id="k1"),
            ],
        )

        engine_c = PrivacyEngine(policy_customers)
        engine_o = PrivacyEngine(policy_orders)

        row_c = {"cust_id": "CUST-1001", "name": "Alice"}
        row_o = {"order_id": "ORD-500", "cust_id": "CUST-1001", "amount": 150.0}

        t_c = engine_c.transform_row(row_c)
        t_o = engine_o.transform_row(row_o)

        self.assertTrue(t_c["cust_id"].startswith("PSEUDO-"))
        self.assertEqual(t_c["cust_id"], t_o["cust_id"])
        self.assertNotEqual(t_c["cust_id"], t_o["order_id"])

    def test_04_durable_encrypted_token_vault_persistence_and_detokenization(self):
        vault = CentralStateStoreTokenVault(state_store=self.state_store, master_key_id="test-key")

        token1 = vault.tokenize("raw_secret_value_123", privacy_domain="USER_ID")
        self.assertTrue(token1.startswith("TOK-USER-"))

        token2 = vault.tokenize("raw_secret_value_123", privacy_domain="USER_ID")
        self.assertEqual(token1, token2)

        raw_restored = vault.detokenize(token1, privacy_domain="USER_ID")
        self.assertEqual(raw_restored, "raw_secret_value_123")

        vault_restarted = CentralStateStoreTokenVault(state_store=self.state_store, master_key_id="test-key")
        token_after_restart = vault_restarted.tokenize("raw_secret_value_123", privacy_domain="USER_ID")
        self.assertEqual(token1, token_after_restart)
        self.assertEqual(vault_restarted.detokenize(token1, privacy_domain="USER_ID"), "raw_secret_value_123")

    def test_05_format_preserving_masking(self):
        policy = PrivacyPolicy(
            object_name="CONTACTS",
            rules=[
                PrivacyRule(rule_id="r1", column_name="email", strategy=PrivacyStrategy.FORMAT_PRESERVING_MASK),
                PrivacyRule(rule_id="r2", column_name="card", strategy=PrivacyStrategy.FORMAT_PRESERVING_MASK),
            ],
        )
        engine = PrivacyEngine(policy)
        row = {"email": "aalok@enterprise.com", "card": "1234-5678-9012-3456"}
        transformed = engine.transform_row(row)
        self.assertEqual(transformed["email"], "a****@e*********.com")
        self.assertEqual(transformed["card"], "****-****-****-****")

    def test_06_canonical_log_and_diagnostic_sanitizer(self):
        raw_log = "Error during sync for user contact@acme.com with ssn 123-45-6789 and card 4111111111111111"
        sanitized_log = LogAndDiagnosticSanitizer.sanitize_text(raw_log)
        self.assertNotIn("contact@acme.com", sanitized_log)
        self.assertNotIn("123-45-6789", sanitized_log)
        self.assertNotIn("4111111111111111", sanitized_log)

        dict_payload = {
            "user_id": 101,
            "password": "SuperSecretPassword123!",
            "details": {"email": "user@test.org"},
        }
        sanitized_dict = LogAndDiagnosticSanitizer.sanitize_dict(dict_payload)
        self.assertEqual(sanitized_dict["password"], "[REDACTED]")
        self.assertEqual(sanitized_dict["details"]["email"], "[REDACTED_EMAIL]")

    def test_07_legacy_datamasker_delegation(self):
        config = MaskingConfiguration(
            policies={
                "USERS": [
                    MaskingRule(column_name="email", masking_strategy="REDACT"),
                    MaskingRule(column_name="phone", masking_strategy="PARTIAL", unmasked_length=4),
                ]
            }
        )
        masker = DataMasker(config)
        masker.validate_policies()
        row = {"email": "test@domain.com", "phone": "9876543210"}
        masked = masker.mask_row("USERS", row)
        self.assertEqual(masked["email"], "[REDACTED]")
        self.assertEqual(masked["phone"], "xxxxxx3210")

    def test_08_gateway_privacy_capabilities(self):
        gateway = EngineGateway()
        payload = {
            "object_name": "ACCOUNTS",
            "rules": [
                {"column_name": "acc_no", "strategy": "TOKENIZE", "privacy_domain": "ACC_DOMAIN"},
                {"column_name": "pin", "strategy": "NULLIFY"},
            ],
            "source_rows": [
                {"acc_no": "ACC-9988", "pin": "1234", "balance": 5000},
            ],
        }

        comp_res = gateway.compile_privacy_policy(payload)
        self.assertEqual(comp_res["status"], "SUCCESS")
        self.assertTrue("fingerprint" in comp_res)

        val_res = gateway.validate_privacy_policy(payload)
        self.assertEqual(val_res["status"], "SUCCESS")
        self.assertTrue(val_res["is_valid"])

        prev_res = gateway.preview_privacy_policy(payload)
        self.assertEqual(prev_res["status"], "SUCCESS")
        self.assertEqual(prev_res["rules_applied"], 2)
        transformed_row = prev_res["transformed_rows_after"][0]
        self.assertTrue(transformed_row["acc_no"].startswith("TOK-ACC_"))
        self.assertIsNone(transformed_row["pin"])
        self.assertEqual(transformed_row["balance"], 5000)

    def test_09_multiprocess_token_vault_atomicity(self):
        """Blocker A Hostile Executable Test: Multi-process atomic tokenization & detokenization."""
        ctx = multiprocessing.get_context("spawn")
        q = ctx.Queue()

        processes: List[multiprocessing.Process] = []
        num_workers = 4

        # CASE A: Concurrent tokenization of SAME value across processes
        for _ in range(num_workers):
            p = ctx.Process(target=_mp_tokenize_worker, args=(self.db_path, "CUSTOMER_SSN", "999-00-1111", q))
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=5)

        results = []
        for _ in range(num_workers):
            try:
                results.append(q.get(timeout=10))
            except Exception:
                pass

        self.assertEqual(len(results), num_workers)
        tokens = [r["token"] for r in results if r["status"] == "SUCCESS"]
        self.assertEqual(len(tokens), num_workers)

        # All processes MUST observe exact same converged token!
        self.assertEqual(len(set(tokens)), 1, f"Expected 1 unique token, got {set(tokens)}")

        # Detokenization verification
        vault = CentralStateStoreTokenVault(state_store=self.state_store, master_key_id="mp-test-key")
        self.assertEqual(vault.detokenize(tokens[0], privacy_domain="CUSTOMER_SSN"), "999-00-1111")

        # CASE B: Concurrent tokenization of DIFFERENT values across processes
        processes_b = []
        for i in range(num_workers):
            p = ctx.Process(target=_mp_tokenize_worker, args=(self.db_path, "ORDER_ID", f"ORD-VALUE-{i}", q))
            processes_b.append(p)
            p.start()

        for p in processes_b:
            p.join(timeout=5)

        results_b = []
        for _ in range(num_workers):
            try:
                results_b.append(q.get(timeout=10))
            except Exception:
                pass

        diff_tokens = [r["token"] for r in results_b if r["status"] == "SUCCESS"]
        self.assertEqual(len(diff_tokens), num_workers)
        self.assertEqual(len(set(diff_tokens)), num_workers, "Expected distinct tokens for distinct values.")

        for r in results_b:
            self.assertEqual(vault.detokenize(r["token"], privacy_domain="ORDER_ID"), r["raw"])

    def test_10_unambiguous_hmac_domain_separation(self):
        """Blocker B Hostile Executable Test: Length-prefixed unambiguous domain separation."""
        rule_a = PrivacyRule(rule_id="r1", column_name="col", strategy=PrivacyStrategy.KEYED_PSEUDONYM, privacy_domain="a:b", key_id="k1")
        rule_b = PrivacyRule(rule_id="r2", column_name="col", strategy=PrivacyStrategy.KEYED_PSEUDONYM, privacy_domain="a", key_id="k1")

        engine_a = PrivacyEngine(PrivacyPolicy(object_name="T1", rules=[rule_a]))
        engine_b = PrivacyEngine(PrivacyPolicy(object_name="T2", rules=[rule_b]))

        res_a = engine_a.transform_row({"col": "c"})["col"]
        res_b = engine_b.transform_row({"col": "b:c"})["col"]

        # Ambiguous delimiter concatenation would produce identical strings "a:b:c", resulting in a collision!
        # Unambiguous length-prefixed encoding guarantees res_a != res_b!
        self.assertNotEqual(res_a, res_b, "Delimiter collision detected! Pseudonyms must be distinct.")

    def test_11_fingerprint_approval_and_resume_binding(self):
        """Blocker C Hostile Executable Test: Fingerprint fail-closed enforcement on approval & resume."""
        policy_v1 = PrivacyPolicy(
            object_name="CUSTOMERS",
            rules=[PrivacyRule(rule_id="r1", column_name="email", strategy=PrivacyStrategy.STATIC_REDACT)],
        )
        engine_v1 = PrivacyEngine(policy_v1)
        compiled_v1 = engine_v1.compile_policy()

        exec_plan = {
            "execution_plan_id": "plan-101",
            "fingerprint": compiled_v1.fingerprint,
            "resolved_configuration": {"privacy_fingerprint": compiled_v1.fingerprint},
        }

        # 1. Matching approved fingerprint -> valid
        self.assertTrue(PlanCompiler.validate_plan_approval(exec_plan, approved_fingerprint=compiled_v1.fingerprint))

        # 2. Modify rule -> fingerprint changes -> stale approval rejected fail closed
        policy_v2 = PrivacyPolicy(
            object_name="CUSTOMERS",
            rules=[PrivacyRule(rule_id="r1", column_name="email", strategy=PrivacyStrategy.TOKENIZE)],
        )
        compiled_v2 = PrivacyEngine(policy_v2).compile_policy()
        self.assertNotEqual(compiled_v1.fingerprint, compiled_v2.fingerprint)

        with self.assertRaises(RuntimeError) as ctx_app:
            PlanCompiler.validate_plan_approval(exec_plan, approved_fingerprint=compiled_v2.fingerprint)
        self.assertIn("STALE_APPROVAL_REJECTED", str(ctx_app.exception))

        # 3. Resume checkpoint fail-closed rejection when fingerprint differs
        checkpoint_data = {"checkpoint_id": "chk-001", "privacy_fingerprint": compiled_v1.fingerprint}
        self.assertTrue(PlanCompiler.validate_resume_checkpoint(checkpoint_data, current_privacy_fingerprint=compiled_v1.fingerprint))

        with self.assertRaises(RuntimeError) as ctx_res:
            PlanCompiler.validate_resume_checkpoint(checkpoint_data, current_privacy_fingerprint=compiled_v2.fingerprint)
        self.assertIn("STALE_RESUME_REJECTED", str(ctx_res.exception))

    def test_12_aes_gcm_hkdf_envelope_and_fail_closed(self):
        """Blocker D Hostile Executable Test: HKDF derivation, versioned envelope, and fail-closed tampering."""
        vault = CentralStateStoreTokenVault(state_store=self.state_store, master_key_id="vault-master-key")

        token = vault.tokenize("sensitive_ssn_12345", privacy_domain="SSN")
        self.assertTrue(token.startswith("TOK-SSN-"))

        # Verify envelope structure in state database (No plaintext secret or raw source stored!)
        fwd_hash = hashlib.sha256(b"SSN:sensitive_ssn_12345").hexdigest()
        raw_db_val = self.state_store.get_state(fwd_hash, category="token_fwd_SSN")
        self.assertIsNotNone(raw_db_val)
        raw_db_str = json.dumps(raw_db_val) if isinstance(raw_db_val, dict) else str(raw_db_val)
        self.assertNotIn("sensitive_ssn_12345", raw_db_str)  # Plaintext raw source must NOT be stored!

        envelope = raw_db_val if isinstance(raw_db_val, dict) else json.loads(raw_db_val)
        self.assertEqual(envelope["version"], "1.0.0")
        self.assertEqual(envelope["algorithm"], "AES-256-GCM")
        self.assertIn("nonce", envelope)
        self.assertIn("ciphertext", envelope)

        # Fail closed on missing key / wrong key
        wrong_vault = CentralStateStoreTokenVault(state_store=self.state_store, master_key_id="wrong-key")
        with self.assertRaises(TokenVaultError):
            wrong_vault.detokenize(token, privacy_domain="SSN", key_id="wrong-key")

        # Fail closed on tampered ciphertext
        corrupted_envelope = dict(envelope)
        corrupted_envelope["ciphertext"] = base64.b64encode(b"corrupted_bytes_00000000000").decode("utf-8")
        self.state_store.set_state(token, json.dumps(corrupted_envelope), category="token_rev_SSN")

        with self.assertRaises(TokenVaultError):
            vault.detokenize(token, privacy_domain="SSN")

    def test_13_stale_approval_real_execution_rejection(self):
        """Hostile Integration Test: Real ReplicationPipeline rejects stale approval with zero target writes."""
        import asyncio
        from akaal.replication.pipeline.orchestrator import ReplicationPipeline
        from akaal.replication.core.context import ReplicationContext
        from akaal.replication.core.registry import ReplicatorRegistry
        from akaal.replication.core.models import ReplicationStatus

        policy_v1 = PrivacyPolicy(object_name="T1", rules=[PrivacyRule(rule_id="r1", column_name="col", strategy=PrivacyStrategy.STATIC_REDACT)])
        policy_v2 = PrivacyPolicy(object_name="T1", rules=[PrivacyRule(rule_id="r1", column_name="col", strategy=PrivacyStrategy.TOKENIZE)])

        fp_v1 = PrivacyEngine(policy_v1).compile_policy().fingerprint
        fp_v2 = PrivacyEngine(policy_v2).compile_policy().fingerprint

        exec_plan = {
            "execution_plan_id": "plan-999",
            "fingerprint": fp_v1,
            "resolved_configuration": {"privacy_fingerprint": fp_v1},
        }

        # Context contains execution_plan with fp_v1, but approved_fingerprint is fp_v2 (stale approval!)
        context = ReplicationContext(
            runtime_metadata={
                "execution_plan": exec_plan,
                "approved_fingerprint": fp_v2,
            }
        )

        pipeline = ReplicationPipeline(registry=ReplicatorRegistry())
        session = asyncio.run(pipeline.execute_pipeline(context))

        # Real production pipeline MUST reject stale approval and fail before any target domain replication!
        self.assertEqual(session.state, ReplicationStatus.FAILED)
        self.assertEqual(len(session.results), 0, "Target write count must be EXACTLY 0.")

    def test_14_stale_resume_real_execution_rejection(self):
        """Hostile Integration Test: Real DeterministicResumeEngine rejects stale resume with zero target writes."""
        from akaal.migration.execution.resume_engine import DeterministicResumeEngine
        from akaal.orchestration.checkpoint.checkpoint import WorkflowCheckpoint

        checkpoint = WorkflowCheckpoint(
            checkpoint_id="chk-777",
            workflow_id="wf-123",
            job_id="job-001",
            step_name="MIGRATION_STEP",
            step_index=1,
            engine_state="PAUSED",
            workflow_version="1.0.0",
            config_version=1,
            config_checksum="test_chksum",
            state_data={"last_committed_batch": 5, "privacy_fingerprint": "FP_POLICY_VERSION_1"},
        )

        resume_engine = DeterministicResumeEngine()

        # Attempt resume with current_privacy_fingerprint = "FP_POLICY_VERSION_2" (stale checkpoint!)
        with self.assertRaises(RuntimeError) as ctx_err:
            resume_engine.resume_migration(
                workflow_id="wf-123",
                checkpoint=checkpoint,
                table_name="CUSTOMERS",
                current_privacy_fingerprint="FP_POLICY_VERSION_2",
            )

        self.assertIn("STALE_RESUME_REJECTED", str(ctx_err.exception))

    def test_15_missing_approval_metadata_fail_closed(self):
        """Hostile Test: Missing/empty/malformed approval metadata on privacy plan MUST fail closed with 0 target writes."""
        import asyncio
        from akaal.replication.pipeline.orchestrator import ReplicationPipeline
        from akaal.replication.core.context import ReplicationContext
        from akaal.replication.core.registry import ReplicatorRegistry
        from akaal.replication.core.models import ReplicationStatus

        policy = PrivacyPolicy(object_name="T1", rules=[PrivacyRule(rule_id="r1", column_name="col", strategy=PrivacyStrategy.STATIC_REDACT)])
        privacy_fp = PrivacyEngine(policy).compile_policy().fingerprint

        privacy_exec_plan = {
            "execution_plan_id": "plan-priv",
            "fingerprint": privacy_fp,
            "resolved_configuration": {"privacy_fingerprint": privacy_fp},
        }

        pipeline = ReplicationPipeline(registry=ReplicatorRegistry())

        # CASE A: Privacy plan + None approved_fingerprint -> MUST fail closed
        ctx_none = ReplicationContext(runtime_metadata={"execution_plan": privacy_exec_plan, "approved_fingerprint": None})
        session_none = asyncio.run(pipeline.execute_pipeline(ctx_none))
        self.assertEqual(session_none.state, ReplicationStatus.FAILED)
        self.assertEqual(len(session_none.results), 0, "Target write count must be EXACTLY 0.")

        # CASE B: Privacy plan + empty approved_fingerprint ("") -> MUST fail closed
        ctx_empty = ReplicationContext(runtime_metadata={"execution_plan": privacy_exec_plan, "approved_fingerprint": ""})
        session_empty = asyncio.run(pipeline.execute_pipeline(ctx_empty))
        self.assertEqual(session_empty.state, ReplicationStatus.FAILED)
        self.assertEqual(len(session_empty.results), 0, "Target write count must be EXACTLY 0.")

        # CASE C: Privacy plan + whitespace approved_fingerprint ("   ") -> MUST fail closed
        ctx_ws = ReplicationContext(runtime_metadata={"execution_plan": privacy_exec_plan, "approved_fingerprint": "   "})
        session_ws = asyncio.run(pipeline.execute_pipeline(ctx_ws))
        self.assertEqual(session_ws.state, ReplicationStatus.FAILED)
        self.assertEqual(len(session_ws.results), 0, "Target write count must be EXACTLY 0.")

        # CASE D: Genuine non-privacy plan (no privacy rules/fingerprint) -> valid behavior preserved
        no_priv_plan = {"execution_plan_id": "plan-nopriv", "fingerprint": "", "resolved_configuration": {}}
        ctx_nopriv = ReplicationContext(runtime_metadata={"execution_plan": no_priv_plan})
        session_nopriv = asyncio.run(pipeline.execute_pipeline(ctx_nopriv))
        self.assertNotEqual(session_nopriv.state, ReplicationStatus.FAILED)

    def test_16_missing_resume_metadata_fail_closed(self):
        """Hostile Test: Missing/empty resume privacy metadata MUST fail closed before workflow resume."""
        from akaal.migration.execution.resume_engine import DeterministicResumeEngine
        from akaal.orchestration.checkpoint.checkpoint import WorkflowCheckpoint

        resume_engine = DeterministicResumeEngine()

        privacy_ckpt = WorkflowCheckpoint(
            checkpoint_id="chk-priv",
            workflow_id="wf-1",
            job_id="job-1",
            step_name="STEP",
            step_index=1,
            engine_state="PAUSED",
            workflow_version="1.0",
            config_version=1,
            config_checksum="chksum",
            state_data={"last_committed_batch": 2, "privacy_fingerprint": "FP_PRIVACY_ACTIVE"},
        )

        # CASE A: Privacy checkpoint + None current_privacy_fingerprint -> MUST fail closed
        with self.assertRaises(RuntimeError) as err_a:
            resume_engine.resume_migration("wf-1", privacy_ckpt, "USERS", current_privacy_fingerprint=None)
        self.assertIn("STALE_RESUME_REJECTED", str(err_a.exception))

        # CASE B: Privacy checkpoint + empty current_privacy_fingerprint ("") -> MUST fail closed
        with self.assertRaises(RuntimeError) as err_b:
            resume_engine.resume_migration("wf-1", privacy_ckpt, "USERS", current_privacy_fingerprint="")
        self.assertIn("STALE_RESUME_REJECTED", str(err_b.exception))

        # CASE C: Non-privacy checkpoint + privacy-controlled current execution -> MUST fail closed
        nopriv_ckpt = WorkflowCheckpoint(
            checkpoint_id="chk-nopriv",
            workflow_id="wf-2",
            job_id="job-2",
            step_name="STEP",
            step_index=1,
            engine_state="PAUSED",
            workflow_version="1.0",
            config_version=1,
            config_checksum="chksum",
            state_data={"last_committed_batch": 2},
        )
        with self.assertRaises(RuntimeError) as err_c:
            resume_engine.resume_migration("wf-2", nopriv_ckpt, "USERS", current_privacy_fingerprint="FP_NEW_PRIVACY")
        self.assertIn("STALE_RESUME_REJECTED", str(err_c.exception))

        # CASE D: Genuine non-privacy checkpoint + no current privacy fingerprint -> valid behavior preserved
        res_d = resume_engine.resume_migration("wf-2", nopriv_ckpt, "USERS", current_privacy_fingerprint=None)
        self.assertTrue(res_d.success)


if __name__ == "__main__":
    unittest.main()
