"""
Unit tests for gRPC Servicer and Interceptors.
"""

import pytest
from akaal.api.grpc.service import AkaalV1Servicer


@pytest.mark.asyncio
async def test_grpc_servicer_submit_job():
    servicer = AkaalV1Servicer()
    req = {
        "job_type": "grpc_job",
        "payload_json": '{"target": "db"}',
        "priority": 7,
        "tenant_id": "tenant-grpc-1",
    }
    res = await servicer.SubmitJob(req)
    assert res["job_id"].startswith("job-")
    assert res["status"] == "QUEUED"

    status_req = {"job_id": res["job_id"]}
    status_res = await servicer.GetJobStatus(status_req)
    assert status_res["job_id"] == res["job_id"]
    assert status_res["status"] == "QUEUED"


@pytest.mark.asyncio
async def test_grpc_stream_logs():
    servicer = AkaalV1Servicer()
    logs = []
    async for chunk in servicer.StreamJobLogs({"job_id": "job-100"}):
        logs.append(chunk["log_line"])
    assert len(logs) == 3
    assert "Log stream initialized" in logs[0]
