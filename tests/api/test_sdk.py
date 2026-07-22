"""
Unit tests for Python SDK (Sync and Async).
"""

import pytest
from akaal.api.sdk.client import AkaalClient, AsyncAkaalClient


@pytest.mark.asyncio
async def test_async_sdk_client():
    client = AsyncAkaalClient(api_key="akaal_live_test_key_123")
    res = await client.jobs.submit(job_type="sdk_job", payload={"test": True})
    assert res.job_id.startswith("job-")
    assert res.status == "QUEUED"

    status = await client.jobs.get_status(res.job_id)
    assert status.job_id == res.job_id


def test_sync_sdk_client():
    client = AkaalClient(api_key="akaal_live_test_key_123")
    res = client.jobs.submit(job_type="sync_sdk_job", payload={"sync": True})
    assert res.job_id.startswith("job-")
    assert res.status == "QUEUED"

    cluster_status = client.monitoring.get_cluster_status()
    assert cluster_status.cluster_health == "HEALTHY"
