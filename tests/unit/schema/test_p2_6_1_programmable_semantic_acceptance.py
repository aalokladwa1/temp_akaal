import unittest
from akaal.schema.domain.models import CanonicalView, CanonicalProcedure, CanonicalTrigger
from akaal.schema.domain.programmable_engine import (
    CanonicalProgrammableAuthority,
    StructuredProgrammableArtifact,
    SQLRulebook,
)


class TestP261ProgrammableSemanticAcceptance(unittest.TestCase):
    """
    P2.6.1 Final Programmable-Object Semantic Acceptance & Hardening Test Suite.
    """

    def test_01_lexical_safe_masking_literals_and_comments(self):
        """Verify string literals and comments containing NVL/SYSDATE are NOT corrupted by SQLRulebook."""
        sql_with_literals = "SELECT 'NVL(val)' AS str_lit, NVL(comm, 0) AS actual_comm FROM emp; -- SYSDATE comment"
        translated, warnings = SQLRulebook.translate_expressions(sql_with_literals, "ORACLE", "POSTGRESQL")

        self.assertIn("'NVL(val)'", translated)  # Literal string untouched!
        self.assertIn("COALESCE(comm, 0)", translated)  # Actual NVL function converted!
        self.assertIn("-- SYSDATE comment", translated)  # Comment untouched!

    def test_02_execution_firewall_blocks_manual_review_artifacts(self):
        """Verify artifacts requiring manual review or unsupported constructs are NOT auto-executable."""
        proc_complex = CanonicalProcedure(
            name="sp_complex", schema_name="dbo", source_definition="EXECUTE IMMEDIATE 'DROP TABLE t1';"
        )
        art = CanonicalProgrammableAuthority.convert_procedure(proc_complex, "POSTGRESQL", "ORACLE")

        self.assertEqual(art.conversion_status, "MANUAL_REVIEW_REQUIRED")
        self.assertFalse(art.is_auto_executable)

    def test_03_mssql_inserted_deleted_set_semantics_warning(self):
        """Verify MSSQL INSERTED/DELETED triggers emit explicit multi-row warning & manual review status."""
        trig = CanonicalTrigger(
            name="trg_orders", schema_name="dbo", table_name="orders", timing="AFTER", events=["INSERT"], source_definition="SELECT * FROM INSERTED;"
        )
        art = CanonicalProgrammableAuthority.convert_trigger(trig, "POSTGRESQL", "MSSQL")

        self.assertEqual(art.conversion_status, "MANUAL_REVIEW_REQUIRED")
        self.assertFalse(art.is_auto_executable)
        self.assertIn("MSSQL INSERTED/DELETED pseudo-tables are set-oriented", art.warnings[0])

    def test_04_deterministic_source_and_conversion_fingerprints(self):
        """Verify SHA-256 source and conversion fingerprints are deterministic."""
        v = CanonicalView(name="v1", schema_name="s1", source_definition="SELECT a FROM t1")
        art1 = CanonicalProgrammableAuthority.convert_view(v, "POSTGRESQL", "ORACLE")
        art2 = CanonicalProgrammableAuthority.convert_view(v, "POSTGRESQL", "ORACLE")

        self.assertEqual(art1.source_fingerprint, art2.source_fingerprint)
        self.assertEqual(art1.conversion_fingerprint, art2.conversion_fingerprint)
        self.assertTrue(len(art1.source_fingerprint) == 64)


if __name__ == "__main__":
    unittest.main()
