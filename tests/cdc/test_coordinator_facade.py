"""
Unit tests for CDCCoordinator, CDCClient, and Platform4Facade.
"""

import pytest
from akaal.api.facades.platform4 import Platform4Facade as Platform7FacadeWrapper
from akaal.cdc.api.client import CDCClient
from akaal.cdc.api.facade import Platform4Facade
from akaal.cdc.contracts.event import CDCEvent, ChangeType


@pytest.mark.asyncio
async def test_cdc_client_and_facade_flow():
    p7_wrapper = Platform7FacadeWrapper()
    facade = Platform4Facade()

    # Capabilities check via Platform 7 facade wrapper
    caps = await p7_wrapper.get_capabilities()
    assert caps.platform_name == "Platform 4 (CDC & Replay)"
    assert "distributed_cdc" in caps.supported_features

    # Start Session
    sess = await facade.start_cdc_session("POSTGRES", "db_prod", ["target_dw"])
    assert sess.session_id.startswith("cdc-sess-")
    assert sess.status == "RUNNING"

    # Process Event
    evt = CDCEvent(source_engine="POSTGRES", source_db="db_prod", source_schema="public", source_table="users", change_type=ChangeType.INSERT)
    success = await facade.process_event(evt)
    assert success is True

    # Replay
    replay_res = await facade.replay_events([evt], "0/0", "0/100")
    assert replay_res.replayed_events_count == 1

    # Failover
    fo_res = await facade.failover_sync("node-failed", "node-backup")
    assert fo_res.status == "COMPLETED"
