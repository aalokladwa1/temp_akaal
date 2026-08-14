import datetime
import decimal
import unittest
from unittest.mock import patch

from akaal.validation.domain.reconciliation import (
    CanonicalReconciliationEngine,
    ValidationExecutionMode,
    RowClassification,
    ValidationOnlyWriteFirewall,
    ValidationWriteFirewallError,
    TableReconciliationSummary,
    DatabaseReconciliationSummary,
)


class TestP291ReconciliationSemanticAcceptance(unittest.TestCase):
    """
    P2.9.1 Final Validation-Only, Deep Reconciliation & Mismatch Intelligence Semantic Acceptance Suite.
    Hostile semantic verification.
    """

    def test_01_write_firewall_bypass_resistance(self):
        """Verify Write Firewall resists all target mutation operations in VALIDATION_ONLY mode."""
        mode = ValidationExecutionMode.VALIDATION_ONLY
        operations = [
            "INSERT INTO t", "UPDATE t SET x=1", "DELETE FROM t",
            "MERGE INTO t", "TRUNCATE TABLE t", "DROP TABLE t",
            "ALTER TABLE t", "CREATE TABLE t", "CDC_APPLY"
        ]
        for op in operations:
            with self.assertRaises(ValidationWriteFirewallError):
                ValidationOnlyWriteFirewall.assert_target_mutation_allowed(mode, operation_name=op)

    def test_02_false_match_firewall_on_serialization_exception(self):
        """Verify execution failure forces ERROR status and NEVER MATCHED."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)

        with patch("akaal.validation.domain.reconciliation.CanonicalValueSerializer.serialize_value", side_effect=ValueError("Driver Serialization Error")):
            summary, records = engine.reconcile_tables("fail_table", [(1, "A")], [(1, "A")], ["id", "val"], pk_columns=["id"])
            self.assertEqual(summary.status, "ERROR")
            self.assertNotEqual(summary.status, "MATCHED")

    def test_03_injective_composite_key_identity_encoding(self):
        """Verify composite key sorting uses injective byte framing preventing collisions."""
        k1 = ("ab", "c")
        k2 = ("a", "bc")

        b1 = CanonicalReconciliationEngine._canonical_key_sort_bytes(k1)
        b2 = CanonicalReconciliationEngine._canonical_key_sort_bytes(k2)

        self.assertNotEqual(b1, b2)

    def test_04_nullable_key_rejected_as_indeterminate(self):
        """Verify unique key containing NULL value is rejected as INDETERMINATE."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        source_rows = [(1, "A"), (None, "B")]
        target_rows = [(1, "A"), (None, "B")]
        cols = ["id", "val"]

        summary, records = engine.reconcile_tables("null_key_tbl", source_rows, target_rows, cols, pk_columns=["id"])
        self.assertEqual(summary.status, "INDETERMINATE")

    def test_05_summary_counts_mathematically_coherent(self):
        """Verify summary row counts reconcile mathematically."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        source_rows = [(1, "Alice"), (2, "Bob"), (3, "Charlie")]
        target_rows = [(1, "Alice"), (2, "Robert"), (4, "David")]
        cols = ["id", "name"]

        summary, records = engine.reconcile_tables("summary_tbl", source_rows, target_rows, cols, pk_columns=["id"])

        # Check math: matched (1) + source_only (1) + target_only (1) + value_mismatch (1)
        evaluated_sum = summary.matched_count + summary.source_only_count + summary.target_only_count + summary.value_mismatch_count
        self.assertEqual(evaluated_sum, 4)

    def test_06_database_summary_aggregate_failure_propagation(self):
        """Verify aggregate database status marks ERROR if any table fails."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)

        s_passed = TableReconciliationSummary("t1", 10, 10, 10, 0, 0, 0, 0, 0, 0, 0, "MATCHED")
        s_error = TableReconciliationSummary("t2", 5, 5, 0, 0, 0, 0, 0, 0, 5, 1, "ERROR")

        evidence = engine.aggregate_database_evidence("VAL-ERR-01", [s_passed, s_error])
        self.assertEqual(evidence.database_summary.final_status, "ERROR")
        self.assertEqual(evidence.database_summary.tables_failed, 1)

    def test_07_privacy_firewall_protects_sensitive_row_payloads(self):
        """Verify raw row contents are absent from record strings."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        s_rows = [(100, "secret_ssn_999")]
        t_rows = [(100, "secret_ssn_888")]
        cols = ["id", "ssn"]

        summary, records = engine.reconcile_tables("privacy_tbl", s_rows, t_rows, cols, pk_columns=["id"])
        mismatch_record = records[0]

        rec_str = str(mismatch_record)
        self.assertNotIn("secret_ssn_999", rec_str)
        self.assertNotIn("secret_ssn_888", rec_str)


if __name__ == "__main__":
    unittest.main()
