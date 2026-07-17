import unittest
from akaal.migration.models import ObjectType, OperationType
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry
from akaal.core.models.enums import SystemType
from akaal.migration.ddl.utilities.quoting import IdentifierQuoter
from akaal.migration.ddl.utilities.capabilities import DialectCapabilities
from akaal.migration.ddl.utilities.builder import SQLBuilder

class MockSynonym:
    def __init__(self, name: str, schema: str, object_name: str, is_public: bool = False):
        self.name = name
        self.schema = schema
        self.object_name = object_name
        self.is_public = is_public

class MockMaterializedView:
    def __init__(self, name: str, schema: str, definition: str, refresh_mode: str = "DEMAND", refresh_method: str = "FORCE"):
        self.name = name
        self.schema = schema
        self.definition = definition
        self.refresh_mode = refresh_mode
        self.refresh_method = refresh_method

class TestSynonymMVDependency(unittest.TestCase):
    def test_synonym_skips_and_generation(self):
        translator = ObjectTranslatorRegistry.get_translator(ObjectType.SYNONYM)
        quoter = IdentifierQuoter('"', '"')
        caps = DialectCapabilities()
        builder = SQLBuilder()

        # PG skip check
        syn = MockSynonym("my_syn", "public", "target_table")
        res_pg = translator.translate_create(
            syn, {"target_dialect": SystemType.POSTGRESQL}, quoter, caps, builder
        )
        self.assertEqual(res_pg.sql, "")
        self.assertTrue(any("does not support synonyms" in w for w in res_pg.warnings))

        # Oracle generation check
        res_oracle = translator.translate_create(
            syn, {"target_dialect": SystemType.ORACLE}, quoter, caps, builder
        )
        self.assertIn("CREATE SYNONYM", res_oracle.sql)
        self.assertIn("FOR \"target_table\"", res_oracle.sql)

        # Oracle public synonym check
        syn_pub = MockSynonym("pub_syn", "public", "target_table", is_public=True)
        res_oracle_pub = translator.translate_create(
            syn_pub, {"target_dialect": SystemType.ORACLE}, quoter, caps, builder
        )
        self.assertIn("CREATE PUBLIC SYNONYM", res_oracle_pub.sql)

    def test_materialized_view_generation(self):
        translator = ObjectTranslatorRegistry.get_translator(ObjectType.MATERIALIZED_VIEW)
        quoter = IdentifierQuoter('"', '"')
        caps = DialectCapabilities()
        builder = SQLBuilder()

        mv = MockMaterializedView("my_mv", "public", "SELECT * FROM users", refresh_mode="COMMIT")

        # MySQL skip check
        res_mysql = translator.translate_create(
            mv, {"target_dialect": SystemType.MYSQL}, quoter, caps, builder
        )
        self.assertEqual(res_mysql.sql, "")
        self.assertTrue(any("does not support materialized views" in w for w in res_mysql.warnings))

        # PG native check
        res_pg = translator.translate_create(
            mv, {"target_dialect": SystemType.POSTGRESQL}, quoter, caps, builder
        )
        self.assertIn("CREATE MATERIALIZED VIEW", res_pg.sql)
        self.assertTrue(any("does not support COMMIT" in w for w in res_pg.warnings))

        # SQL Server indexed view check
        res_mssql = translator.translate_create(
            mv, {"target_dialect": SystemType.MSSQL}, quoter, caps, builder
        )
        self.assertIn("CREATE VIEW", res_mssql.sql)
        self.assertIn("WITH SCHEMABINDING", res_mssql.sql)
