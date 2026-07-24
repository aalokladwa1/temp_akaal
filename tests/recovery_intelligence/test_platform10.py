"""
AKAAL Platform 10 — Recovery Intelligence Unit & Integration Test Suite.
Verifies all 5 capabilities: RPO Recommendation, RTO Estimation, Recovery Strategy Recommendation, Readiness Assessment, Recovery Simulation.
"""

import unittest
import asyncio

from akaal.recovery_intelligence import RecoveryIntelligencePlatformV10
from akaal.api.facades.platform10 import Platform10Facade


class TestPlatform10RecoveryIntelligence(unittest.TestCase):

    def setUp(self):
        self.platform = RecoveryIntelligencePlatformV10()
        self.facade = Platform10Facade(self.platform)

    def test_capabilities_dto(self):
        caps = asyncio.run(self.facade.get_capabilities())
        self.assertEqual(caps.platform_name, "Platform 10 (Recovery Intelligence Platform)")
        self.assertEqual(len(caps.supported_features), 5)

    def test_rpo_recommendation(self):
        rec = self.platform.recommend_recovery_point("mig-001", "chk-100")
        self.assertEqual(rec.target_migration_id, "mig-001")

    def test_rto_estimation(self):
        est = self.platform.estimate_recovery_time("mig-001", 10)
        self.assertEqual(est.estimated_rto_minutes, 5.0)

    def test_strategy_recommendation(self):
        stg = self.platform.recommend_strategy("mig-001", checkpoint_available=True)
        self.assertEqual(stg.strategy_type.value, "CHECKPOINT_RESUME")

    def test_readiness_assessment(self):
        rep = self.platform.assess_readiness("mig-001", checkpoint_valid=True)
        self.assertEqual(rep.state.value, "READY")

    def test_scenario_simulation(self):
        sim = self.platform.simulate_recovery("mig-001")
        self.assertTrue(sim.success)

    def test_facade_async_recommendation(self):
        res = asyncio.run(self.facade.recommend_recovery_point("mig-001", "chk-100"))
        self.assertEqual(res["target_migration_id"], "mig-001")


if __name__ == "__main__":
    unittest.main()
