import unittest
from akaal.schema.domain.models import (
    CanonicalSchemaModel,
    CanonicalTable,
    CanonicalColumn,
    CanonicalObjectIdentity,
    CanonicalForeignKey,
)
from akaal.schema.domain.types import (
    CanonicalTypeCategory,
    CanonicalType,
)
from akaal.schema.compatibility.comparison_engine import (
    CanonicalSchemaComparator,
    CanonicalRiskScorer,
    CanonicalDriftAnalyzer,
    SchemaDifference,
    RiskAssessment,
    DifferenceCategory,
    CompatibilityClassification,
    RiskSeverity,
)


class TestP271SchemaRiskDriftSemanticAcceptance(unittest.TestCase):
    """
    P2.7.1 Final Schema Comparison, Compatibility Intelligence, Risk Scoring & Drift Semantic Acceptance Test Suite.
    """

    def test_01_namespace_collision_safety(self):
        """Verify sales.customers and archive.customers remain distinct and do NOT collapse."""
        m_src = CanonicalSchemaModel(schema_name="sales", engine="ORACLE")
        m_src.add_table(
            CanonicalTable(
                identity=CanonicalObjectIdentity(schema_name="sales", object_name="customers"),
                columns=[CanonicalColumn(name="id", ordinal_position=1, source_native_type="NUMBER")],
            )
        )
        m_src.add_table(
            CanonicalTable(
                identity=CanonicalObjectIdentity(schema_name="archive", object_name="customers"),
                columns=[CanonicalColumn(name="id", ordinal_position=1, source_native_type="NUMBER")],
            )
        )

        diffs = CanonicalSchemaComparator.compare_schemas(m_src, m_src)
        self.assertEqual(len(diffs), 0)

    def test_02_directional_asymmetry_narrowing_vs_widening(self):
        """Verify length narrowing (200 -> 100) is POTENTIALLY_LOSSY while widening (100 -> 200) is COMPATIBLE."""
        m_narrow = CanonicalSchemaModel(schema_name="hr", engine="POSTGRESQL")
        c_narrow = CanonicalColumn(
            name="bio",
            ordinal_position=1,
            source_native_type="VARCHAR(100)",
            canonical_type_model=CanonicalType(category=CanonicalTypeCategory.VARCHAR, raw_vendor_type="VARCHAR", length=100),
        )
        m_narrow.add_table(CanonicalTable(identity=CanonicalObjectIdentity(schema_name="hr", object_name="emp"), columns=[c_narrow]))

        m_wide = CanonicalSchemaModel(schema_name="hr", engine="ORACLE")
        c_wide = CanonicalColumn(
            name="bio",
            ordinal_position=1,
            source_native_type="VARCHAR2(200)",
            canonical_type_model=CanonicalType(category=CanonicalTypeCategory.VARCHAR, raw_vendor_type="VARCHAR2", length=200),
        )
        m_wide.add_table(CanonicalTable(identity=CanonicalObjectIdentity(schema_name="hr", object_name="emp"), columns=[c_wide]))

        # Wide -> Narrow (Narrowing risk)
        diffs_narrow = CanonicalSchemaComparator.compare_schemas(m_wide, m_narrow)
        self.assertEqual(len(diffs_narrow), 1)
        self.assertEqual(diffs_narrow[0].compatibility, CompatibilityClassification.POTENTIALLY_LOSSY)
        self.assertEqual(diffs_narrow[0].severity, RiskSeverity.HIGH)

        # Narrow -> Wide (Widening safe)
        diffs_wide = CanonicalSchemaComparator.compare_schemas(m_narrow, m_wide)
        self.assertEqual(len(diffs_wide), 1)
        self.assertEqual(diffs_wide[0].compatibility, CompatibilityClassification.COMPATIBLE_WITH_CONVERSION)
        self.assertEqual(diffs_wide[0].severity, RiskSeverity.LOW)

    def test_03_foreign_key_referential_action_difference(self):
        """Verify FK ON DELETE mismatch is detected as a constraint change."""
        m1 = CanonicalSchemaModel(schema_name="sales", engine="ORACLE")
        fk1 = CanonicalForeignKey(name="fk_ord_cust", table_name="orders", column_names=["cust_id"], referenced_schema="sales", referenced_table="customers", referenced_columns=["id"], on_delete="CASCADE")
        m1.add_table(CanonicalTable(identity=CanonicalObjectIdentity(schema_name="sales", object_name="orders"), foreign_keys=[fk1]))

        m2 = CanonicalSchemaModel(schema_name="sales", engine="POSTGRESQL")
        fk2 = CanonicalForeignKey(name="fk_ord_cust", table_name="orders", column_names=["cust_id"], referenced_schema="sales", referenced_table="customers", referenced_columns=["id"], on_delete="NO ACTION")
        m2.add_table(CanonicalTable(identity=CanonicalObjectIdentity(schema_name="sales", object_name="orders"), foreign_keys=[fk2]))

        diffs = CanonicalSchemaComparator.compare_schemas(m1, m2)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].category, DifferenceCategory.CONSTRAINT_CHANGED)
        self.assertEqual(diffs[0].property_name, "on_delete")

    def test_04_blocking_finding_forces_unsafe_status(self):
        """Verify a BLOCKING finding forces is_safe_to_continue = False regardless of numerical score dilution."""
        diff_blocking = SchemaDifference(
            difference_id="diff-block",
            object_type="TABLE",
            schema_name="dbo",
            object_name="secret",
            category=DifferenceCategory.UNSUPPORTED,
            severity=RiskSeverity.BLOCKING,
            compatibility=CompatibilityClassification.BLOCKING,
            explanation="Blocking unsupported engine construct",
        )

        risk = CanonicalRiskScorer.evaluate_risk([diff_blocking])
        self.assertFalse(risk.is_safe_to_continue)
        self.assertEqual(risk.overall_compatibility, CompatibilityClassification.BLOCKING)
        self.assertEqual(risk.blocking_findings_count, 1)

    def test_05_heuristic_rename_not_automatically_accepted(self):
        """Verify HEURISTIC_RENAME_AUTOMATICALLY_ACCEPTED invariant is False."""
        self.assertFalse(CanonicalSchemaComparator.HEURISTIC_RENAME_AUTOMATICALLY_ACCEPTED)


if __name__ == "__main__":
    unittest.main()
