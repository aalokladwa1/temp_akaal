import unittest
from akaal.schema.domain.models import (
    CanonicalSchemaModel,
    CanonicalTable,
    CanonicalColumn,
    CanonicalObjectIdentity,
    CanonicalView,
    CanonicalProcedure,
)
from akaal.schema.domain.type_registry import CanonicalTypeRegistry
from akaal.schema.compatibility.comparison_engine import (
    CanonicalSchemaComparator,
    CanonicalRiskScorer,
    CanonicalDriftAnalyzer,
    SchemaDifference,
    RiskAssessment,
    SchemaDriftReport,
    DifferenceCategory,
    CompatibilityClassification,
    RiskSeverity,
    DriftClassification,
)


class TestP27SchemaCompatibilityRiskDrift(unittest.TestCase):
    """
    P2.7 Schema Comparison, Compatibility Intelligence, Risk Scoring & Drift Analysis Test Suite.
    """

    def setUp(self):
        # Build baseline CanonicalSchemaModel
        self.m1 = CanonicalSchemaModel(schema_name="sales", engine="ORACLE")
        id1 = CanonicalObjectIdentity(schema_name="sales", object_name="customers")
        c1 = CanonicalColumn(
            name="id",
            ordinal_position=1,
            source_native_type="NUMBER(10,0)",
            canonical_type_model=CanonicalTypeRegistry.normalize_source_type("ORACLE", "NUMBER(10,0)"),
        )
        c2 = CanonicalColumn(
            name="name",
            ordinal_position=2,
            source_native_type="VARCHAR2(100)",
            canonical_type_model=CanonicalTypeRegistry.normalize_source_type("ORACLE", "VARCHAR2(100)"),
        )
        self.m1.add_table(CanonicalTable(identity=id1, columns=[c1, c2]))

    def test_01_identical_schemas_produce_zero_differences(self):
        """Verify identical CanonicalSchemaModels yield zero differences and 0 risk score."""
        diffs = CanonicalSchemaComparator.compare_schemas(self.m1, self.m1)
        self.assertEqual(len(diffs), 0)

        risk = CanonicalRiskScorer.evaluate_risk(diffs)
        self.assertEqual(risk.risk_score, 0)
        self.assertTrue(risk.is_safe_to_continue)

    def test_02_detect_table_additions_and_removals(self):
        """Verify missing source table in target is detected as REMOVED difference."""
        m2 = CanonicalSchemaModel(schema_name="sales", engine="POSTGRESQL")  # Empty target model

        diffs = CanonicalSchemaComparator.compare_schemas(self.m1, m2)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].category, DifferenceCategory.REMOVED)
        self.assertEqual(diffs[0].object_name, "customers")

    def test_03_detect_column_datatype_mismatch(self):
        """Verify column datatype mismatch (e.g. INTEGER vs VARCHAR) is detected."""
        m2 = CanonicalSchemaModel(schema_name="sales", engine="POSTGRESQL")
        id2 = CanonicalObjectIdentity(schema_name="sales", object_name="customers")
        c1 = CanonicalColumn(
            name="id",
            ordinal_position=1,
            source_native_type="VARCHAR(100)",
            canonical_type_model=CanonicalTypeRegistry.normalize_source_type("POSTGRESQL", "VARCHAR(100)"),
        )
        c2 = CanonicalColumn(
            name="name",
            ordinal_position=2,
            source_native_type="VARCHAR(100)",
            canonical_type_model=CanonicalTypeRegistry.normalize_source_type("POSTGRESQL", "VARCHAR(100)"),
        )
        m2.add_table(CanonicalTable(identity=id2, columns=[c1, c2]))

        diffs = CanonicalSchemaComparator.compare_schemas(self.m1, m2)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].category, DifferenceCategory.TYPE_CHANGED)
        self.assertEqual(diffs[0].property_name, "id")

    def test_04_explainable_risk_scoring_and_breakdown(self):
        """Verify RiskAssessment computes deterministic risk_score (0..100) and category breakdown."""
        diff1 = SchemaDifference(
            difference_id="d1",
            object_type="TABLE",
            schema_name="sales",
            object_name="orders",
            category=DifferenceCategory.REMOVED,
            severity=RiskSeverity.HIGH,
        )
        diff2 = SchemaDifference(
            difference_id="d2",
            object_type="COLUMN",
            schema_name="sales",
            object_name="customers",
            category=DifferenceCategory.TYPE_CHANGED,
            property_name="sal",
            severity=RiskSeverity.MEDIUM,
        )

        risk = CanonicalRiskScorer.evaluate_risk([diff1, diff2], "ORACLE", "POSTGRESQL")
        self.assertEqual(risk.risk_score, 40)
        self.assertIn("STRUCTURAL", risk.breakdown)
        self.assertIn("DATATYPE", risk.breakdown)

    def test_05_deterministic_schema_drift_analysis(self):
        """Verify CanonicalDriftAnalyzer detects drift using SHA-256 schema fingerprints."""
        m2 = CanonicalSchemaModel(schema_name="sales", engine="ORACLE")
        id2 = CanonicalObjectIdentity(schema_name="sales", object_name="customers")
        c1 = CanonicalColumn(
            name="id",
            ordinal_position=1,
            source_native_type="NUMBER(10,0)",
            canonical_type_model=CanonicalTypeRegistry.normalize_source_type("ORACLE", "NUMBER(10,0)"),
        )
        m2.add_table(CanonicalTable(identity=id2, columns=[c1]))  # Column 'name' removed in m2

        report = CanonicalDriftAnalyzer.analyze_drift(self.m1, m2)
        self.assertTrue(report.is_drift_detected)
        self.assertNotEqual(report.source_fingerprint, report.target_fingerprint)
        self.assertEqual(report.drift_classification, DriftClassification.BREAKING_DRIFT)

    def test_06_all_12_cross_engine_assessment_routes(self):
        """Verify assessment routes across all 12 pairwise engine combinations."""
        engines = ["ORACLE", "POSTGRESQL", "MYSQL", "MSSQL"]
        routes_tested = 0

        for src in engines:
            for tgt in engines:
                if src == tgt:
                    continue
                diffs = CanonicalSchemaComparator.compare_schemas(self.m1, self.m1)
                risk = CanonicalRiskScorer.evaluate_risk(diffs, src, tgt)
                self.assertIsNotNone(risk)
                routes_tested += 1

        self.assertEqual(routes_tested, 12)

    def test_07_database_5_extensibility_proof(self):
        """Verify hypothetical Database #5 (IBM DB2) schema models compare cleanly without core engine changes."""
        db2_model = CanonicalSchemaModel(schema_name="sales", engine="IBM_DB2")
        id_db2 = CanonicalObjectIdentity(schema_name="sales", object_name="customers")
        c1 = CanonicalColumn(
            name="id",
            ordinal_position=1,
            source_native_type="INTEGER",
            canonical_type_model=CanonicalTypeRegistry.normalize_source_type("IBM_DB2", "INTEGER"),
        )
        db2_model.add_table(CanonicalTable(identity=id_db2, columns=[c1]))

        diffs = CanonicalSchemaComparator.compare_schemas(self.m1, db2_model)
        self.assertGreater(len(diffs), 0)


if __name__ == "__main__":
    unittest.main()
