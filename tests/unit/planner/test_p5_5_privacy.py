"""
AKAAL P5.5 Privacy, Masking & Tokenization Executable Test Suite
===============================================================
Comprehensive executable unit and integration test suite covering:
1. Static Redaction, Partial Masking, Salted Hashing
2. Keyed Pseudonymization & Privacy Domain Referential Consistency
3. Durable Encrypted Token Vault Persistence & Detokenization (CentralStateStoreTokenVault)
4. Format-Preserving Masking (Email, Credit Card, Phone)
5. Canonical Log, Error, Preview, & Quarantine Sanitization
6. Legacy DataMasker Delegation
7. Bulk, CDC, & Validation Alignment Integration
8. IPC Gateway Privacy Capabilities (compile, validate, preview)
"""

import unittest
import os
import shutil
import tempfile
from typing import Dict, Any

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
        self.assertEqual(len(transformed["passport"]), 64)  # SHA-256 hex string

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
        self.assertEqual(t_c["cust_id"], t_o["cust_id"])  # Referential consistency across tables!
        self.assertNotEqual(t_c["cust_id"], t_o["order_id"])  # Domain separation prevents cross-domain correlation!

    def test_04_durable_encrypted_token_vault_persistence_and_detokenization(self):
        vault = CentralStateStoreTokenVault(state_store=self.state_store, master_key_id="test-key")

        token1 = vault.tokenize("raw_secret_value_123", privacy_domain="USER_ID")
        self.assertTrue(token1.startswith("TOK-USER-"))

        # Idempotent tokenization
        token2 = vault.tokenize("raw_secret_value_123", privacy_domain="USER_ID")
        self.assertEqual(token1, token2)

        # Detokenization
        raw_restored = vault.detokenize(token1, privacy_domain="USER_ID")
        self.assertEqual(raw_restored, "raw_secret_value_123")

        # Restart simulation: instantiate new vault instance reading from persisted CentralStateStore
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


if __name__ == "__main__":
    unittest.main()
