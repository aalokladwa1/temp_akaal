"""
AKAAL Platform 9 — Reliability Intelligence Unit & Integration Test Suite.
Verifies all 5 capabilities: Regression Testing, Baseline Comparison, Trend Analysis, Drift Detection, Recommendation Engine.
"""

import unittest
import asyncio

from akaal.reliability_intelligence import ReliabilityIntelligencePlatformV9
from akaal.api.facades.platform9 import Platform9Facade


class TestPlatform9ReliabilityIntelligence(unittest.TestCase):

    def setUp(self):
        self.platform = ReliabilityIntelligencePlatformV9()
        self.facade = Platform9Facade(self.platform)

    def test_capabilities_dto(self):
        caps = asyncio.run(self.facade.get_capabilities())
        self.assertEqual(caps.platform_name, "Platform 9 (Reliability Intelligence Platform)")
        self.assertEqual(len(caps.supported_features), 5)

    def test_regression_evaluation(self):
        report = self.platform.evaluate_regression("workflow-engine", 10.0, 12.0)
        self.assertEqual(report.status.value, "PASSED")

        regressed = self.platform.evaluate_regression("workflow-engine", 10.0, 20.0)
        self.assertEqual(regressed.status.value, "REGRESSED")

    def test_baseline_creation(self):
        bsl = self.platform.create_baseline("distributed-runtime", 15.0, 0.01, 99.99)
        self.assertEqual(bsl.target_name, "distributed-runtime")

    def test_trend_analysis(self):
        trends = self.platform.analyze_trends([10.0, 12.0, 14.0, 16.0])
        self.assertEqual(trends["trend_direction"], "DEGRADED")

    def test_drift_detection(self):
        drift = self.platform.detect_drift("cdc-coordinator", 10.0, 13.0)
        self.assertEqual(drift.drift_severity.value, "MODERATE")

    def test_recommendation_generation(self):
        rec = self.platform.generate_recommendation("streaming-runtime", "Scale Partition Count", "Increase partitions from 8 to 16")
        self.assertEqual(rec.service_id, "streaming-runtime")

    def test_facade_async_eval(self):
        res = asyncio.run(self.facade.evaluate_regression("workflow-engine", 10.0, 11.0))
        self.assertEqual(res["status"], "PASSED")


if __name__ == "__main__":
    unittest.main()
