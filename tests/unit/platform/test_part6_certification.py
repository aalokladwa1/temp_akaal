"""
Unit Tests for AKAAL Platform Part 6 - Operations, Chaos & 7-Gate Platform Certification.
"""

import unittest
from akaal.platform.ops.operations_manager import OperationsManager, IncidentState
from akaal.platform.testing.chaos_manager import ChaosManager, ChaosFaultType
from akaal.platform.testing.testing_manager import TestingManager
from akaal.platform.supportability.support_manager import SupportManager
from akaal.platform.certification.platform_certification_manager import PlatformCertificationManager


class TestOperationsAndCertification(unittest.TestCase):

    def setUp(self):
        self.ops = OperationsManager()
        self.chaos = ChaosManager()
        self.test_mgr = TestingManager()
        self.support = SupportManager()
        self.cert_mgr = PlatformCertificationManager()

    def test_incident_lifecycle_and_runbook_execution(self):
        inc = self.ops.incidents.create_incident("High Latency on Node 3", "CRITICAL")
        self.assertEqual(inc.state, IncidentState.DETECTED)

        self.ops.incidents.transition_state(inc.incident_id, IncidentState.INVESTIGATING)
        self.assertEqual(self.ops.incidents._incidents[inc.incident_id].state, IncidentState.INVESTIGATING)

        self.ops.runbooks.register_runbook("DrainNode3", lambda: True)
        self.assertTrue(self.ops.runbooks.execute_runbook("DrainNode3"))

    def test_chaos_fault_injection_and_benchmark(self):
        exp = self.chaos.run_experiment("node-worker-2", ChaosFaultType.NETWORK_LATENCY, duration_sec=5)
        self.assertTrue(exp.active)
        self.assertEqual(exp.fault_type, ChaosFaultType.NETWORK_LATENCY)

        report = self.test_mgr.benchmark_manager.run_benchmark("MemoryRingBuffer", iterations=5000)
        self.assertTrue(report.passed_sla)
        self.assertGreater(report.throughput_records_per_sec, 0)

    def test_support_bundle_generation(self):
        bundle = self.support.generate_support_bundle("supp-999")
        self.assertEqual(bundle.bundle_id, "supp-999")
        self.assertIn("node_id", bundle.system_snapshot)

    def test_7_gate_platform_certification(self):
        gates = self.cert_mgr.execute_all_gates()
        self.assertEqual(len(gates), 7)
        for g in gates:
            self.assertTrue(g.passed, f"Gate failed: {g.gate_name}")

        self.assertTrue(self.cert_mgr.is_platform_certified())


if __name__ == "__main__":
    unittest.main()
