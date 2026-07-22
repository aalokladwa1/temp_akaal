"""
Failure Injection & Chaos Engineering Verification Test Suite.
"""

import pytest
from akaal.cdc.buffering.buffer import DurableCDCBuffer
from akaal.cdc.contracts.event import CDCEvent, ChangeType
from akaal.cdc.replay.engine import CDCReplayEngine
from akaal.reporting.contracts.dto import ReportRequestDTO
from akaal.reporting.engine.engine import ReportEngine


def test_cdc_buffer_overflow_and_dlq_chaos():
    buffer = DurableCDCBuffer(max_capacity=2)
    evt1 = CDCEvent(source_engine="POSTGRES", source_db="db", source_schema="s", source_table="t", change_type=ChangeType.INSERT)
    evt2 = CDCEvent(source_engine="POSTGRES", source_db="db", source_schema="s", source_table="t", change_type=ChangeType.INSERT)
    evt3 = CDCEvent(source_engine="POSTGRES", source_db="db", source_schema="s", source_table="t", change_type=ChangeType.INSERT)

    assert buffer.push_event(evt1) is True
    assert buffer.push_event(evt2) is True
    # Overflow attempt
    assert buffer.push_event(evt3) is False

    dlq_events = buffer.dlq.get_all()
    assert len(dlq_events) == 1
    assert dlq_events[0]["reason"] == "Buffer capacity overflow"


@pytest.mark.asyncio
async def test_cdc_reordered_and_duplicate_replay_chaos():
    engine = CDCReplayEngine()
    evt1 = CDCEvent(event_id="e1", source_engine="MYSQL", source_db="d", source_schema="s", source_table="t", change_type=ChangeType.INSERT)
    evt2 = CDCEvent(event_id="e2", source_engine="MYSQL", source_db="d", source_schema="s", source_table="t", change_type=ChangeType.UPDATE)

    # Out-of-order duplicate events
    events = [evt2, evt1, evt2, evt1]

    result = await engine.replay_events(events, start_position="0/0", end_position="0/100")
    assert result.replayed_events_count == 2
    assert result.status == "COMPLETED"


def test_reporting_engine_invalid_report_type_chaos():
    engine = ReportEngine()
    req = ReportRequestDTO(report_type="INVALID_TYPE", migration_id="mig-err")

    with pytest.raises(ValueError, match="Unsupported report type"):
        engine.generate_report(req)
