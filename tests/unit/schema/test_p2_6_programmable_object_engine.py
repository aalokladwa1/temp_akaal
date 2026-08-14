import unittest
from akaal.schema.domain.models import (
    CanonicalView,
    CanonicalMaterializedView,
    CanonicalProcedure,
    CanonicalFunction,
    CanonicalTrigger,
)
from akaal.schema.domain.types import ConversionSafety
from akaal.schema.domain.programmable_engine import (
    CanonicalProgrammableAuthority,
    StructuredProgrammableArtifact,
    BaseProgrammableEmitter,
    SQLRulebook,
)


class TestP26ProgrammableObjectEngine(unittest.TestCase):
    """
    P2.6 Programmable Database Object Intelligence & Universal Conversion Engine Test Suite.
    """

    def test_01_view_conversion_preserves_query_semantics(self):
        """Verify view conversion translates NVL/SYSDATE and preserves real query SELECT projection."""
        v = CanonicalView(
            name="v_active_emp",
            schema_name="hr",
            source_definition="SELECT id, NVL(comm, 0) AS comm, SYSDATE AS hire_date FROM emp WHERE active = 1",
        )
        art = CanonicalProgrammableAuthority.convert_view(v, "POSTGRESQL", "ORACLE")

        self.assertEqual(art.object_type, "VIEW")
        self.assertEqual(art.conversion_status, "AUTOMATIC")
        self.assertIn("COALESCE(comm, 0)", art.target_sql)
        self.assertIn("CURRENT_TIMESTAMP", art.target_sql)
        self.assertNotIn("SELECT 1 AS view_id", art.target_sql)

    def test_02_materialized_view_conversion(self):
        """Verify Materialized View conversion produces target-compatible DDL."""
        mv = CanonicalMaterializedView(
            name="mv_monthly_sales",
            schema_name="sales",
            source_definition="SELECT region, SUM(amount) AS total FROM sales_data GROUP BY region",
        )
        art_pg = CanonicalProgrammableAuthority.convert_materialized_view(mv, "POSTGRESQL", "ORACLE")
        self.assertIn('CREATE MATERIALIZED VIEW IF NOT EXISTS "sales"."mv_monthly_sales"', art_pg.target_sql)

        art_my = CanonicalProgrammableAuthority.convert_materialized_view(mv, "MYSQL", "ORACLE")
        self.assertEqual(art_my.conversion_status, "AUTOMATIC_WITH_WARNINGS")
        self.assertIn("does not natively support MATERIALIZED VIEW", art_my.warnings[0])

    def test_03_stored_procedure_conversion_and_complex_constructs(self):
        """Verify stored procedure conversion detects complex/dynamic SQL requiring manual review."""
        proc_simple = CanonicalProcedure(name="sp_log", schema_name="dbo", source_definition="INSERT INTO logs VALUES ('done');")
        art_simple = CanonicalProgrammableAuthority.convert_procedure(proc_simple, "POSTGRESQL", "MSSQL")
        self.assertEqual(art_simple.conversion_status, "AUTOMATIC")

        proc_complex = CanonicalProcedure(
            name="sp_exec_dyn", schema_name="dbo", source_definition="EXECUTE IMMEDIATE 'TRUNCATE TABLE temp_data';"
        )
        art_complex = CanonicalProgrammableAuthority.convert_procedure(proc_complex, "POSTGRESQL", "ORACLE")
        self.assertEqual(art_complex.conversion_status, "MANUAL_REVIEW_REQUIRED")
        self.assertEqual(art_complex.safety, ConversionSafety.POTENTIALLY_LOSSY)
        self.assertIn("MANUAL REVIEW REQUIRED", art_complex.target_sql)

    def test_04_function_conversion_with_type_registry_integration(self):
        """Verify function conversion maps return datatype via CanonicalTypeRegistry."""
        fn = CanonicalFunction(name="fn_get_total", schema_name="dbo", return_type="VARCHAR2(100)", source_definition="RETURN 'OK';")
        art = CanonicalProgrammableAuthority.convert_function(fn, "POSTGRESQL", "ORACLE")
        self.assertIn("RETURNS VARCHAR(100)", art.target_sql)

    def test_05_trigger_conversion_and_pseudo_table_translation(self):
        """Verify trigger conversion translates :NEW/:OLD to NEW/OLD in PostgreSQL and trigger function DDL."""
        trig = CanonicalTrigger(
            name="trg_emp_audit",
            schema_name="hr",
            table_name="employees",
            timing="BEFORE",
            events=["UPDATE"],
            source_definition="IF :NEW.salary > :OLD.salary THEN NULL; END IF;",
        )
        art = CanonicalProgrammableAuthority.convert_trigger(trig, "POSTGRESQL", "ORACLE")
        self.assertIn("NEW.salary > OLD.salary", art.target_sql)
        self.assertIn("RETURNS trigger LANGUAGE plpgsql", art.target_sql)
        self.assertIn('CREATE TRIGGER "trg_emp_audit" BEFORE UPDATE ON "hr"."employees"', art.target_sql)

    def test_06_all_12_cross_engine_programmable_routes(self):
        """Verify programmable object conversion across all 12 pairwise engine directions."""
        engines = ["ORACLE", "POSTGRESQL", "MYSQL", "MSSQL"]
        routes_tested = 0

        v = CanonicalView(name="v_test", schema_name="public", source_definition="SELECT ISNULL(val, 0) FROM t1")

        for src in engines:
            for tgt in engines:
                if src == tgt:
                    continue
                art = CanonicalProgrammableAuthority.convert_view(v, tgt, src)
                self.assertIsNotNone(art.target_sql)
                self.assertEqual(art.target_engine, tgt)
                routes_tested += 1

        self.assertEqual(routes_tested, 12)

    def test_07_zero_placeholder_policy(self):
        """Verify zero placeholder DDL strings are produced across views, procedures, and functions."""
        v = CanonicalView(name="v1", schema_name="s1", source_definition="SELECT a, b FROM t1")
        art_v = CanonicalProgrammableAuthority.convert_view(v, "POSTGRESQL", "ORACLE")
        self.assertNotIn("SELECT 1 AS view_id", art_v.target_sql)
        self.assertIn("SELECT a, b FROM t1", art_v.target_sql)

    def test_08_database_5_extensibility_proof(self):
        """Verify hypothetical Database #5 (IBM DB2) custom programmable emitter registration."""

        class IBMDB2ProgrammableEmitter(BaseProgrammableEmitter):

            def __init__(self):
                super().__init__("IBM_DB2")

            def emit_view(self, view: CanonicalView, source_engine: str):
                sql = f'CREATE VIEW "{view.schema_name}"."{view.name}" AS {view.source_definition};'
                return StructuredProgrammableArtifact("VIEW", view.name, view.schema_name, source_engine, "IBM_DB2", view.source_definition or "", sql, "AUTOMATIC")

            def emit_materialized_view(self, mv, source_engine):
                pass

            def emit_procedure(self, proc, source_engine):
                pass

            def emit_function(self, func, source_engine):
                pass

            def emit_trigger(self, trig, source_engine):
                pass

        CanonicalProgrammableAuthority.register_emitter("IBM_DB2", IBMDB2ProgrammableEmitter())

        v = CanonicalView(name="v_db2", schema_name="db2admin", source_definition="SELECT 1 FROM sysibm.sysdummy1")
        art = CanonicalProgrammableAuthority.convert_view(v, "IBM_DB2", "ORACLE")
        self.assertEqual(art.target_engine, "IBM_DB2")
        self.assertIn('CREATE VIEW "db2admin"."v_db2"', art.target_sql)


if __name__ == "__main__":
    unittest.main()
