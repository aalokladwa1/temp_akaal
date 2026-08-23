"""
tests/integration/engine_data_processing/test_processing_runtime_integration.py
================================================================================
Integration tests for Authority #8 Data Processing physical integration with Authority #7 Telemetry & Authority #6 Runtime.
"""

import tempfile
import pytest
from akaalEngine.durability import DurabilityAuthority, DurabilityConfig
from akaalEngine.runtime import RuntimeAuthority
from akaalEngine.telemetry import TelemetryAuthority
from akaalEngine.data_processing import DataProcessingAuthority, TransformationRule, RuleType, PrivacyStrategy


@pytest.fixture
def temp_durability_authority():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = DurabilityConfig(
            storage_dir=tmp_dir,
            fencing_signing_key=b"fencing_secret_key_1234567890123",
            journal_anchor_key=b"journal_anchor_key_1234567890123",
        )
        dur = DurabilityAuthority(config)
        yield dur
        dur.close()


def test_data_processing_telemetry_and_runtime_integration(temp_durability_authority):
    """Proves DataProcessingAuthority emits metrics through TelemetryAuthority during batch transformations."""
    dur = temp_durability_authority
    runtime = RuntimeAuthority(durability_authority=dur)
    runtime.start()

    telemetry = TelemetryAuthority(runtime_authority=runtime)
    data_processing = DataProcessingAuthority(telemetry_authority=telemetry, runtime_authority=runtime)

    rule = TransformationRule(
        rule_id="r1", column_name="ssn", rule_type=RuleType.PRIVACY, privacy_strategy=PrivacyStrategy.STATIC_REDACT
    )
    plan = data_processing.compile_plan("customers", rules=[rule])

    batch = [{"ssn": "111-22-3333"}, {"ssn": "444-55-6666"}]
    transformed, results = data_processing.transform_batch(batch, plan)

    assert len(transformed) == 2
    assert transformed[0]["ssn"] == "[REDACTED]"
    assert transformed[1]["ssn"] == "[REDACTED]"

    # Verify Telemetry counter metrics recorded
    metrics_snap = telemetry.get_metric_snapshot()
    assert metrics_snap.counters.get("rows_processed_total", 0.0) == 2.0

    runtime.shutdown()
