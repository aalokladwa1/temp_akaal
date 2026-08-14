import unittest
import asyncio
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
    CanonicalSequence,
    CanonicalIdentity,
    CanonicalPartition,
    CanonicalView,
    CanonicalProcedure,
    CanonicalFunction,
    CanonicalTrigger,
)
from akaal.adapters.rdbms.oracle_adapter import OracleAdapter
from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
from akaal.adapters.rdbms.mysql_adapter import MySQLAdapter
from akaal.adapters.rdbms.mssql_adapter import MSSQLAdapter
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType


class TestP22CanonicalSchemaModel(unittest.TestCase):
    """
    P2.2 Canonical Schema Model & Universal Metadata Normalization Test Suite.
    """

    def test_01_canonical_table_and_column_construction(self):
        """Verify strongly-typed canonical table and column construction."""
        identity = CanonicalObjectIdentity(
            schema_name="HR",
            object_name="EMPLOYEES",
            object_type="TABLE",
            catalog="PRODDB",
            quoted_identifier='"HR"."EMPLOYEES"',
        )
        col1 = CanonicalColumn(name="emp_id", ordinal_position=1, source_native_type="NUMBER(10)", is_primary_key=True, nullable=False)
        col2 = CanonicalColumn(name="email", ordinal_position=2, source_native_type="VARCHAR2(100)", nullable=True)

        pk = CanonicalPrimaryKey(table_name="EMPLOYEES", column_names=["emp_id"], name="pk_emp")

        table = CanonicalTable(identity=identity, columns=[col1, col2], primary_key=pk)
        model = CanonicalSchemaModel(schema_name="HR", engine="ORACLE")
        model.add_table(table)

        self.assertIn("employees", model.tables)
        tbl_ret = model.get_table("EMPLOYEES")
        self.assertIsNotNone(tbl_ret)
        self.assertEqual(len(tbl_ret.columns), 2)
        self.assertEqual(tbl_ret.primary_key.column_names, ["emp_id"])

    def test_02_deterministic_schema_serialization_and_fingerprint(self):
        """Verify schema to_dict() serialization and SHA-256 fingerprinting are deterministic."""
        model1 = CanonicalSchemaModel(schema_name="sales", engine="POSTGRESQL")
        id1 = CanonicalObjectIdentity(schema_name="sales", object_name="orders")
        t1 = CanonicalTable(identity=id1, columns=[CanonicalColumn(name="id", ordinal_position=1, source_native_type="INT")])
        model1.add_table(t1)

        model2 = CanonicalSchemaModel(schema_name="sales", engine="POSTGRESQL")
        id2 = CanonicalObjectIdentity(schema_name="sales", object_name="orders")
        t2 = CanonicalTable(identity=id2, columns=[CanonicalColumn(name="id", ordinal_position=1, source_native_type="INT")])
        model2.add_table(t2)

        fp1 = model1.compute_schema_fingerprint()
        fp2 = model2.compute_schema_fingerprint()

        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64)  # SHA-256 hex string

    def test_03_four_adapters_expose_get_canonical_schema(self):
        """Verify Oracle, PostgreSQL, MySQL, and MSSQL adapters expose get_canonical_schema."""
        loop = asyncio.new_event_loop()
        try:
            ora_cfg = ConnectionConfig(system_type=SystemType.ORACLE, host="127.0.0.1", port=1521, database_name="db", credentials_ref="cred-ref", extra={"mock_mode": True})
            ora_ad = OracleAdapter(ora_cfg)
            ora_model = loop.run_until_complete(ora_ad.get_canonical_schema("HR"))
            self.assertIsInstance(ora_model, CanonicalSchemaModel)
            self.assertEqual(ora_model.engine, "ORACLE")

            pg_cfg = ConnectionConfig(system_type=SystemType.POSTGRESQL, host="127.0.0.1", port=5432, database_name="db", credentials_ref="cred-ref", extra={"mock_mode": True})
            pg_ad = PostgreSQLAdapter(pg_cfg)
            pg_model = loop.run_until_complete(pg_ad.get_canonical_schema("public"))
            self.assertIsInstance(pg_model, CanonicalSchemaModel)
            self.assertEqual(pg_model.engine, "POSTGRESQL")

            my_cfg = ConnectionConfig(system_type=SystemType.MYSQL, host="127.0.0.1", port=3306, database_name="db", credentials_ref="cred-ref", extra={"mock_mode": True})
            my_ad = MySQLAdapter(my_cfg)
            my_model = loop.run_until_complete(my_ad.get_canonical_schema("crm"))
            self.assertIsInstance(my_model, CanonicalSchemaModel)
            self.assertEqual(my_model.engine, "MYSQL")

            ms_cfg = ConnectionConfig(system_type=SystemType.MSSQL, host="127.0.0.1", port=1433, database_name="db", credentials_ref="cred-ref", extra={"mock_mode": True})
            ms_ad = MSSQLAdapter(ms_cfg)
            ms_model = loop.run_until_complete(ms_ad.get_canonical_schema("dbo"))
            self.assertIsInstance(ms_model, CanonicalSchemaModel)
            self.assertEqual(ms_model.engine, "MSSQL")
        finally:
            loop.close()

    def test_04_identifier_preservation(self):
        """Verify catalog, schema, object_name, quoted, and normalized identifiers are preserved."""
        ident = CanonicalObjectIdentity(
            schema_name="Sales",
            object_name="Customers",
            object_type="TABLE",
            catalog="DB_PROD",
            quoted_identifier='[Sales].[Customers]',
        )
        self.assertEqual(ident.schema_name, "Sales")
        self.assertEqual(ident.object_name, "Customers")
        self.assertEqual(ident.normalized_identifier, "sales.customers")
        self.assertEqual(ident.quoted_identifier, '[Sales].[Customers]')


if __name__ == "__main__":
    unittest.main()
