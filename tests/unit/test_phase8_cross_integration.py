import asyncio
import unittest
from akaal.core.models.project import MigrationProject, ConnectionConfig
from akaal.core.models.enums import SystemType, MigrationStrategy
from akaal.core.models.configuration import (
    ColumnMapping,
    TableMapping,
    TransformationRule,
    MaskingRule
)
from akaal.migration.reliability.mapping.engine import MappingEngine
from akaal.migration.reliability.transformation.transformer import DataTransformer
from akaal.migration.reliability.masking.masker import DataMasker
from akaal.migration.execution.incremental.manager import IncrementalManager
from akaal.migration.execution.incremental.store import MemoryStateStore

class TestPhase8CrossIntegration(unittest.TestCase):
    def test_mapping_transformation_masking_integration(self):
        # 1. Setup Configuration
        c_src = ConnectionConfig(SystemType.POSTGRESQL, "localhost", 5432, "src", "ref")
        c_tgt = ConnectionConfig(SystemType.POSTGRESQL, "localhost", 5432, "tgt", "ref")
        project = MigrationProject("cross_integration_proj", c_src, c_tgt, MigrationStrategy.BIG_BANG)

        # Mappings: Rename raw_email to email, ignore password, inject constant category='GUEST'
        col1 = ColumnMapping("raw_email", "email")
        col2 = ColumnMapping("password", "password", is_ignored=True)
        col3 = ColumnMapping("category", "category", constant_value="GUEST")
        t_map = TableMapping("users", "users_target", column_mappings=[col1, col2, col3])
        project.configuration.mapping.table_mappings = [t_map]

        # Transformations: Convert first_name to uppercase (priority 10), raw_email to lowercase (priority 5)
        rule_a = TransformationRule("first_name", "EXPRESSION", expression="upper(first_name)", priority=10)
        rule_b = TransformationRule("raw_email", "EXPRESSION", expression="lower(raw_email)", priority=5)
        project.configuration.transformation.rules = {"users": [rule_a, rule_b]}

        # Masking: Hash email column
        mask_rule = MaskingRule("email", "HASH", salt="testsalt")
        project.configuration.masking.policies = {"users": [mask_rule]}

        # 2. Engines
        map_engine = MappingEngine(project.configuration.mapping)
        transformer = DataTransformer(project.configuration.transformation)
        masker = DataMasker(project.configuration.masking)

        # 3. Process Row
        row = {
            "raw_email": "John.Doe@EXAMPLE.COM",
            "first_name": "john",
            "password": "secret_password",
            "other_field": 42
        }

        # Step A: Transform
        row = transformer.transform_row("users", row)
        self.assertEqual(row["raw_email"], "john.doe@example.com")
        self.assertEqual(row["first_name"], "JOHN")

        # Step B: Mask
        # Wait, since the mask rule points to the mapped column 'email', we must do mapping first OR mapping renames before masking!
        # In GBAgent.migrate_table:
        # row = transformer.transform_row(table_name, row)
        # row = masker.mask_row(table_name, row) # wait, mask rules are configured on target columns or source columns?
        # In GBAgent we did:
        # row = transformer.transform_row(table_name, row)
        # row = masker.mask_row(table_name, row)
        # row = map_engine.map_row(table_name, row)
        # So we configure mask rule on the target column name or the raw column name!
        # If mask rules are applied on raw/transformed columns:
        # Let's adjust rule to raw_email:
        raw_mask_rule = MaskingRule("raw_email", "HASH", salt="testsalt")
        project.configuration.masking.policies = {"users": [raw_mask_rule]}
        masker = DataMasker(project.configuration.masking)

        row = masker.mask_row("users", row)
        self.assertNotEqual(row["raw_email"], "john.doe@example.com") # hashed!

        # Step C: Map
        row = map_engine.map_row("users", row)
        self.assertNotIn("raw_email", row)
        self.assertIn("email", row) # renamed from raw_email
        self.assertNotIn("password", row)
        self.assertEqual(row["category"], "GUEST")
        self.assertEqual(row["other_field"], 42)

    async def run_incremental_watermark_integration(self):
        store = MemoryStateStore()
        manager = IncrementalManager(store)

        project_id = "p1"
        migration_id = "m1"
        table_name = "orders"

        # Fresh run: watermark is None
        w1 = await manager.get_current_watermark(project_id, migration_id, table_name)
        self.assertIsNone(w1)

        # Batch 1 processed: update watermark to latest value
        batch = [
            {"id": 1, "updated_at": "2026-07-17T10:00:00Z"},
            {"id": 2, "updated_at": "2026-07-17T11:00:00Z"}
        ]
        
        # Save max updated_at
        max_val = max([r["updated_at"] for r in batch])
        await manager.update_watermark(project_id, migration_id, table_name, max_val)

        # Resumed run: get watermark
        w2 = await manager.get_current_watermark(project_id, migration_id, table_name)
        self.assertEqual(w2, "2026-07-17T11:00:00Z")

        # Compile filter
        config = {"strategy": "TIMESTAMP", "tracking_column": "updated_at"}
        inc_filter = manager.get_incremental_filter(config, w2)
        self.assertIsNotNone(inc_filter)
        self.assertEqual(inc_filter["column"], "updated_at")
        self.assertEqual(inc_filter["value"], "2026-07-17T11:00:00Z")

    def test_run_async(self):
        import asyncio
        asyncio.run(self.run_incremental_watermark_integration())
