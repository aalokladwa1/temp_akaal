import unittest
from akaal.schema.domain.models import (
    CanonicalSchemaModel,
    CanonicalTable,
    CanonicalColumn,
    CanonicalObjectIdentity,
    CanonicalPrimaryKey,
    CanonicalForeignKey,
    CanonicalUniqueConstraint,
    CanonicalCheckConstraint,
    CanonicalIndex,
)
from akaal.schema.domain.ddl_emitter import (
    UniversalDDLAuthority,
    StructuredDDLArtifact,
    BaseTargetDDLEmitter,
    PostgreSQLDDLEmitter,
    OracleDDLEmitter,
    MySQLDDLEmitter,
    MSSQLDDLEmitter,
)
from akaal.schema.domain.type_registry import CanonicalTypeRegistry


class TestP24StructuralDDLEmitters(unittest.TestCase):
    """
    P2.4 Structural Object DDL Emitters & Universal Target DDL Architecture Test Suite.
    """

    def setUp(self):
        # Construct a representative CanonicalTable with Composite PK, FK, Unique Constraint, Check Constraint, Index
        ident = CanonicalObjectIdentity(schema_name="sales", object_name="orders")
        col1 = CanonicalColumn(name="order_id", ordinal_position=1, source_native_type="BIGINT", is_identity=True, nullable=False)
        col2 = CanonicalColumn(name="cust_id", ordinal_position=2, source_native_type="INT", nullable=False)
        col3 = CanonicalColumn(name="total_amt", ordinal_position=3, source_native_type="DECIMAL(10,2)", nullable=True)

        pk = CanonicalPrimaryKey(table_name="orders", column_names=["order_id", "cust_id"], name="pk_orders")
        fk = CanonicalForeignKey(
            table_name="orders",
            column_names=["cust_id"],
            referenced_schema="sales",
            referenced_table="customers",
            referenced_columns=["cust_id"],
            name="fk_orders_cust",
        )
        uc = CanonicalUniqueConstraint(table_name="orders", column_names=["order_id"], name="uq_order_id")
        cc = CanonicalCheckConstraint(table_name="orders", check_clause="total_amt >= 0", name="chk_total_amt")
        idx = CanonicalIndex(name="idx_orders_cust", table_name="orders", column_names=["cust_id"], is_unique=False)

        self.sample_table = CanonicalTable(
            identity=ident,
            columns=[col1, col2, col3],
            primary_key=pk,
            foreign_keys=[fk],
            unique_constraints=[uc],
            check_constraints=[cc],
            indexes=[idx],
        )

    def test_01_postgresql_ddl_emission(self):
        """Verify PostgreSQL target DDL emission for table, PK, FK, UC, CC, and Index."""
        artifacts = UniversalDDLAuthority.emit_table_ddl(self.sample_table, "POSTGRESQL")
        self.assertGreaterEqual(len(artifacts), 6)

        types = [a.object_type for a in artifacts]
        self.assertIn("TABLE", types)
        self.assertIn("PRIMARY_KEY", types)
        self.assertIn("FOREIGN_KEY", types)
        self.assertIn("UNIQUE_CONSTRAINT", types)
        self.assertIn("CHECK_CONSTRAINT", types)
        self.assertIn("INDEX", types)

        tbl_art = next(a for a in artifacts if a.object_type == "TABLE")
        self.assertIn('CREATE TABLE IF NOT EXISTS "sales"."orders"', tbl_art.sql)
        self.assertIn('GENERATED ALWAYS AS IDENTITY', tbl_art.sql)

        pk_art = next(a for a in artifacts if a.object_type == "PRIMARY_KEY")
        self.assertIn('PRIMARY KEY ("order_id", "cust_id")', pk_art.sql)

    def test_02_oracle_ddl_emission(self):
        """Verify Oracle target DDL emission with uppercase quoted identifiers."""
        artifacts = UniversalDDLAuthority.emit_table_ddl(self.sample_table, "ORACLE")
        tbl_art = next(a for a in artifacts if a.object_type == "TABLE")
        self.assertIn('CREATE TABLE "SALES"."ORDERS"', tbl_art.sql)
        self.assertIn('GENERATED ALWAYS AS IDENTITY', tbl_art.sql)

    def test_03_mysql_ddl_emission(self):
        """Verify MySQL target DDL emission with backtick identifiers and InnoDB engine."""
        artifacts = UniversalDDLAuthority.emit_table_ddl(self.sample_table, "MYSQL")
        tbl_art = next(a for a in artifacts if a.object_type == "TABLE")
        self.assertIn('CREATE TABLE IF NOT EXISTS `sales`.`orders`', tbl_art.sql)
        self.assertIn('AUTO_INCREMENT', tbl_art.sql)
        self.assertIn('ENGINE=InnoDB', tbl_art.sql)

    def test_04_mssql_ddl_emission(self):
        """Verify MSSQL target DDL emission with bracket identifiers and IDENTITY."""
        artifacts = UniversalDDLAuthority.emit_table_ddl(self.sample_table, "MSSQL")
        tbl_art = next(a for a in artifacts if a.object_type == "TABLE")
        self.assertIn('CREATE TABLE [sales].[orders]', tbl_art.sql)
        self.assertIn('IDENTITY(1,1)', tbl_art.sql)

    def test_05_all_12_cross_engine_structural_routes(self):
        """Verify structural DDL generation across all 12 non-self database target directions."""
        engines = ["ORACLE", "POSTGRESQL", "MYSQL", "MSSQL"]
        routes_tested = 0

        for src in engines:
            # Build canonical table derived from source engine
            c_model = CanonicalTypeRegistry.normalize_source_type(src, "BIGINT")
            col = CanonicalColumn(name="id", ordinal_position=1, source_native_type="BIGINT", canonical_type_model=c_model)
            tbl = CanonicalTable(identity=CanonicalObjectIdentity(schema_name="public", object_name="t1"), columns=[col])

            for tgt in engines:
                if src == tgt:
                    continue
                artifacts = UniversalDDLAuthority.emit_table_ddl(tbl, tgt, src)
                self.assertTrue(len(artifacts) > 0)
                self.assertEqual(artifacts[0].target_engine, tgt)
                routes_tested += 1

        self.assertEqual(routes_tested, 12)

    def test_06_ddl_emission_determinism(self):
        """Verify target DDL generation is 100% deterministic across repeated runs."""
        arts1 = UniversalDDLAuthority.emit_table_ddl(self.sample_table, "POSTGRESQL")
        arts2 = UniversalDDLAuthority.emit_table_ddl(self.sample_table, "POSTGRESQL")

        sqls1 = [a.sql for a in arts1]
        sqls2 = [a.sql for a in arts2]
        self.assertEqual(sqls1, sqls2)

    def test_07_database_5_extensibility_proof(self):
        """Verify hypothetical Database #5 (IBM DB2) can register custom target DDL emitter dynamically."""

        class IBMDB2DDLEmitter(BaseTargetDDLEmitter):

            def __init__(self):
                super().__init__("IBM_DB2")

            def quote_identifier(self, name: str) -> str:
                return f'"{name.upper()}"'

            def emit_column_definition(self, col: CanonicalColumn, source_engine: str = "GENERIC"):
                return f'"{col.name.upper()}" VARCHAR(255)', ConversionSafety.EXACT, []

            def emit_table_artifacts(self, table: CanonicalTable, source_engine: str = "GENERIC"):
                s_name = table.identity.schema_name
                t_name = table.identity.object_name
                sql = f'CREATE TABLE "{s_name.upper()}"."{t_name.upper()}" ("ID" BIGINT NOT NULL);'
                return [StructuredDDLArtifact("TABLE", t_name, s_name, sql, "IBM_DB2")]

        UniversalDDLAuthority.register_emitter("IBM_DB2", IBMDB2DDLEmitter())

        artifacts = UniversalDDLAuthority.emit_table_ddl(self.sample_table, "IBM_DB2")
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0].target_engine, "IBM_DB2")
        self.assertIn('CREATE TABLE "SALES"."ORDERS"', artifacts[0].sql)


if __name__ == "__main__":
    unittest.main()
