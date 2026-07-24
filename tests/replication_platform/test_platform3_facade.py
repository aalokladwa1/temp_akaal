"""Tests for EnterpriseReplicationPlatformV3 canonical façade and end-to-end execution."""

import pytest
from akaal.replication.facade.platform3 import EnterpriseReplicationPlatformV3
from akaal.replication.core.config import ReplicationConfig, ReplicationProfile


def test_platform3_facade_initialization():
    platform = EnterpriseReplicationPlatformV3()
    assert platform.get_health()["status"] == "HEALTHY"
    caps = platform.get_supported_capabilities()
    assert len(caps) == 25


def test_platform3_sync_execution():
    platform = EnterpriseReplicationPlatformV3()
    session = platform.replicate_all()
    assert session.is_successful is True
    assert len(session.results) == 6
    assert session.total_actions_executed > 0


@pytest.mark.asyncio
async def test_platform3_async_execution():
    platform = EnterpriseReplicationPlatformV3()
    session = await platform.replicate_all_async()
    assert session.is_successful is True
    assert session.state.value == "COMPLETED"
