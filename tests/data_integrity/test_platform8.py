"""
AKAAL Platform 8 — Enterprise Data Integrity Unit & Integration Test Suite.
Verifies all 6 capabilities: E2E Consistency, Transaction Boundaries, Snapshot Consistency, Cross-Table, Referential Integrity, Incremental.
"""

import unittest
import asyncio

from akaal.data_integrity import EnterpriseDataIntegrityPlatformV8
from akaal.api.facades.platform8 import Platform8Facade


class TestPlatform8DataIntegrity(unittest.TestCase):

    def setUp(self):
        self.platform = EnterpriseDataIntegrityPlatformV8()
        self.facade = Platform8Facade(self.platform)

    def test_capabilities_dto(self):
        caps = asyncio.run(self.facade.get_capabilities())
        self.assertEqual(caps.platform_name, "Platform 8 (Enterprise Data Integrity Platform)")
        self.assertEqual(len(caps.supported_features), 6)

    def test_e2e_consistency(self):
        report = self.platform.verify_e2e_consistency("orders_src", "orders_tgt", 1000000)
        self.assertEqual(report.status.value, "VALIDATED")
        self.assertEqual(report.rows_compared, 1000000)
        self.assertEqual(report.checksum_source, report.checksum_target)

    def test_transaction_boundary(self):
        res = self.platform.validate_transaction_boundary("tx-1001")
        self.assertTrue(res.is_committed_consistently)
        self.assertEqual(res.uncommitted_row_count, 0)

    def test_snapshot_consistency(self):
        report = self.platform.validate_snapshot("snap-2026", "users")
        self.assertEqual(report.status.value, "VALIDATED")

    def test_cross_table_consistency(self):
        report = self.platform.validate_cross_table(["users", "orders", "payments"])
        self.assertEqual(report.status.value, "VALIDATED")

    def test_referential_integrity(self):
        res = self.platform.validate_referential_integrity("fk_user_orders", "users", "orders")
        self.assertTrue(res.is_valid)

    def test_incremental_consistency(self):
        report = self.platform.verify_incremental("batch-99", 50000)
        self.assertEqual(report.status.value, "VALIDATED")

    def test_facade_async_e2e_verification(self):
        res = asyncio.run(self.facade.verify_e2e_consistency("customers", "customers", 100000))
        self.assertEqual(res["status"], "VALIDATED")


if __name__ == "__main__":
    unittest.main()
