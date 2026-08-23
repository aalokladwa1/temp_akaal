"""
tests/integration/engine_transport/test_transport_integration.py
===============================================================
Integration tests for Authority #9 Transport physical integration with Authorities #1, #5, #6, #7, #8.
"""

import tempfile
import pytest
from akaalEngine.data_processing import DataProcessingAuthority, RuleType, TransformationRule
from akaalEngine.durability import DurabilityAuthority, DurabilityConfig
from akaalEngine.runtime import RuntimeAuthority
from akaalEngine.telemetry import TelemetryAuthority
from akaalEngine.transport import (
    FileSourceReader,
    FileTargetWriter,
    PartitionStrategy,
    TransportAuthority,
    TransportPartition,
)


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


def test_transport_authority_full_integration(temp_durability_authority):
    """Proves TransportAuthority integrates cleanly with Data Processing, Telemetry, Runtime, and Durability."""
    dur = temp_durability_authority
    runtime = RuntimeAuthority(durability_authority=dur)
    runtime.start()

    telemetry = TelemetryAuthority(runtime_authority=runtime)
    data_processing = DataProcessingAuthority(telemetry_authority=telemetry, runtime_authority=runtime)

    transport = TransportAuthority(
        durability_authority=dur,
        runtime_authority=runtime,
        telemetry_authority=telemetry,
        data_processing_authority=data_processing,
    )

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as f_src, \
         tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as f_tgt:

        f_src.write("id,name,city\n1,Alice,NYC\n2,Bob,LA\n")
        f_src.flush()
        f_src.close()

        reader = FileSourceReader(f_src.name, "CSV")
        writer = FileTargetWriter(f_tgt.name, "CSV")

        rule = TransformationRule(rule_id="r1", column_name="city", cleansing_operation="UPPER", rule_type=RuleType.CLEANSING)
        plan = data_processing.compile_plan("customers", rules=[rule])

        part = TransportPartition(
            partition_id="p1",
            table_name=f_src.name,
            schema_name="file",
            target_schema="file",
            strategy=PartitionStrategy.SINGLE_PARTITION,
        )

        written = transport.execute_partition_transport(
            reader=reader,
            writer=writer,
            partition=part,
            processing_plan=plan,
        )

        assert written == 2

        # Verify Telemetry Snapshot
        snap = transport.get_snapshot()
        assert snap.rows_read_total == 2
        assert snap.rows_written_total == 2

        writer.close()

    runtime.shutdown()
