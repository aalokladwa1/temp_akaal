import unittest
import asyncio
from typing import Dict, Any, Tuple
from akaal.core.models.enums import SystemType
from akaal.migration.models import (
    ObjectType,
    OperationType,
    Table,
    Column,
    Constraint,
    Index,
    View,
    Sequence,
    Trigger,
    MigrationOperation,
    MigrationPlan,
    DDLCommand
)
from akaal.migration.ddl import (
    BaseDDLGenerator,
    PostgreSQLDDLGenerator,
    MySQLDDLGenerator,
    OracleDDLGenerator,
    SQLServerDDLGenerator,
    DDLGeneratorRegistry
)
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry
from akaal.migration.ddl.utilities.quoting import IdentifierQuoter
from akaal.migration.ddl.utilities.capabilities import DialectCapabilities
from akaal.migration.ddl.utilities.builder import SQLBuilder
from akaal.migration.ddl.utilities.formatter import SQLFormatter
from akaal.migration.execution.batching import TransactionBatcher

class TestDDLTranslationEngine(unittest.TestCase):
    def test_translation_result_immutability(self):
        """Verify TranslationResult cannot be modified after construction."""
        res = TranslationResult(sql="CREATE", rollback_sql="DROP", warnings=("warn",), metadata={"a": 1})
        self.assertEqual(res.sql, "CREATE")
        self.assertEqual(res.metadata, {"a": 1})
        with self.assertRaises(Exception):
            res.sql = "OTHER"  # type: ignore

    def test_object_translator_registry_validation(self):
        """Verify validation and inheritance rules in ObjectTranslatorRegistry."""
        # Temporarily pop ObjectType.SEQUENCE to safely test validation on a clean key
        old_trans = ObjectTranslatorRegistry._registry.pop(ObjectType.SEQUENCE, None)
        try:
            class BadTranslator:
                pass

            with self.assertRaises(TypeError):
                ObjectTranslatorRegistry.register(ObjectType.SEQUENCE, BadTranslator())  # type: ignore

            # Registering translator for object type it doesn't list support for
            class TableTranslatorNoTable(BaseObjectTranslator):
                SUPPORTED_OBJECTS = set()
                SUPPORTED_OPERATIONS = {OperationType.CREATE}
                def translate_create(self, obj, context, quoter, capabilities, builder): return TranslationResult("")
                def translate_drop(self, obj, context, quoter, capabilities, builder): return TranslationResult("")
                def translate_alter(self, obj, context, quoter, capabilities, builder): return TranslationResult("")

            with self.assertRaises(ValueError):
                ObjectTranslatorRegistry.register(ObjectType.SEQUENCE, TableTranslatorNoTable())
        finally:
            if old_trans:
                ObjectTranslatorRegistry._registry[ObjectType.SEQUENCE] = old_trans

    def test_object_translator_registry_duplicate_prevention(self):
        """Verify ObjectTranslatorRegistry raises error on duplicate registrations."""
        translator = ObjectTranslatorRegistry.get_translator(ObjectType.TABLE)
        with self.assertRaises(ValueError):
            ObjectTranslatorRegistry.register(ObjectType.TABLE, translator)

    def test_ddl_generator_registry_duplicate_prevention(self):
        """Verify DDLGeneratorRegistry raises error on duplicate registrations."""
        with self.assertRaises(ValueError):
            DDLGeneratorRegistry.register(SystemType.POSTGRESQL, PostgreSQLDDLGenerator)

    def test_quoting_vendor_variants(self):
        """Verify IdentifierQuoter quotes paths, handles unicode and keywords correctly."""
        pq_quoter = IdentifierQuoter.postgresql()
        my_quoter = IdentifierQuoter.mysql()
        or_quoter = IdentifierQuoter.oracle()
        ss_quoter = IdentifierQuoter.sqlserver()

        # Dotted paths
        self.assertEqual(pq_quoter.quote("public.users"), '"public"."users"')
        self.assertEqual(my_quoter.quote("public.users"), '`public`.`users`')
        self.assertEqual(or_quoter.quote("public.users"), '"PUBLIC"."USERS"')
        self.assertEqual(ss_quoter.quote("public.users"), '[public].[users]')

        # Unicode
        self.assertEqual(pq_quoter.quote("users_äöü"), '"users_äöü"')

        # Reserved keywords
        self.assertEqual(ss_quoter.quote("select"), '[select]')

    def test_sql_builder_vendor_agnostic(self):
        """Verify SQLBuilder assembles standard templates without vendor specifics."""
        builder = SQLBuilder()
        self.assertEqual(builder.build_drop_table("users"), "DROP TABLE users")
        self.assertEqual(builder.build_create_view("v_users", "SELECT 1"), "CREATE VIEW v_users AS SELECT 1")

    def test_placeholder_translators(self):
        """Verify placeholder translators register successfully and return basic DDL/warnings."""
        from akaal.migration.models import Function as ModelFunction
        func_obj = ModelFunction(name="test_func")
        func_trans = ObjectTranslatorRegistry.get_translator(ObjectType.FUNCTION)
        res = func_trans.translate_alter(func_obj, {}, IdentifierQuoter.postgresql(), None, None)
        self.assertIn("Unsupported ALTER operation", res.warnings[0])

    def test_transaction_batching_relocation(self):
        """Verify TransactionBatcher splits commands correctly."""
        batcher = TransactionBatcher()
        cmd_tx = DDLCommand(sql="SQL1", transaction_required=True)
        cmd_notx = DDLCommand(sql="SQL2", transaction_required=False)
        cmd_tx2 = DDLCommand(sql="SQL3", transaction_required=True)

        batches = batcher.batch_commands([cmd_tx, cmd_notx, cmd_tx2])
        self.assertEqual(len(batches), 3)
        self.assertEqual(batches[0], [cmd_tx])
        self.assertEqual(batches[1], [cmd_notx])
        self.assertEqual(batches[2], [cmd_tx2])

    def test_pg_translation_and_rollback(self):
        """Verify PostgreSQL DDL generation and integrated rollbacks."""
        gen = PostgreSQLDDLGenerator()
        t_obj = Table(name="logs", schema="public")
        op = MigrationOperation(
            operation_id="op_1",
            operation_type=OperationType.CREATE,
            target_object=t_obj
        )
        cmds = gen.generate_commands([op])
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].sql, 'CREATE TABLE "public"."logs" (id INT PRIMARY KEY)')
        self.assertEqual(cmds[0].rollback_sql, 'DROP TABLE IF EXISTS "public"."logs"')

    def test_mysql_translation_and_rollback(self):
        """Verify MySQL DDL generation, integrated rollbacks, and replacements."""
        gen = MySQLDDLGenerator()
        col_obj = Column(name="status", schema="public", data_type="VARCHAR(20)")
        op = MigrationOperation(
            operation_id="op_1",
            operation_type=OperationType.CREATE,
            target_object=col_obj,
            context={"table_name": "orders"}
        )
        cmds = gen.generate_commands([op])
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].sql, 'ALTER TABLE `public`.`orders` ADD `status` VARCHAR(20)')
        self.assertEqual(cmds[0].rollback_sql, 'ALTER TABLE `public`.`orders` DROP COLUMN `status`')

    def test_oracle_translation_and_rollback(self):
        """Verify Oracle DDL generation and replacements."""
        gen = OracleDDLGenerator()
        col_obj = Column(name="status", schema="public", data_type="VARCHAR(20)")
        op = MigrationOperation(
            operation_id="op_1",
            operation_type=OperationType.CREATE,
            target_object=col_obj,
            context={"table_name": "orders"}
        )
        cmds = gen.generate_commands([op])
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].sql, 'ALTER TABLE "PUBLIC"."ORDERS" ADD "STATUS" VARCHAR(20)')

    def test_sqlserver_translation_and_rollback(self):
        """Verify SQL Server DDL generation."""
        gen = SQLServerDDLGenerator()
        t_obj = Table(name="logs", schema="public")
        op = MigrationOperation(
            operation_id="op_1",
            operation_type=OperationType.CREATE,
            target_object=t_obj
        )
        cmds = gen.generate_commands([op])
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].sql, 'CREATE TABLE [public].[logs] (id INT PRIMARY KEY)')

    def test_warning_propagation(self):
        """Verify warning collection matches model properties."""
        gen = PostgreSQLDDLGenerator()
        t_obj = Table(name="logs", schema="public")
        op = MigrationOperation(
            operation_id="op_1",
            operation_type=OperationType.DROP,
            target_object=t_obj
        )
        cmds = gen.generate_commands([op])
        self.assertEqual(len(cmds), 1)
        self.assertIn("Destructive operation", cmds[0].warnings[0])

    def test_compatibility_layer_imports(self):
        """Verify that imports from akaal.migration.ddl re-export correct types."""
        from akaal.migration.ddl import PostgreSQLDDLGenerator as OldPostgres
        self.assertEqual(OldPostgres, PostgreSQLDDLGenerator)
