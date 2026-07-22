"""
Unit tests for Replay Engine and Exactly-Once Controller.
"""

import pytest
from akaal.cdc.contracts.event import CDCEvent, ChangeType
from akaal.cdc.replay.engine import CDCReplayEngine, ExactlyOnceController


@pytest.mark.asyncio
async def test_exactly_once_controller():
    controller = ExactlyOnceController()
    evt1 = CDCEvent(event_id="evt-100", source_engine="POSTGRES", source_db="db", source_schema="s", source_table="t", change_type=ChangeType.INSERT)

    assert controller.process_event(evt1) is True
    # Duplicate event
    assert controller.process_event(evt1) is False


@pytest.mark.asyncio
async def test_cdc_replay_engine():
    engine = CDCReplayEngine()
    evt1 = CDCEvent(event_id="evt-1", source_engine="MYSQL", source_db="db", source_schema="s", source_table="t", change_type=ChangeType.INSERT)
    evt2 = CDCEvent(event_id="evt-2", source_engine="MYSQL", source_db="db", source_schema="s", source_table="t", change_type=ChangeType.UPDATE)

    # List with duplicate
    events = [evt1, evt2, evt1]

    result = await engine.replay_events(events, start_position="0/0", end_position="0/100")
    assert result.replayed_events_count == 2
    assert result.status == "COMPLETED"
