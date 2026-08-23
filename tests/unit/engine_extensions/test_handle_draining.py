"""
tests.unit.engine_extensions.test_handle_draining
=================================================
Tests for handle lease tracking, drain-safe deactivation, and duplicate/stale release safety.
"""

from akaalEngine.extensions.lifecycle.leases import HandleLeaseTracker
from akaalEngine.extensions.models.identity import ExtensionId, StrategyId


def test_handle_lease_acquisition_and_release():
    tracker = HandleLeaseTracker()
    ext_id = ExtensionId("ext-a")
    strat_id = StrategyId("strat-1")

    assert tracker.get_total_active_count() == 0
    assert tracker.get_extension_active_count(ext_id) == 0

    token1 = tracker.acquire_lease(ext_id, strat_id)
    token2 = tracker.acquire_lease(ext_id, strat_id)

    assert tracker.get_total_active_count() == 2
    assert tracker.get_extension_active_count(ext_id) == 2
    assert tracker.get_strategy_active_count(strat_id) == 2

    # Release first token
    assert tracker.release_lease(token1) is True
    assert tracker.get_total_active_count() == 1
    assert tracker.get_extension_active_count(ext_id) == 1

    # Duplicate release of already released token returns False without corrupting counter
    assert tracker.release_lease(token1) is False
    assert tracker.get_total_active_count() == 1
    assert tracker.get_extension_active_count(ext_id) == 1

    # Release second token
    assert tracker.release_lease(token2) is True
    assert tracker.get_total_active_count() == 0
    assert tracker.get_extension_active_count(ext_id) == 0
    assert tracker.has_active_leases(ext_id) is False


def test_unregister_rejection_with_active_leases():
    import pytest
    from akaalEngine.extensions.authority import ExtensionsAuthority
    from akaalEngine.extensions.errors.taxonomy import ExtensionHandleLeakError

    ext_auth = ExtensionsAuthority.get_instance()

    # Acquire an active strategy handle (lease)
    handle = ext_auth.resolve_strategy("sqlite", "connection")
    assert handle is not None

    # Attempting to unregister the owning extension while the handle lease is active must fail closed
    with pytest.raises(ExtensionHandleLeakError) as exc_info:
        ext_auth.unregister_extension(handle.extension_id)
    assert "active strategy handle leases exist" in str(exc_info.value)

    # Release lease
    handle.release()
