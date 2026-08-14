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


class TestP281ValidationSemanticAcceptance(unittest.TestCase):
    """
    P2.8.1 Final Canonical Validation, Cross-Database Serialization & Merkle Integrity Semantic Acceptance Suite.
    Adversarial testing for framing injectivity, false MATCH firewall, LOB streaming, timezone normalization,
    and cross-type collision resistance.
    """

    def test_01_framing_injective_field_boundary_collision_resistance(self):
        """Adversarial test: prove ["ab", "c"] and ["a", "bc"] can NEVER serialize identically."""
        r1 = ("ab", "c")
        r2 = ("a", "bc")
        cols = ["col1", "col2"]

        s1 = PhysicalChecksumValidator.serialize_row(r1, cols)
        s2 = PhysicalChecksumValidator.serialize_row(r2, cols)

        self.assertNotEqual(s1, s2)

    def test_02_false_match_firewall_enforcement(self):
        """Adversarial test: prove row count or Merkle digest mismatches NEVER report PASSED."""
        v = PhysicalChecksumValidator()

        # Row count mismatch
        res_cnt = v.validate_table_checksums([("val1",)], [("val1",), ("val2",)], ["col1"])
        self.assertEqual(res_cnt["status"], "FAILED")

        # Data digest mismatch
        res_data = v.validate_table_checksums([("val1",)], [("val2",)], ["col1"])
        self.assertEqual(res_data["status"], "FAILED")

    def test_03_lob_streaming_chunk_boundary_independence(self):
        """Adversarial test: prove LOB streaming chunk boundaries do not alter final digest."""
        chunks_a = [b"chunk1_", b"chunk2_", b"chunk3"]
        chunks_b = [b"chunk1_chunk2_", b"chunk3"]
        chunks_c = [b"chunk1_chunk2_chunk3"]

        h_a = PhysicalChecksumValidator.hash_lob_stream(chunks_a)
        h_b = PhysicalChecksumValidator.hash_lob_stream(chunks_b)
        h_c = PhysicalChecksumValidator.hash_lob_stream(chunks_c)

        self.assertEqual(h_a, h_b)
        self.assertEqual(h_b, h_c)

    def test_04_timezone_equivalent_instants_canonicalize_equal(self):
        """Adversarial test: prove 12:00 EST and 17:00 UTC represent identical TIMESTAMPTZ instant."""
        est_tz = datetime.timezone(datetime.timedelta(hours=-5))
        dt_est = datetime.datetime(2026, 8, 14, 12, 0, 0, tzinfo=est_tz)

        utc_tz = datetime.timezone.utc
        dt_utc = datetime.datetime(2026, 8, 14, 17, 0, 0, tzinfo=utc_tz)

        b_est = CanonicalValueSerializer.serialize_value(dt_est)
        b_utc = CanonicalValueSerializer.serialize_value(dt_utc)

        self.assertEqual(b_est, b_utc)

    def test_05_oracle_empty_string_not_globally_normalized_to_null(self):
        """Adversarial test: prove empty string "" is preserved as STR for PostgreSQL/MySQL/MSSQL but NULL for Oracle."""
        b_ansi = CanonicalValueSerializer.serialize_value("", dialect="ansi")
        b_pg = CanonicalValueSerializer.serialize_value("", dialect="postgresql")
        b_my = CanonicalValueSerializer.serialize_value("", dialect="mysql")
        b_ms = CanonicalValueSerializer.serialize_value("", dialect="mssql")
        b_ora = CanonicalValueSerializer.serialize_value("", dialect="oracle")

        self.assertEqual(b_ansi, b_pg)
        self.assertEqual(b_pg, b_my)
        self.assertEqual(b_my, b_ms)
        self.assertNotEqual(b_pg, b_ora)
        self.assertEqual(b_ora, b"TYPE:NULL:1:0:")

    def test_06_evidence_fingerprint_deterministic_and_machine_independent(self):
        """Adversarial test: prove evidence fingerprints are deterministic across runs."""
        v = PhysicalChecksumValidator()
        res1 = v.validate_table_checksums([("test_data",)], [("test_data",)], ["col1"])
        res2 = v.validate_table_checksums([("test_data",)], [("test_data",)], ["col1"])

        self.assertEqual(res1["evidence_fingerprint"], res2["evidence_fingerprint"])


if __name__ == "__main__":
    unittest.main()
