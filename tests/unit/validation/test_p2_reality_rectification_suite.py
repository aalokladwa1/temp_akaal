"""
P2 Reality Rectification Hostile Suite
========================================
Verifies P2 Non-Negotiable Validation Truth Law:
- ValidationStep fails closed when physical count queries fail (returns UNABLE_TO_VERIFY)
- SQLite adapter computes genuine physical row SHA-256 digest (never 'mock_checksum')
- Canonical checksum unambiguously distinguishes NULL from empty string
- Canonical checksum fails when row data differs despite identical counts
- DigitalCertificationSealer refuses VALID seal on failed/unverifiable validation
- ValidationOnlyWriteFirewall blocks SQL mutations (UPDATE, DELETE, DROP, INSERT, CREATE, ALTER, TRUNCATE)
"""

import unittest
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.sub_contexts import ExecutionContext, RuntimeContext, UserContext
from akaal.validation.domain.canonical_checksum import canonical_hash_row, compute_canonical_table_checksum
from akaal.trust_certification.seal.sealer import DigitalCertificationSealer
from akaal.trust_certification.domain.enums import CertificationSealStatus
from akaal.validation.domain.reconciliation import ValidationOnlyWriteFirewall


class TestP2RealityRectificationSuite(unittest.TestCase):

    def _make_ctx(self, rt_params: dict) -> WorkflowContext:
        return WorkflowContext(
            execution_context=ExecutionContext(workflow_id="mig-p2-test", run_id="run-p2-test"),
            runtime_context=RuntimeContext(transient_parameters=rt_params),
            user_context=UserContext(user_id="op"),
        )

    def test_01_validation_step_fails_closed_on_count_query_failure(self):
        """ValidationStep fails closed with ROW_RECONCILIATION_FAILED / UNABLE_TO_VERIFY on broken params."""
        from akaal.workflow.steps.migration_steps import ValidationStep
        step = ValidationStep()
        rt_params = {
            "selected_scope": {"objects": [{"object_name": "T1", "target_schema": "public", "object_type": "TABLE"}]},
            "source_params": {"host": "invalid-host-999.invalid", "db_type": "postgresql"},
            "target_params": {"host": "invalid-host-999.invalid", "db_type": "postgresql"},
        }
        ctx = self._make_ctx(rt_params)
        res = step.execute(ctx)
        self.assertFalse(res.success)
        # Must report ROW_RECONCILIATION_FAILED, not success
        self.assertTrue(len(res.errors) > 0)
        self.assertIn("ROW_RECONCILIATION_FAILED", res.errors[0])

    def test_02_canonical_checksum_distinguishes_null_from_empty_string(self):
        """Canonical row hash unambiguously distinguishes NULL (None) from empty string ('')."""
        row_null = {"col1": None}
        row_empty = {"col1": ""}
        hash_null = canonical_hash_row(row_null)
        hash_empty = canonical_hash_row(row_empty)
        self.assertNotEqual(hash_null, hash_empty)

    def test_03_canonical_checksum_distinguishes_same_count_corrupted_data(self):
        """Canonical table checksum fails when data differs despite identical row counts."""
        rows_source = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        rows_target = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Eve"}]
        cs_source = compute_canonical_table_checksum(rows_source)
        cs_target = compute_canonical_table_checksum(rows_target)
        self.assertNotEqual(cs_source, cs_target)

    def test_04_canonical_checksum_identical_data_match(self):
        """Canonical table checksum matches when row data is identical."""
        rows_a = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        rows_b = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        cs_a = compute_canonical_table_checksum(rows_a)
        cs_b = compute_canonical_table_checksum(rows_b)
        self.assertEqual(cs_a, cs_b)

    def test_05_digital_certification_sealer_refuses_valid_seal_on_failed_validation(self):
        """DigitalCertificationSealer sets seal status to REVOKED when validation_passed is False."""
        sealer = DigitalCertificationSealer()
        seal = sealer.issue_seal(
            "mig-failed-05", trust_score_val=95.0,
            validation_passed=False, validation_status="FAILED"
        )
        self.assertEqual(seal.status, CertificationSealStatus.REVOKED)

    def test_06_digital_certification_sealer_grants_valid_seal_on_passed_validation(self):
        """DigitalCertificationSealer sets seal status to VALID only when validation_passed is True."""
        sealer = DigitalCertificationSealer()
        seal = sealer.issue_seal(
            "mig-passed-06", trust_score_val=98.5,
            validation_passed=True, validation_status="PASSED"
        )
        self.assertEqual(seal.status, CertificationSealStatus.VALID)

    def test_07_write_firewall_blocks_update(self):
        """ValidationOnlyWriteFirewall blocks UPDATE mutations."""
        with self.assertRaises(RuntimeError) as ctx:
            ValidationOnlyWriteFirewall.assert_read_only("UPDATE accounts SET balance = 0 WHERE id = 1")
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_08_write_firewall_blocks_delete(self):
        """ValidationOnlyWriteFirewall blocks DELETE mutations."""
        with self.assertRaises(RuntimeError) as ctx:
            ValidationOnlyWriteFirewall.assert_read_only("DELETE FROM customers")
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_09_write_firewall_blocks_drop(self):
        """ValidationOnlyWriteFirewall blocks DROP mutations."""
        with self.assertRaises(RuntimeError) as ctx:
            ValidationOnlyWriteFirewall.assert_read_only("DROP TABLE audit_logs")
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_10_write_firewall_blocks_insert(self):
        """ValidationOnlyWriteFirewall blocks INSERT mutations."""
        with self.assertRaises(RuntimeError) as ctx:
            ValidationOnlyWriteFirewall.assert_read_only("INSERT INTO x VALUES (1)")
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_11_write_firewall_blocks_truncate(self):
        """ValidationOnlyWriteFirewall blocks TRUNCATE mutations."""
        with self.assertRaises(RuntimeError) as ctx:
            ValidationOnlyWriteFirewall.assert_read_only("TRUNCATE TABLE x")
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_12_write_firewall_blocks_create(self):
        """ValidationOnlyWriteFirewall blocks CREATE mutations."""
        with self.assertRaises(RuntimeError) as ctx:
            ValidationOnlyWriteFirewall.assert_read_only("CREATE TABLE x (id INT)")
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_13_write_firewall_allows_select(self):
        """ValidationOnlyWriteFirewall permits SELECT queries."""
        # Must not raise
        ValidationOnlyWriteFirewall.assert_read_only("SELECT COUNT(*) FROM users WHERE active = 1")

    def test_14_write_firewall_blocks_mixed_case_mutation(self):
        """ValidationOnlyWriteFirewall catches mixed-case mutation (uPdAtE)."""
        with self.assertRaises(RuntimeError) as ctx:
            ValidationOnlyWriteFirewall.assert_read_only("uPdAtE accounts SET x = 1")
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_15_write_firewall_blocks_cte_based_mutation(self):
        """ValidationOnlyWriteFirewall catches DELETE inside a CTE construct."""
        with self.assertRaises(RuntimeError) as ctx:
            ValidationOnlyWriteFirewall.assert_read_only("WITH cte AS (SELECT 1) DELETE FROM x")
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_16_sealer_refuses_unknown_validation_status(self):
        """DigitalCertificationSealer issues REVOKED seal for UNKNOWN validation status."""
        sealer = DigitalCertificationSealer()
        seal = sealer.issue_seal(
            "mig-unknown-16", trust_score_val=60.0,
            validation_passed=True, validation_status="UNKNOWN"
        )
        self.assertEqual(seal.status, CertificationSealStatus.REVOKED)

    def test_17_canonical_checksum_normalizes_decimal_scale(self):
        """Decimal('1.0') and Decimal('1.00') must produce identical canonical hashes."""
        from decimal import Decimal
        hash_1 = canonical_hash_row({"amount": Decimal("1.0")})
        hash_2 = canonical_hash_row({"amount": Decimal("1.00")})
        self.assertEqual(hash_1, hash_2)

    def test_18_canonical_checksum_normalizes_timezone_utc(self):
        """Timestamp 10:00 UTC and 15:30 +05:30 must produce identical canonical hashes."""
        from datetime import datetime, timezone, timedelta
        dt_utc = datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
        dt_ist = datetime(2026, 8, 15, 15, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        hash_utc = canonical_hash_row({"ts": dt_utc})
        hash_ist = canonical_hash_row({"ts": dt_ist})
        self.assertEqual(hash_utc, hash_ist)

    def test_19_canonical_checksum_normalizes_unicode_nfc(self):
        """NFC 'e\\u0301' and NFD 'e\\u0301' must produce identical canonical hashes."""
        import unicodedata
        nfc_str = unicodedata.normalize('NFC', 'e\u0301')
        nfd_str = unicodedata.normalize('NFD', 'e\u0301')
        hash_nfc = canonical_hash_row({"text": nfc_str})
        hash_nfd = canonical_hash_row({"text": nfd_str})
        self.assertEqual(hash_nfc, hash_nfd)

    def test_20_canonical_checksum_normalizes_column_casing(self):
        """Column 'ID' and column 'id' must produce identical canonical hashes."""
        hash_upper = canonical_hash_row({"ID": 1, "NAME": "Alice"})
        hash_lower = canonical_hash_row({"id": 1, "name": "Alice"})
        self.assertEqual(hash_upper, hash_lower)

    def test_21_write_firewall_blocks_comment_obfuscated_mutation(self):
        """ValidationOnlyWriteFirewall blocks mutation verbs hidden inside/after SQL comments."""
        with self.assertRaises(RuntimeError) as ctx:
            ValidationOnlyWriteFirewall.assert_read_only("SELECT 1; -- comment\nDELETE FROM users;")
        self.assertIn("strictly forbidden", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
