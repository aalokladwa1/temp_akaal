import unittest
from akaal.advisor.eta_engine import ETAEngine
from akaal.migration.target_identifier import validate_operator_configured_identifier, derive_akaal_generated_target_mapping

class TestETAAndTargetIdentifierValidation(unittest.TestCase):

    def test_preflight_eta_unmeasured_returns_calibrating(self):
        objects = [{"object_name": "t1", "object_type": "Table", "estimated_rows": 10000}]
        res = ETAEngine.calculate_preflight_eta(objects, source_read_rows_per_sec=None, target_write_rows_per_sec=None)
        self.assertIsNone(res["estimated_duration_seconds"])
        self.assertEqual(res["estimated_duration_display"], "Not yet estimated")
        self.assertEqual(res["eta_confidence"], "Low")

    def test_preflight_eta_with_real_benchmarks(self):
        objects = [
            {"object_name": "t1", "object_type": "Table", "estimated_rows": 100000, "estimated_bytes": 5000000},
            {"object_name": "t2", "object_type": "Table", "estimated_rows": 50000, "estimated_bytes": 2000000}
        ]
        res = ETAEngine.calculate_preflight_eta(
            objects,
            source_read_rows_per_sec=1000.0,
            target_write_rows_per_sec=500.0,
            parallelism=1
        )
        self.assertIsNotNone(res["estimated_duration_seconds"])
        # Total rows = 150,000. Bottleneck write rate = 500 rows/sec (single-stream).
        # Duration = 150,000 / 500 = 300s (5m 0s)
        self.assertEqual(res["estimated_duration_seconds"], 307)
        self.assertEqual(res["eta_confidence"], "Medium")
        self.assertIn("Conservative preflight estimate", res["eta_basis"])

    def test_runtime_ewma_adaptive_eta(self):
        # 100,000 total, 20,000 transferred (80,000 remaining).
        # Observed rate = 1,000 rows/sec.
        res = ETAEngine.calculate_runtime_adaptive_eta(
            rows_total=100000,
            rows_transferred=20000,
            observed_rows_per_sec=1000.0,
            previous_ewma_rate=None
        )
        self.assertEqual(res["rows_remaining"], 80000)
        self.assertEqual(res["ewma_rows_per_sec"], 1000.0)
        self.assertEqual(res["estimated_remaining_seconds"], 80)
        self.assertIn("1m 20s remaining", res["display_eta"])

    def test_operator_configured_identifier_rejection(self):
        # Explicit operator configuration of 'pg_analytics' MUST BE REJECTED
        res = validate_operator_configured_identifier("pg_analytics", "schema")
        self.assertFalse(res["valid"])
        self.assertEqual(res["error_code"], "RESERVED_PREFIX")
        self.assertIn("reserved by PostgreSQL system namespaces", res["error_message"])

    def test_operator_configured_valid_schema(self):
        res = validate_operator_configured_identifier("app_analytics", "schema")
        self.assertTrue(res["valid"])
        self.assertEqual(res["sanitized_identifier"], "app_analytics")

    def test_akaal_generated_target_mapping(self):
        # Auto-generated mapping for discovered catalog
        res = derive_akaal_generated_target_mapping("pg_analytics")
        self.assertTrue(res["remapped"])
        self.assertEqual(res["target_schema"], "app_analytics")

if __name__ == "__main__":
    unittest.main()
