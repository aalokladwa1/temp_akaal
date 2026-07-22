"""
Unit tests for Platform Façades.
"""

import pytest
from akaal.api.contracts.dto import JobRequestDTO, WorkflowSubmitDTO, SchemaCheckDTO
from akaal.api.facades.platform1 import Platform1Facade
from akaal.api.facades.platform2 import Platform2Facade
from akaal.api.facades.platform5 import Platform5Facade


@pytest.mark.asyncio
async def test_platform1_facade_job_submit():
    facade = Platform1Facade()
    req = JobRequestDTO(job_type="copy_table", payload={"source": "A", "target": "B"})
    res = await facade.submit_job(req)
    assert res.job_id.startswith("job-")
    assert res.status == "QUEUED"

    status = await facade.get_job_status(res.job_id)
    assert status.job_id == res.job_id
    assert status.status == "QUEUED"


@pytest.mark.asyncio
async def test_platform2_facade_worker_scale():
    facade = Platform2Facade()
    status = await facade.get_worker_cluster_status()
    assert status.cluster_health == "HEALTHY"

    scaled = await facade.scale_workers(15)
    assert scaled.previous_count == 10
    assert scaled.target_count == 15


@pytest.mark.asyncio
async def test_platform5_facade_schema_check():
    facade = Platform5Facade()
    req = SchemaCheckDTO(target_schema_name="users", proposed_ddl="ALTER TABLE users ADD COLUMN age INT;")
    res = await facade.validate_schema_compatibility(req)
    assert res.is_compatible is True

    bad_req = SchemaCheckDTO(
        target_schema_name="users", proposed_ddl="ALTER TABLE users DROP COLUMN age;", compatibility_mode="BACKWARD"
    )
    bad_res = await facade.validate_schema_compatibility(bad_req)
    assert bad_res.is_compatible is False
    assert len(bad_res.violations) > 0
