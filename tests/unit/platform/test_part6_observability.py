"""
Unit Tests for AKAAL Platform Part 6 - Observability Subsystem.
"""

import unittest
from akaal.platform.observability.central_log_manager import CentralLogManager, LogLevel, LogAggregation
from akaal.platform.observability.metrics_engine import MetricsRegistry, MetricsEngine
from akaal.platform.observability.tracing_engine import TracingEngine, TraceContext
from akaal.platform.observability.observability_manager import ObservabilityManager


class TestObservabilitySubsystem(unittest.TestCase):

    def setUp(self):
        self.node_id = "node-test-1"
        self.obs = ObservabilityManager(self.node_id)

    def test_log_manager_asynchronous_queue(self):
        event = self.obs.log_info("test.logger", "System initializing", trace_id="tr-1001", region="us-east")
        self.assertEqual(event.logger_name, "test.logger")
        self.assertEqual(event.level, LogLevel.INFO)
        self.assertEqual(event.trace_id, "tr-1001")
        self.assertEqual(event.node_id, self.node_id)

        query_results = self.obs.log_manager.aggregation.query_logs(logger_name="test.logger")
        self.assertEqual(len(query_results), 1)

    def test_metrics_registry_and_prometheus_export(self):
        self.obs.record_counter("akaal_records_processed_total", 500, labels={"partition": "p0"})
        self.obs.record_counter("akaal_records_processed_total", 250, labels={"partition": "p0"})
        self.obs.record_gauge("akaal_memory_used_bytes", 1048576)

        counter_val = self.obs.metrics_registry.get_counter("akaal_records_processed_total", labels={"partition": "p0"})
        self.assertEqual(counter_val, 750.0)

        gauge_val = self.obs.metrics_registry.get_gauge("akaal_memory_used_bytes")
        self.assertEqual(gauge_val, 1048576.0)

        export_text = self.obs.metrics_engine.export_prometheus_format()
        self.assertIn("akaal_records_processed_total", export_text)
        self.assertIn("akaal_memory_used_bytes", export_text)

    def test_tracing_engine_and_w3c_context(self):
        span = self.obs.start_trace("ProcessStreamBatch")
        self.assertIsNotNone(span.trace_id)
        self.assertIsNotNone(span.span_id)
        span.finish()
        self.assertIsNotNone(span.end_time_ms)

        context = TraceContext(trace_id=span.trace_id, parent_span_id=span.span_id)
        headers = context.inject_headers()
        self.assertIn("traceparent", headers)

        extracted = TraceContext.extract_headers(headers)
        self.assertEqual(extracted.trace_id, span.trace_id)
        self.assertEqual(extracted.parent_span_id, span.span_id)


if __name__ == "__main__":
    unittest.main()
