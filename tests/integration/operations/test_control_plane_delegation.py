"""
Integration Tests for Control Plane Delegation and Operations Platform Façade.
"""

import pytest
from akaal.operations.facade.platform9 import DefaultOperationsPlatformV9


def test_platform9_facade_and_control_plane_delegation():
    platform = DefaultOperationsPlatformV9()

    # 1. Verification of initial overview
    overview = platform.get_overview()
    assert overview["system_health"] == 100.0
    assert "Platform1" in overview["registered_platforms"]

    # 2. Control plane authorization checks
    # Authorized admin user
    res1 = platform.control_plane.pause_job("job_100", "admin")
    assert res1 is True

    # Unauthorized operator user attempting emergency_stop
    with pytest.raises(PermissionError):
        platform.control_plane.emergency_stop("operator1")
