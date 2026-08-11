"""
AKAAL Unit Tests — Canonical Physical Validation Infrastructure (Step 2 Verification)
====================================================================================
Tests PhysicalChecksumValidator normalization, framed serialization, Merkle roots,
and DataValidator physical dispatch across all 20 required test scenarios.
"""

import datetime
import decimal
import unittest

from akaal.validation.domain.physical_validator import PhysicalChecksumValidator
from akaal.validation.domain.data import DataValidator
from akaal.validation.core.context import ValidationContext


class TestCanonicalPhysicalValidation(unittest.IsolatedAsyncioTestCase):

    def test_01_null_normalization(self):
        val_b = PhysicalChecksumValidator.normalize_value_to_bytes(None)
        self.assertEqual(val_b, b"TYPE:NULL")

    def test_02_oracle_empty_string_semantics(self):
        # Oracle treats empty string as NULL
        val_b = PhysicalChecksumValidator.normalize_value_to_bytes("", dialect="oracle")
        self.assertEqual(val_b, b"TYPE:NULL")

    def test_03_postgresql_empty_string_distinction(self):
        # PostgreSQL distinguishes empty string from NULL
        val_b = PhysicalChecksumValidator.normalize_value_to_bytes("", dialect="postgresql")
        self.assertEqual(val_b, b"TYPE:STR:0:")

    def test_04_decimal_equivalence(self):
        val1 = decimal.Decimal("12.50")
        val2 = decimal.Decimal("12.5")
        b1 = PhysicalChecksumValidator.normalize_value_to_bytes(val1)
        b2 = PhysicalChecksumValidator.normalize_value_to_bytes(val2)
        self.assertEqual(b1, b2)
        self.assertEqual(b1, b"TYPE:DEC:4:12.5")

    def test_05_decimal_precision(self):
        val1 = decimal.Decimal("0.0000000000000000001")
        b1 = PhysicalChecksumValidator.normalize_value_to_bytes(val1)
        self.assertTrue(b1.startswith(b"TYPE:DEC:"))

    def test_06_unicode_nfc_normalization(self):
        # NFD vs NFC
        str_nfd = "cafe\u0301"
        str_nfc = "café"
        b1 = PhysicalChecksumValidator.normalize_value_to_bytes(str_nfd)
        b2 = PhysicalChecksumValidator.normalize_value_to_bytes(str_nfc)
        self.assertEqual(b1, b2)

    def test_07_timestamps_with_timezone(self):
        dt1 = datetime.datetime(2026, 8, 11, 20, 0, 0, tzinfo=datetime.timezone.utc)
        dt2 = datetime.datetime(2026, 8, 11, 16, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-4)))
        b1 = PhysicalChecksumValidator.normalize_value_to_bytes(dt1)
        b2 = PhysicalChecksumValidator.normalize_value_to_bytes(dt2)
        self.assertEqual(b1, b2)

    def test_08_timestamps_without_timezone(self):
        dt = datetime.datetime(2026, 8, 11, 20, 0, 0)
        b1 = PhysicalChecksumValidator.normalize_value_to_bytes(dt)
        self.assertEqual(b1, b"TYPE:DATE:26:2026-08-11T20:00:00.000000")

    def test_09_binary_values(self):
        raw_b = b"\x00\x01\x02\xFF"
        b1 = PhysicalChecksumValidator.normalize_value_to_bytes(raw_b)
        self.assertEqual(b1, b"TYPE:BYTES:4:\x00\x01\x02\xFF")

    def test_10_embedded_delimiter_strings_no_collision(self):
        # ["a|b", "c"] vs ["a", "b|c"]
        cols = ["col1", "col2"]
        row1 = ("a|b", "c")
        row2 = ("a", "b|c")

        h1 = PhysicalChecksumValidator.hash_row(row1, cols)
        h2 = PhysicalChecksumValidator.hash_row(row2, cols)
        self.assertNotEqual(h1, h2)

    def test_11_composite_primary_keys(self):
        cols = ["tenant_id", "user_id", "name"]
        row = (100, 500, "Alice")
        h = PhysicalChecksumValidator.hash_row(row, cols)
        self.assertTrue(isinstance(h, str))
        self.assertEqual(len(h), 64)  # SHA-256 hex length

    def test_12_no_primary_key_behavior(self):
        validator = PhysicalChecksumValidator()
        src_rows = [(1, "A"), (2, "B")]
        tgt_rows = [(2, "B"), (1, "A")]  # Different order
        cols = ["id", "val"]

        # Without PK, table hashes should sort deterministically and pass
        res = validator.validate_table_checksums(src_rows, tgt_rows, cols, pk_columns=None)
        self.assertEqual(res["status"], "PASSED")

    def test_13_different_row_value_different_digest(self):
        cols = ["id", "val"]
        row1 = (1, "Alice")
        row2 = (1, "Bob")
        h1 = PhysicalChecksumValidator.hash_row(row1, cols)
        h2 = PhysicalChecksumValidator.hash_row(row2, cols)
        self.assertNotEqual(h1, h2)

    def test_14_equivalent_logical_oracle_pg_row_same_digest(self):
        # Oracle row with "" (NULL) vs PG row with None (NULL)
        cols = ["id", "val"]
        oracle_row = (1, "")
        pg_row = (1, None)
        h_oracle = PhysicalChecksumValidator.hash_row(oracle_row, cols, dialect="oracle")
        h_pg = PhysicalChecksumValidator.hash_row(pg_row, cols, dialect="postgresql")
        self.assertEqual(h_oracle, h_pg)

    def test_15_row_count_mismatch_validation_failure(self):
        validator = PhysicalChecksumValidator()
        src_rows = [(1, "A"), (2, "B")]
        tgt_rows = [(1, "A")]
        cols = ["id", "val"]

        res = validator.validate_table_checksums(src_rows, tgt_rows, cols)
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("Row count mismatch", res["reason"])

    async def test_16_source_query_failure_validation_failure(self):
        validator = DataValidator()
        ctx = ValidationContext(
            runtime_metadata={
                "physical_validation_context": {
                    "query_error": "ORA-00942: table or view does not exist",
                    "table_name": "MISSING_TABLE",
                }
            }
        )
        res = await validator.validate_domain(ctx)
        self.assertEqual(res.status.value, "FAILED")
        self.assertTrue(len(res.issues) > 0)
        self.assertIn("ORA-00942", res.issues[0].message)

    async def test_17_target_query_failure_validation_failure(self):
        validator = DataValidator()
        ctx = ValidationContext(
            runtime_metadata={
                "physical_validation_context": {
                    "query_error": "psycopg2.OperationalError: relation 'missing_table' does not exist",
                    "table_name": "missing_table",
                }
            }
        )
        res = await validator.validate_domain(ctx)
        self.assertEqual(res.status.value, "FAILED")

    async def test_18_physical_context_cannot_fall_back_to_synthetic_pass(self):
        validator = DataValidator()
        ctx = ValidationContext(
            runtime_metadata={
                "physical_validation_context": {
                    "source_rows": [(1, "Alice")],
                    "target_rows": [(1, "Bob")],  # Data mismatch
                    "columns": ["id", "name"],
                }
            }
        )
        res = await validator.validate_domain(ctx)
        self.assertEqual(res.status.value, "FAILED")
        self.assertNotEqual(res.passed_count, 1000)  # Must not use synthetic 1000 pass count

    def test_19_deterministic_repeated_execution(self):
        cols = ["id", "val"]
        row = (42, "Constant Data")
        h1 = PhysicalChecksumValidator.hash_row(row, cols)
        h2 = PhysicalChecksumValidator.hash_row(row, cols)
        self.assertEqual(h1, h2)

    def test_20_large_value_lob_hashing_behavior(self):
        large_text = "A" * 100000
        cols = ["id", "clob_col"]
        row = (1, large_text)
        h = PhysicalChecksumValidator.hash_row(row, cols)
        self.assertEqual(len(h), 64)


if __name__ == "__main__":
    unittest.main()
