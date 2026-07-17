import unittest
from akaal.core.models.configuration import MappingConfiguration, TableMapping, ColumnMapping
from akaal.migration.reliability.mapping.engine import MappingEngine

class TestMappingValidation(unittest.TestCase):
    def test_mapping_validation_collisions(self):
        # Setup conflicting mapping configuration
        col1 = ColumnMapping("src_col", "tgt_col")
        col2 = ColumnMapping("other_col", "tgt_col") # Conflict target column name
        
        t_map = TableMapping("src_tbl", "tgt_tbl", column_mappings=[col1, col2])
        config = MappingConfiguration(table_mappings=[t_map])
        engine = MappingEngine(config)

        report = engine.validate_mappings()
        self.assertFalse(report.success)
        self.assertTrue(any("Collision" in err for err in report.errors))

    def test_mapping_validation_duplicates(self):
        col1 = ColumnMapping("src_col", "tgt_col")
        t_map1 = TableMapping("src_tbl", "tgt_tbl", column_mappings=[col1])
        t_map2 = TableMapping("src_tbl", "other_tgt_tbl", column_mappings=[col1]) # Duplicate source table
        
        config = MappingConfiguration(table_mappings=[t_map1, t_map2])
        engine = MappingEngine(config)

        report = engine.validate_mappings()
        self.assertFalse(report.success)
        self.assertTrue(any("Duplicate mapping" in err for err in report.errors))

    def test_row_remapping_and_injection(self):
        col1 = ColumnMapping("id", "user_id")
        col2 = ColumnMapping("email", "email_address")
        col3 = ColumnMapping("secret", "secret", is_ignored=True)
        col4 = ColumnMapping("type", "type", constant_value="CUSTOMER")
        col5 = ColumnMapping("computed", "computed", expression="concat(id, email)")

        t_map = TableMapping("users", "users_target", column_mappings=[col1, col2, col3, col4, col5])
        config = MappingConfiguration(table_mappings=[t_map])
        engine = MappingEngine(config)

        row = {
            "id": 123,
            "email": "test@example.com",
            "secret": "confidential",
            "first_name": "John" # Stays unchanged
        }

        mapped_row = engine.map_row("users", row)

        self.assertIn("user_id", mapped_row)
        self.assertEqual(mapped_row["user_id"], 123)
        self.assertNotIn("id", mapped_row)

        self.assertIn("email_address", mapped_row)
        self.assertEqual(mapped_row["email_address"], "test@example.com")

        self.assertNotIn("secret", mapped_row)

        self.assertIn("first_name", mapped_row)
        self.assertEqual(mapped_row["first_name"], "John")

        # Constant injection
        self.assertEqual(mapped_row["type"], "CUSTOMER")

        # Expression evaluation
        self.assertIn("computed", mapped_row)
