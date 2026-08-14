import unittest
from akaal.schema.domain.types import (
    CanonicalTypeCategory,
    ConversionSafety,
    CanonicalType,
    TargetTypeEmission,
)
from akaal.schema.domain.type_registry import CanonicalTypeRegistry
from akaal.schema.domain.models import (
    CanonicalSchemaModel,
    CanonicalTable,
    CanonicalColumn,
    CanonicalObjectIdentity,
)


class TestP231DatatypeSemanticAcceptance(unittest.TestCase):
    """
    P2.3.1 Final Universal Datatype Semantic Acceptance & Hardening Test Suite.
    """

    def test_01_mysql_tinyint1_not_blindly_boolean(self):
        """Verify MySQL TINYINT(1) preserves INTEGER semantics by default, becoming BOOLEAN only with explicit evidence."""
        c_int = CanonicalTypeRegistry.normalize_source_type("MYSQL", "TINYINT(1)")
        self.assertEqual(c_int.category, CanonicalTypeCategory.INTEGER)
        self.assertEqual(c_int.bits, 8)
        self.assertTrue(c_int.extra.get("mysql_tinyint1_ambiguous"))

        c_bool = CanonicalTypeRegistry.normalize_source_type("MYSQL", "TINYINT(1)", extra_metadata={"is_boolean": True})
        self.assertEqual(c_bool.category, CanonicalTypeCategory.BOOLEAN)

    def test_02_oracle_number_ambiguity_and_negative_scale(self):
        """Verify Oracle NUMBER ambiguity, precision/scale, and negative scale handling."""
        c_amb = CanonicalTypeRegistry.normalize_source_type("ORACLE", "NUMBER")
        self.assertEqual(c_amb.category, CanonicalTypeCategory.DECIMAL)
        self.assertTrue(c_amb.extra.get("oracle_ambiguous_number"))

        c_neg = CanonicalTypeRegistry.normalize_source_type("ORACLE", "NUMBER(5,-2)")
        self.assertEqual(c_neg.category, CanonicalTypeCategory.INTEGER)
        self.assertTrue(c_neg.extra.get("oracle_negative_scale"))

    def test_03_oracle_date_preserves_time_component(self):
        """Verify Oracle DATE preserves time component (TIMESTAMP category)."""
        c_date = CanonicalTypeRegistry.normalize_source_type("ORACLE", "DATE")
        self.assertEqual(c_date.category, CanonicalTypeCategory.TIMESTAMP)
        self.assertFalse(c_date.timezone_aware)

        c_ltz = CanonicalTypeRegistry.normalize_source_type("ORACLE", "TIMESTAMP WITH LOCAL TIME ZONE")
        self.assertEqual(c_ltz.category, CanonicalTypeCategory.TIMESTAMPTZ)
        self.assertTrue(c_ltz.extra.get("oracle_local_tz"))

    def test_04_mssql_rowversion_not_temporal_timestamp(self):
        """Verify MSSQL ROWVERSION / TIMESTAMP normalizes to VARBINARY, never temporal timestamp."""
        c_rv = CanonicalTypeRegistry.normalize_source_type("MSSQL", "ROWVERSION")
        self.assertEqual(c_rv.category, CanonicalTypeCategory.VARBINARY)
        self.assertTrue(c_rv.extra.get("mssql_rowversion"))

        emission = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", c_rv)
        self.assertEqual(emission.target_native_type, "BYTEA")
        self.assertEqual(emission.safety, ConversionSafety.VENDOR_SPECIFIC)
        self.assertIn("target database cannot automatically generate", emission.warning_message)

    def test_05_unsigned_64bit_integer_range_safety(self):
        """Verify MySQL BIGINT UNSIGNED maps safely to PostgreSQL NUMERIC(20,0) to prevent signed overflow."""
        c_ubig = CanonicalTypeRegistry.normalize_source_type("MYSQL", "BIGINT UNSIGNED")
        self.assertEqual(c_ubig.category, CanonicalTypeCategory.INTEGER)
        self.assertFalse(c_ubig.is_signed)

        emission = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", c_ubig)
        self.assertEqual(emission.target_native_type, "NUMERIC(20,0)")
        self.assertEqual(emission.safety, ConversionSafety.SAFE)

    def test_06_unknown_type_safety_classification(self):
        """Verify unknown vendor types normalize to UNKNOWN and emit UNSUPPORTED safety classification."""
        c_unk = CanonicalTypeRegistry.normalize_source_type("ORACLE", "MYSTERY_TYPE")
        self.assertEqual(c_unk.category, CanonicalTypeCategory.UNKNOWN)

        emission = CanonicalTypeRegistry.emit_target_type("POSTGRESQL", c_unk)
        self.assertEqual(emission.safety, ConversionSafety.UNSUPPORTED)

    def test_07_plugin_registry_extensibility(self):
        """Verify register_normalizer and register_emitter allow dynamic plugin registration for custom engines."""

        def custom_normalizer(raw, l, p, s):
            return CanonicalType(category=CanonicalTypeCategory.VARCHAR, raw_vendor_type=raw, length=123)

        def custom_emitter(c):
            return TargetTypeEmission("CUSTOM_DB", f"CUSTOM_VARCHAR({c.length})", ConversionSafety.EXACT)

        CanonicalTypeRegistry.register_normalizer("CUSTOM_DB", custom_normalizer)
        CanonicalTypeRegistry.register_emitter("CUSTOM_DB", custom_emitter)

        c_type = CanonicalTypeRegistry.normalize_source_type("CUSTOM_DB", "FOO_TYPE")
        self.assertEqual(c_type.length, 123)

        emission = CanonicalTypeRegistry.emit_target_type("CUSTOM_DB", c_type)
        self.assertEqual(emission.target_native_type, "CUSTOM_VARCHAR(123)")

    def test_08_fingerprint_determinism_with_canonical_types(self):
        """Verify schema SHA-256 fingerprint remains 100% deterministic with CanonicalType models."""
        m1 = CanonicalSchemaModel(schema_name="hr", engine="ORACLE")
        id1 = CanonicalObjectIdentity(schema_name="hr", object_name="emp")
        c1 = CanonicalTypeRegistry.normalize_source_type("ORACLE", "NUMBER(10,2)")
        col1 = CanonicalColumn(name="sal", ordinal_position=1, source_native_type="NUMBER(10,2)", canonical_type_model=c1)
        m1.add_table(CanonicalTable(identity=id1, columns=[col1]))

        m2 = CanonicalSchemaModel(schema_name="hr", engine="ORACLE")
        id2 = CanonicalObjectIdentity(schema_name="hr", object_name="emp")
        c2 = CanonicalTypeRegistry.normalize_source_type("ORACLE", "NUMBER(10,2)")
        col2 = CanonicalColumn(name="sal", ordinal_position=1, source_native_type="NUMBER(10,2)", canonical_type_model=c2)
        m2.add_table(CanonicalTable(identity=id2, columns=[col2]))

        self.assertEqual(m1.compute_schema_fingerprint(), m2.compute_schema_fingerprint())


if __name__ == "__main__":
    unittest.main()
