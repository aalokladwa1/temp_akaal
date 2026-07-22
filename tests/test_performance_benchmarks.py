"""
Performance & Micro-Benchmarking Verification Suite.
"""

import time
import pytest
from akaal.cdc.contracts.event import CDCEvent, ChangeType
from akaal.cdc.coordinator.coordinator import CDCCoordinator
from akaal.reporting.contracts.dto import ReportRequestDTO
from akaal.reporting.engine.engine import ReportEngine


@pytest.mark.asyncio
async def test_cdc_throughput_benchmark():
    coord = CDCCoordinator()
    evt = CDCEvent(source_engine="POSTGRES", source_db="db", source_schema="public", source_table="users", change_type=ChangeType.INSERT)

    iterations = 500
    start = time.time()
    for _ in range(iterations):
        await coord.process_cdc_event(evt)
    elapsed = time.time() - start

    events_per_sec = iterations / elapsed
    assert events_per_sec > 100, f"CDC throughput below target: {events_per_sec:.2f} events/sec"


def test_reporting_export_benchmark():
    engine = ReportEngine()
    formats = ["JSON", "HTML", "CSV", "PDF"]

    for fmt in formats:
        req = ReportRequestDTO(report_type="PRE_MIGRATION", migration_id="bench-1", export_format=fmt)
        start = time.time()
        res = engine.generate_report(req)
        elapsed_ms = (time.time() - start) * 1000.0

        assert len(res.content_b64) > 0
        assert elapsed_ms < 100.0, f"{fmt} report generation latency too high: {elapsed_ms:.2f} ms"
