import decimal
import datetime
import unittest
import uuid

from akaal.schema.domain.types import CanonicalType, CanonicalTypeCategory
from akaal.validation.domain.physical_validator import (
    PhysicalChecksumValidator,
    CanonicalValueSerializer,
    SERIALIZATION_VERSION,
)


class TestP28CanonicalValidationEngine(unittest.TestCase):
    """
    P2.8 Canonical Validation Engine, Cross-Database Value Serialization & Merkle Integrity Test Suite.
    """

    def test_01_null_semantics_unambiguous_framing(self):
        """Verify NULL, empty string, 'NULL', 0, False, b'' hash distinctly."""
        v_null = CanonicalValueSerializer.serialize_value(None)
        v_empty_str = CanonicalValueSerializer.serialize_value("")
        v_null_str = CanonicalValueSerializer.serialize_value("NULL")
        v_zero = CanonicalValueSerializer.serialize_value(0)
        v_false = CanonicalValueSerializer.serialize_value(False)
        v_empty_bytes = CanonicalValueSerializer.serialize_value(b"")

        bytes_list = [v_null, v_empty_str, v_null_str, v_zero, v_false, v_empty_bytes]
        self.assertEqual(len(set(bytes_list)), len(bytes_list))  # All distinct!

    def test_02_numeric_canonicalization_decimal_normalization(self):
        """Verify Decimal('100.00'), 100.0, and 100 produce identical canonical bytes."""
        b1 = CanonicalValueSerializer.serialize_value(decimal.Decimal("100.00"))
        b2 = CanonicalValueSerializer.serialize_value(100.0)
        b3 = CanonicalValueSerializer.serialize_value(100)

        self.assertEqual(b1, b2)
        self.assertEqual(b2, b3)

    def test_03_float_special_values_nan_inf(self):
        """Verify special IEEE float values (NaN, +Inf, -Inf) encode deterministically."""
        b_nan = CanonicalValueSerializer.serialize_value(float("nan"))
        b_inf = CanonicalValueSerializer.serialize_value(float("inf"))
        b_neginf = CanonicalValueSerializer.serialize_value(float("-inf"))

        self.assertIn(b"NaN", b_nan)
        self.assertIn(b"+Infinity", b_inf)
        self.assertIn(b"-Infinity", b_neginf)

    def test_04_boolean_normalization(self):
        """Verify boolean normalization encodes True as 1 and False as 0."""
        b_true = CanonicalValueSerializer.serialize_value(True)
        b_false = CanonicalValueSerializer.serialize_value(False)

        self.assertIn(b"TYPE:BOOL:0:1:1", b_true)
        self.assertIn(b"TYPE:BOOL:0:1:0", b_false)

    def test_05_utf8_text_unicode_nfc_normalization(self):
        """Verify text serialization uses UTF-8 and NFC normalization."""
        # e + combining acute accent vs precomposed e with acute accent
        str1 = "e\u0301"
        str2 = "\u00e9"

        b1 = CanonicalValueSerializer.serialize_value(str1)
        b2 = CanonicalValueSerializer.serialize_value(str2)

        self.assertEqual(b1, b2)

    def test_06_oracle_empty_string_treated_as_null(self):
        """Verify Oracle dialect treats empty string as NULL."""
        b_ansi = CanonicalValueSerializer.serialize_value("", dialect="ansi")
        b_ora = CanonicalValueSerializer.serialize_value("", dialect="oracle")

        self.assertNotEqual(b_ansi, b_ora)
        self.assertEqual(b_ora, b"TYPE:NULL:1:0:")

    def test_07_datetime_tz_normalization_to_utc(self):
        """Verify timezone-aware datetimes normalize to UTC ISO-8601 string."""
        tz_est = datetime.timezone(datetime.timedelta(hours=-5))
        dt_est = datetime.datetime(2026, 8, 14, 12, 0, 0, tzinfo=tz_est)

        tz_utc = datetime.timezone.utc
        dt_utc = datetime.datetime(2026, 8, 14, 17, 0, 0, tzinfo=tz_utc)

        b_est = CanonicalValueSerializer.serialize_value(dt_est)
        b_utc = CanonicalValueSerializer.serialize_value(dt_utc)

        self.assertEqual(b_est, b_utc)

    def test_08_binary_exact_bytes_hashing(self):
        """Verify binary data hashes exact byte sequence."""
        raw = b"\x00\xff\xfe\xfd"
        b_res = CanonicalValueSerializer.serialize_value(raw)
        self.assertIn(raw, b_res)

    def test_09_uuid_normalization(self):
        """Verify UUID object and UUID string encode identically."""
        u_str = "123e4567-e89b-12d3-a456-426614174000"
        u_obj = uuid.UUID(u_str)

        b_str = CanonicalValueSerializer.serialize_value(u_str, canonical_type=CanonicalType(category=CanonicalTypeCategory.UUID, raw_vendor_type="UUID"))
        b_obj = CanonicalValueSerializer.serialize_value(u_obj)

        self.assertEqual(b_str, b_obj)

    def test_10_json_deterministic_key_ordering(self):
        """Verify JSON key ordering differences hash identically."""
        j1 = '{"b": 2, "a": 1}'
        j2 = '{"a": 1, "b": 2}'

        b1 = CanonicalValueSerializer.serialize_value(j1, canonical_type=CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type="JSON"))
        b2 = CanonicalValueSerializer.serialize_value(j2, canonical_type=CanonicalType(category=CanonicalTypeCategory.JSON, raw_vendor_type="JSON"))

        self.assertEqual(b1, b2)

    def test_11_lob_streaming_hash_without_full_ram_materialization(self):
        """Verify streaming LOB hashing computes deterministic SHA-256."""
        chunks = [b"chunk1_", b"chunk2_", b"chunk3"]
        h_stream = PhysicalChecksumValidator.hash_lob_stream(chunks)
        h_full = PhysicalChecksumValidator.hash_lob_stream([b"chunk1_chunk2_chunk3"])

        self.assertEqual(h_stream, h_full)

    def test_12_ambiguous_concatenation_resistance(self):
        """Verify length-prefixed row framing prevents field boundary collisions."""
        v = PhysicalChecksumValidator()
        r1 = ("ab", "c")
        r2 = ("a", "bc")
        cols = ["c1", "c2"]

        h1 = v.hash_row(r1, cols)
        h2 = v.hash_row(r2, cols)

        self.assertNotEqual(h1, h2)

    def test_13_deterministic_merkle_root_and_empty_dataset(self):
        """Verify Merkle root is deterministic and empty dataset produces valid root."""
        v = PhysicalChecksumValidator()
        h_empty = v.build_merkle_root([])
        self.assertIsNotNone(h_empty)

        h1 = v.build_merkle_root(["hash1", "hash2", "hash3"])
        h2 = v.build_merkle_root(["hash1", "hash2", "hash3"])
        self.assertEqual(h1, h2)

    def test_14_versioned_evidence_format(self):
        """Verify validation evidence contains SERIALIZATION_VERSION = AKAAL-CANONICAL-V1."""
        v = PhysicalChecksumValidator()
        res = v.validate_table_checksums([("val1",)], [("val1",)], ["col1"])

        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(res["serialization_version"], SERIALIZATION_VERSION)
        self.assertEqual(res["hash_algorithm"], "SHA-256")
        self.assertIn("evidence_fingerprint", res)

    def test_15_all_12_cross_engine_validation_routes(self):
        """Verify validation operates identically across all 12 pairwise engine directions."""
        engines = ["oracle", "postgresql", "mysql", "mssql"]
        v = PhysicalChecksumValidator()
        routes_tested = 0

        rows = [(100, "active", datetime.date(2026, 8, 14))]
        cols = ["id", "status", "dt"]

        for src in engines:
            for tgt in engines:
                if src == tgt:
                    continue
                res = v.validate_table_checksums(rows, rows, cols, source_dialect=src, target_dialect=tgt)
                self.assertEqual(res["status"], "PASSED")
                routes_tested += 1

        self.assertEqual(routes_tested, 12)

    def test_16_database_5_extensibility_proof(self):
        """Verify hypothetical Database #5 (IBM DB2) validation uses same canonical serialization."""
        v = PhysicalChecksumValidator()
        res = v.validate_table_checksums([(1, "data")], [(1, "data")], ["id", "val"], source_dialect="ibm_db2", target_dialect="postgresql")
        self.assertEqual(res["status"], "PASSED")


if __name__ == "__main__":
    unittest.main()
