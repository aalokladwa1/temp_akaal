import datetime
import decimal
import unittest

from akaal.validation.domain.reconciliation import (
    CanonicalReconciliationEngine,
    ValidationExecutionMode,
    RowClassification,
    ValidationOnlyWriteFirewall,
    ValidationWriteFirewallError,
    ReconciliationEvidence,
)


class TestP29ValidationOnlyDeepReconciliation(unittest.TestCase):
    """
    P2.9 Validation-Only Mode, Deep Reconciliation & Mismatch Intelligence Unit Test Suite.
    Includes 1-to-1 Requirement Traceability.
    """

    def test_01_validation_only_write_firewall_blocks_target_mutations(self):
        """REQ-P2.9-01: Verify Write Firewall blocks target mutation in VALIDATION_ONLY mode."""
        mode = ValidationExecutionMode.VALIDATION_ONLY
        with self.assertRaises(ValidationWriteFirewallError):
            ValidationOnlyWriteFirewall.assert_target_mutation_allowed(mode, operation_name="INSERT INTO target")

        with self.assertRaises(ValidationWriteFirewallError):
            ValidationOnlyWriteFirewall.assert_target_mutation_allowed(mode, operation_name="TRUNCATE TABLE target")

        # Verify MIGRATION_VALIDATION allows writes if authorized
        ValidationOnlyWriteFirewall.assert_target_mutation_allowed(
            ValidationExecutionMode.MIGRATION_VALIDATION, operation_name="INSERT INTO target"
        )

    def test_02_independent_preexisting_target_validation(self):
        """REQ-P2.9-02: Verify validation operates independently on pre-existing source and target databases."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        source_rows = [(1, "Alice"), (2, "Bob")]
        target_rows = [(1, "Alice"), (2, "Bob")]
        cols = ["id", "name"]

        summary, records = engine.reconcile_tables("users", source_rows, target_rows, cols, pk_columns=["id"])
        self.assertEqual(summary.status, "MATCHED")
        self.assertEqual(summary.matched_count, 2)
        self.assertEqual(len(records), 0)

    def test_03_primary_key_row_identity_reconciliation(self):
        """REQ-P2.9-03: Verify PK row identity categorizes MATCHED, SOURCE_ONLY, TARGET_ONLY, and VALUE_MISMATCH."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        source_rows = [
            (1, "Alice"),   # MATCHED
            (2, "Bob"),     # VALUE_MISMATCH (Target has 'Robert')
            (3, "Charlie")  # SOURCE_ONLY
        ]
        target_rows = [
            (1, "Alice"),   # MATCHED
            (2, "Robert"),  # VALUE_MISMATCH
            (4, "David")    # TARGET_ONLY
        ]
        cols = ["id", "name"]

        summary, records = engine.reconcile_tables("users", source_rows, target_rows, cols, pk_columns=["id"])
        self.assertEqual(summary.status, "MISMATCH")
        self.assertEqual(summary.matched_count, 1)
        self.assertEqual(summary.source_only_count, 1)
        self.assertEqual(summary.target_only_count, 1)
        self.assertEqual(summary.value_mismatch_count, 1)

        class_map = {r.row_identity["id"]: r.classification for r in records}
        self.assertEqual(class_map[2], RowClassification.VALUE_MISMATCH)
        self.assertEqual(class_map[3], RowClassification.SOURCE_ONLY)
        self.assertEqual(class_map[4], RowClassification.TARGET_ONLY)

    def test_04_composite_primary_key_reconciliation(self):
        """REQ-P2.9-04: Verify composite PK identity maintains deterministic key ordering."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        source_rows = [("US", 101, 500.00), ("US", 102, 300.00)]
        target_rows = [("US", 101, 500.00), ("US", 102, 999.00)]  # 102 has VALUE_MISMATCH
        cols = ["country_code", "store_id", "revenue"]

        summary, records = engine.reconcile_tables(
            "store_sales", source_rows, target_rows, cols, pk_columns=["country_code", "store_id"]
        )

        self.assertEqual(summary.status, "MISMATCH")
        self.assertEqual(summary.matched_count, 1)
        self.assertEqual(summary.value_mismatch_count, 1)

        mismatch_record = records[0]
        self.assertEqual(mismatch_record.row_identity, {"country_code": "US", "store_id": 102})

    def test_05_column_level_difference_localization(self):
        """REQ-P2.9-05: Verify column-level difference localization pinpoints mismatched columns."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        source_rows = [(1, "Product A", 100.00, "Active")]
        target_rows = [(1, "Product A", 100.00, "Archived")]  # Only 'status' column differs
        cols = ["id", "name", "price", "status"]

        summary, records = engine.reconcile_tables("products", source_rows, target_rows, cols, pk_columns=["id"])
        self.assertEqual(summary.value_mismatch_count, 1)

        mismatch = records[0]
        col_diffs = {c.column_name: c for c in mismatch.column_differences}
        self.assertTrue(col_diffs["id"].is_match)
        self.assertTrue(col_diffs["name"].is_match)
        self.assertTrue(col_diffs["price"].is_match)
        self.assertFalse(col_diffs["status"].is_match)

    def test_06_no_stable_key_handled_as_indeterminate(self):
        """REQ-P2.9-06: Verify table with no PK or Unique Key identity returns INDETERMINATE."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        source_rows = [("log1", "info"), ("log2", "warn")]
        target_rows = [("log1", "info"), ("log2", "error")]
        cols = ["message", "level"]

        summary, records = engine.reconcile_tables("logs", source_rows, target_rows, cols, pk_columns=None)
        self.assertEqual(summary.status, "INDETERMINATE")
        self.assertEqual(summary.indeterminate_count, 2)

    def test_07_aggregated_database_evidence_generation(self):
        """REQ-P2.9-07: Verify aggregated database reconciliation evidence generation."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        s1, _ = engine.reconcile_tables("users", [(1, "A")], [(1, "A")], ["id", "name"], pk_columns=["id"])
        s2, _ = engine.reconcile_tables("orders", [(10, 50)], [(10, 99)], ["id", "amount"], pk_columns=["id"])

        evidence = engine.aggregate_database_evidence("VAL-001", [s1, s2])
        self.assertEqual(evidence.execution_mode, ValidationExecutionMode.VALIDATION_ONLY)
        self.assertEqual(evidence.database_summary.tables_validated, 2)
        self.assertEqual(evidence.database_summary.tables_matched, 1)
        self.assertEqual(evidence.database_summary.tables_mismatched, 1)
        self.assertEqual(evidence.database_summary.final_status, "MISMATCHED")
        self.assertIsNotNone(evidence.evidence_fingerprint)

    def test_08_raw_data_privacy_firewall(self):
        """REQ-P2.9-08: Verify evidence records exclude raw customer values/passwords/LOBs."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        source_rows = [(1, "sensitive_password_123")]
        target_rows = [(1, "sensitive_password_456")]
        cols = ["id", "password"]

        summary, records = engine.reconcile_tables("accounts", source_rows, target_rows, cols, pk_columns=["id"])
        record = records[0]

        # Raw values must NOT exist on record attributes
        rec_str = str(record)
        self.assertNotIn("sensitive_password_123", rec_str)
        self.assertNotIn("sensitive_password_456", rec_str)

    def test_09_all_12_cross_engine_reconciliation_routes(self):
        """REQ-P2.9-09: Verify deep reconciliation operates cleanly across all 12 cross-engine routes."""
        engines = ["oracle", "postgresql", "mysql", "mssql"]
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        routes_tested = 0

        source_rows = [(1, decimal.Decimal("100.00"), datetime.date(2026, 8, 14))]
        target_rows = [(1, decimal.Decimal("100.00"), datetime.date(2026, 8, 14))]
        cols = ["id", "amount", "dt"]

        for src in engines:
            for tgt in engines:
                if src == tgt:
                    continue
                summary, _ = engine.reconcile_tables(
                    "txns", source_rows, target_rows, cols, pk_columns=["id"], source_dialect=src, target_dialect=tgt
                )
                self.assertEqual(summary.status, "MATCHED")
                routes_tested += 1

        self.assertEqual(routes_tested, 12)

    def test_10_database_5_extensibility_proof(self):
        """REQ-P2.9-10: Verify Database #5 (IBM DB2) reconciliation operates without core engine changes."""
        engine = CanonicalReconciliationEngine(mode=ValidationExecutionMode.VALIDATION_ONLY)
        summary, _ = engine.reconcile_tables(
            "tbl5", [(1, "val")], [(1, "val")], ["id", "val"], pk_columns=["id"], source_dialect="ibm_db2", target_dialect="postgresql"
        )
        self.assertEqual(summary.status, "MATCHED")


if __name__ == "__main__":
    unittest.main()
