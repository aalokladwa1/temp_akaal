import unittest
from akaal.migration.target_identifier import sanitize_pg_identifier, validate_target_schema

class TestTargetIdentifierValidation(unittest.TestCase):

    def test_reserved_pg_prefix_sanitization(self):
        self.assertEqual(sanitize_pg_identifier("pg_analytics"), "app_analytics")
        self.assertEqual(sanitize_pg_identifier("PG_CUSTOM"), "app_custom")

    def test_reserved_pg_schema_names(self):
        res = validate_target_schema("pg_analytics")
        self.assertFalse(res["valid"])
        self.assertEqual(res["error_code"], "RESERVED_SCHEMA_NAME")
        self.assertEqual(res["suggestion"], "app_analytics")

    def test_valid_custom_target_schema(self):
        res = validate_target_schema("custom_analytics")
        self.assertTrue(res["valid"])
        self.assertEqual(res["sanitized"], "custom_analytics")

    def test_length_truncation(self):
        long_name = "a" * 70
        sanitized = sanitize_pg_identifier(long_name)
        self.assertEqual(len(sanitized), 63)

if __name__ == "__main__":
    unittest.main()
