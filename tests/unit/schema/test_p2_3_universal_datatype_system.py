import unittest
from akaal.schema.domain.types import (
    CanonicalTypeCategory,
    ConversionSafety,
    CanonicalType,
    TargetTypeEmission,
)
from akaal.schema.domain.type_registry import CanonicalTypeRegistry
from akaal.core.compatibility.compatibility_layer import CompatibilityLayer
from akaal.core.models.enums import SystemType


class TestP23UniversalDatatypeSystem(unittest.TestCase):
    """
    P2.3 Universal Datatype System & Rulebook Standardization Test Suite.
    """

    def test_01_canonical_type_construction_and_string(self):
        """Verify CanonicalType construction and readable string generation."""
        c = CanonicalType(
            category=CanonicalTypeCategory.VARCHAR,
            raw_vendor_type="NVARCHAR2(200)",
            length=200,
            is_unicode=True,
        )
        self.assertEqual(c.category, CanonicalTypeCategory.VARCHAR)
        self.assertTrue(c.is_unicode)
        self.assertIn("CanonicalVarchar", c.to_canonical_string())
        self.assertIn("unicode=True", c.to_canonical_string())

    def test_02_oracle_source_normalization(self):
        """Verify Oracle native types normalize correctly to CanonicalType."""
        c_num = CanonicalTypeRegistry.normalize_source_type("ORACLE", "NUMBER(10,2)")
        self.assertEqual(c_num.category, CanonicalTypeCategory.DECIMAL)
        self.assertEqual(c_num.precision, 10)
        self.assertEqual(c_num.scale, 2)

        c_date = CanonicalTypeRegistry.normalize_source_type("ORACLE", "DATE")
        self.assertEqual(c_date.category, CanonicalTypeCategory.TIMESTAMP)  # Oracle DATE contains time!

        c_clob = CanonicalTypeRegistry.normalize_source_type("ORACLE", "CLOB")
        self.assertEqual(c_clob.category, CanonicalTypeCategory.TEXT)

    def test_03_mssql_rowversion_special_handling(self):
        """Verify MSSQL ROWVERSION is normalized to VARBINARY rather than temporal TIMESTAMP."""
        c_rv = CanonicalTypeRegistry.normalize_source_type("MSSQL", "ROWVERSION")
        self.assertEqual(c_rv.category, CanonicalTypeCategory.VARBINARY)
        self.assertTrue(c_rv.extra.get("mssql_rowversion"))

    def test_04_mysql_tinyint1_boolean_handling(self):
        """Verify MySQL TINYINT(1) normalizes to BOOLEAN."""
        c_bool = CanonicalTypeRegistry.normalize_source_type("MYSQL", "TINYINT(1)")
        self.assertEqual(c_bool.category, CanonicalTypeCategory.BOOLEAN)

    def test_05_all_12_cross_engine_directions(self):
        """Verify all 12 pairwise directional type conversions succeed through 2-step canonical pipeline."""
        engines = ["ORACLE", "POSTGRESQL", "MYSQL", "MSSQL"]
        sample_types = {
            "ORACLE": "VARCHAR2(100)",
            "POSTGRESQL": "TIMESTAMP WITH TIME ZONE",
            "MYSQL": "BIGINT UNSIGNED",
            "MSSQL": "UNIQUEIDENTIFIER",
        }

        directions_tested = 0
        for src in engines:
            for tgt in engines:
                if src == tgt:
                    continue
                raw_src = sample_types[src]
                emission = CanonicalTypeRegistry.convert_type(src, tgt, raw_src)
                self.assertIsInstance(emission, TargetTypeEmission)
                self.assertEqual(emission.target_engine, tgt)
                self.assertIsNotNone(emission.target_native_type)
                self.assertIn(emission.safety, list(ConversionSafety))
                directions_tested += 1

        self.assertEqual(directions_tested, 12)

    def test_06_compatibility_layer_delegation(self):
        """Verify CompatibilityLayer.map_datatype delegates to CanonicalTypeRegistry."""
        t_res = CompatibilityLayer.map_datatype(SystemType.ORACLE, SystemType.POSTGRESQL, "CLOB")
        self.assertEqual(t_res, "TEXT")

    def test_07_database_5_extensibility_proof(self):
        """Verify hypothetical Database #5 (IBM DB2) normalizes and emits types without core engine changes."""
        c_db2 = CanonicalTypeRegistry.normalize_source_type("IBM_DB2", "CLOB")
        self.assertEqual(c_db2.category, CanonicalTypeCategory.TEXT)

        emission = CanonicalTypeRegistry.emit_target_type("IBM_DB2", c_db2)
        self.assertEqual(emission.target_engine, "IBM_DB2")
        self.assertEqual(emission.target_native_type, "CLOB")
        self.assertEqual(emission.safety, ConversionSafety.EXACT)


if __name__ == "__main__":
    unittest.main()
