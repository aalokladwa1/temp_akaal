"""
Unit Tests for AKAAL Platform Part 6 - Monitoring, Diagnostics & Alerting Subsystems.
"""

import unittest
from akaal.platform.monitoring.monitoring_manager import MonitoringManager, ProbeStatus
from akaal.platform.diagnostics.diagnostics_manager import DiagnosticsManager
from akaal.platform.alerting.alert_manager import AlertManager, AlertPayload, AlertSeverity, AlertRules


class TestMonitoringAndDiagnostics(unittest.TestCase):

    def setUp(self):
        self.mon = MonitoringManager()
        self.diag = DiagnosticsManager()
        self.alert = AlertManager()

    def test_health_monitoring_probes(self):
        health = self.mon.health_monitor.check_component("raft-consensus", lambda: True)
        self.assertEqual(health.status, ProbeStatus.HEALTHY)
        self.assertEqual(health.subsystem_name, "raft-consensus")

        synthetic = self.mon.synthetic_monitor.run_synthetic_probe("pipe-101")
        self.assertEqual(synthetic.status, ProbeStatus.HEALTHY)

    def test_diagnostics_and_root_cause_analysis(self):
        report = self.diag.diagnose_node("node-worker-5")
        self.assertIsNotNone(report.report_id)
        self.assertIn("node-worker-5", report.target_node_id)
        self.assertEqual(report.overall_status, ProbeStatus.HEALTHY)

    def test_alert_rules_routing_and_suppression(self):
        rule_eval = self.alert.rules.evaluate_rule("HighCpuUsage", current_value=125.0, threshold=80.0)
        self.assertIsNotNone(rule_eval)
        self.assertEqual(rule_eval.severity, AlertSeverity.CRITICAL)

        received_alerts = []
        self.alert.router.register_handler(lambda a: received_alerts.append(a))

        self.alert.dispatch(rule_eval)
        self.assertEqual(len(received_alerts), 1)

        # Test Alert Suppression
        self.alert.suppression.suppress_node("node-worker-5")
        suppressed_alert = AlertPayload(
            alert_id="alert-999",
            rule_name="RingBufferDrop",
            severity=AlertSeverity.WARNING,
            source_subsystem="memory-ring",
            node_id="node-worker-5",
            description="Buffer drop",
            timestamp_ms=10000,
        )
        self.alert.dispatch(suppressed_alert)
        self.assertTrue(suppressed_alert.suppressed)


if __name__ == "__main__":
    unittest.main()
