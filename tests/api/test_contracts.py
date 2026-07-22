"""
Unit tests for Contracts and Errors.
"""

import pytest
from akaal.api.contracts.errors import (
    AkaalError,
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
    ErrorResponse,
)
from akaal.api.contracts.dto import JobRequestDTO, JobResponseDTO


def test_akaal_error_serialization():
    err = AuthenticationError("Invalid API key", details={"key": "test"})
    assert err.status_code == 401
    assert err.code == "AUTHENTICATION_FAILED"
    d = err.to_dict()
    assert d["code"] == "AUTHENTICATION_FAILED"
    assert d["message"] == "Invalid API key"


def test_dto_instantiation():
    req = JobRequestDTO(job_type="migration", payload={"table": "users"}, priority=8)
    assert req.job_type == "migration"
    assert req.priority == 8

    res = JobResponseDTO(job_id="job-1", status="QUEUED", job_type="migration", created_at="2026-07-22T00:00:00Z")
    assert res.job_id == "job-1"
