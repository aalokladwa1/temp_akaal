"""
Unit Tests for AKAAL Zero-Tolerance Parity Verifier & In-Place Delta Self-Healing
================================================================================
"""

import unittest
from akaal.validation.domain.zero_tolerance_verifier import (
    ZeroToleranceParityVerifier,
    ZeroToleranceVerificationResult,
)
from akaal.healing.services.in_place_delta_healer import (
    InPlaceDeltaHealer,
    InPlaceHealingResult,
)


class TestZeroToleranceAndHealing(unittest.TestCase):
    """Test suite for strict 100.0000% parity verification and in-place delta self-healing."""

    def setUp(self):
        self.verifier = ZeroToleranceParityVerifier()
        self.healer = InPlaceDeltaHealer()

        self.source_data = [
            {"id": 1, "name": "Alice", "balance": 1000.0, "status": "ACTIVE"},
            {"id": 2, "name": "Bob", "balance": 2500.5, "status": "ACTIVE"},
            {"id": 3, "name": "Charlie", "balance": 50.0, "status": "SUSPENDED"},
            {"id": 4, "name": "Diana", "balance": 9900.0, "status": "ACTIVE"},
        ]

    def test_identical_datasets_achieve_100_percent_parity(self):
        """Verify that identical source and target datasets yield 100.0000% parity."""
        target_data = [dict(r) for r in self.source_data]
        res = self.verifier.verify_table_parity("accounts", self.source_data, target_data)

        self.assertTrue(res.zero_tolerance_satisfied)
        self.assertEqual(res.exact_parity_percentage, 100.0000)
        self.assertEqual(len(res.missing_pks), 0)
        self.assertEqual(len(res.corrupted_pks), 0)

    def test_missing_and_corrupted_rows_detected(self):
        """Verify detection of missing PK (id=4) and corrupted record (id=2 balance changed)."""
        target_data = [
            {"id": 1, "name": "Alice", "balance": 1000.0, "status": "ACTIVE"},
            {"id": 2, "name": "Bob", "balance": 9999.9, "status": "ACTIVE"}, # Corrupted balance
            {"id": 3, "name": "Charlie", "balance": 50.0, "status": "SUSPENDED"},
            # id=4 missing
        ]

        res = self.verifier.verify_table_parity("accounts", self.source_data, target_data)

        self.assertFalse(res.zero_tolerance_satisfied)
        self.assertLess(res.exact_parity_percentage, 100.0000)
        self.assertEqual(res.missing_pks, [4])
        self.assertEqual(res.corrupted_pks, [2])

    def test_in_place_healing_repairs_deltas_to_100_percent(self):
        """Verify that InPlaceDeltaHealer repairs missing & corrupted records to achieve 100.0000% parity."""
        target_data = [
            {"id": 1, "name": "Alice", "balance": 1000.0, "status": "ACTIVE"},
            {"id": 2, "name": "Bob", "balance": 9999.9, "status": "ACTIVE"}, # Corrupted balance
            {"id": 3, "name": "Charlie", "balance": 50.0, "status": "SUSPENDED"},
            # id=4 missing
        ]

        # 1. First verification fails zero tolerance
        res1 = self.verifier.verify_table_parity("accounts", self.source_data, target_data)
        self.assertFalse(res1.zero_tolerance_satisfied)

        # 2. Apply targeted in-place healing for delta PKs
        heal_res = self.healer.heal_delta_records(
            table_name="accounts",
            source_records=self.source_data,
            target_records=target_data,
            missing_pks=res1.missing_pks,
            corrupted_pks=res1.corrupted_pks,
            primary_key_col="id"
        )

        self.assertTrue(heal_res.success)
        self.assertEqual(heal_res.repaired_missing_count, 1)
        self.assertEqual(heal_res.repaired_corrupted_count, 1)
        self.assertEqual(heal_res.total_repairs_applied, 2)

        # 3. Re-verification MUST achieve 100.0000% parity
        res2 = self.verifier.verify_table_parity(
            "accounts",
            self.source_data,
            heal_res.repaired_target_records
        )

        self.assertTrue(res2.zero_tolerance_satisfied)
        self.assertEqual(res2.exact_parity_percentage, 100.0000)
        self.assertEqual(len(res2.missing_pks), 0)
        self.assertEqual(len(res2.corrupted_pks), 0)


if __name__ == "__main__":
    unittest.main()
