"""
tests.unit.engine_extensions.test_sandbox_isolation
=====================================================
Hostile verification of P7A.3 SUBPROCESS isolation: real OS process boundary,
real wall-clock timeout enforcement, real crash containment, real environment
restriction, and honest reporting of what is/isn't platform-enforceable.

No mocks: real child Python processes throughout.
"""

from __future__ import annotations

import os
import sys
import time

import pytest

from akaalEngine.extensions.errors.taxonomy import ExtensionRegistrationError
from akaalEngine.extensions.loading.isolation import IsolationManager
from akaalEngine.extensions.models.enums import IsolationMode, TrustTier
from akaalEngine.extensions.sandbox.permissions import GrantedPermissions, PermissionKind, PermissionRequest
from akaalEngine.extensions.sandbox.process_isolation import SubprocessSandbox

TARGET_MODULE = "tests.unit.engine_extensions.fixtures.sandbox_worker_targets"


def test_successful_execution_returns_result():
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0)
    result = SubprocessSandbox.execute(TARGET_MODULE, "echo", {"x": 1}, granted)
    assert result.success is True
    assert result.result == {"echoed": {"x": 1}}
    assert result.exit_code == 0


def test_extension_crash_is_contained_not_propagated():
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0)
    result = SubprocessSandbox.execute(TARGET_MODULE, "crash", {}, granted)
    assert result.success is False
    assert "RuntimeError" in result.error
    assert result.timed_out is False
    # The host test process itself is still alive and functioning -- proven by this
    # assertion executing at all after the "crash".


def test_hard_process_exit_is_contained_not_propagated():
    """A native-style hard exit (not a Python exception) still yields a clean failure result."""
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0)
    result = SubprocessSandbox.execute(TARGET_MODULE, "crash_the_process_outright", {}, granted)
    assert result.success is False
    assert result.exit_code == 139
    assert result.timed_out is False


def test_hung_extension_is_killed_at_wall_clock_budget():
    granted = GrantedPermissions(wall_clock_budget_seconds=1.0)
    start = time.monotonic()
    result = SubprocessSandbox.execute(TARGET_MODULE, "hang_forever", {}, granted)
    elapsed = time.monotonic() - start
    assert result.success is False
    assert result.timed_out is True
    # Must be killed close to the budget, not left to run indefinitely.
    assert elapsed < 5.0, f"Sandbox did not enforce timeout promptly (took {elapsed}s)"


def test_environment_is_restricted_to_granted_variables_only():
    os.environ["AKAAL_TEST_SECRET_NOT_GRANTED"] = "should-not-be-visible"
    os.environ["AKAAL_TEST_GRANTED_VAR"] = "should-be-visible"
    try:
        granted = GrantedPermissions(
            wall_clock_budget_seconds=10.0,
            environment_variables=frozenset({"AKAAL_TEST_GRANTED_VAR"}),
        )
        result = SubprocessSandbox.execute(
            TARGET_MODULE, "read_env_var", {"var_name": "AKAAL_TEST_GRANTED_VAR"}, granted
        )
        assert result.success is True
        assert result.result == {"value": "should-be-visible"}

        result2 = SubprocessSandbox.execute(
            TARGET_MODULE, "read_env_var", {"var_name": "AKAAL_TEST_SECRET_NOT_GRANTED"}, granted
        )
        assert result2.success is True
        assert result2.result == {"value": None}, (
            "Ungranted environment variable leaked into the sandboxed child process."
        )
    finally:
        del os.environ["AKAAL_TEST_SECRET_NOT_GRANTED"]
        del os.environ["AKAAL_TEST_GRANTED_VAR"]


def test_no_environment_variables_granted_means_none_leak():
    os.environ["AKAAL_TEST_ANOTHER_SECRET"] = "must-not-leak"
    try:
        granted = GrantedPermissions(wall_clock_budget_seconds=10.0)  # zero-trust default
        result = SubprocessSandbox.execute(
            TARGET_MODULE, "read_env_var", {"var_name": "AKAAL_TEST_ANOTHER_SECRET"}, granted
        )
        assert result.success is True
        assert result.result == {"value": None}
    finally:
        del os.environ["AKAAL_TEST_ANOTHER_SECRET"]


def test_malformed_module_reference_fails_closed_not_silently():
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0)
    result = SubprocessSandbox.execute("nonexistent.module.path", "whatever", {}, granted)
    assert result.success is False
    assert result.error


@pytest.mark.skipif(sys.platform == "win32", reason="RLIMIT_AS/RLIMIT_CPU are POSIX-only; honestly not enforced on Windows.")
def test_posix_resource_limits_are_reported_as_enforced():
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0, memory_budget_bytes=256 * 1024 * 1024)
    result = SubprocessSandbox.execute(TARGET_MODULE, "echo", {"a": 1}, granted)
    assert result.resource_limits_enforced is True


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object containment is Windows-only.")
def test_windows_job_object_reports_memory_limit_as_actually_enforced():
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0, memory_budget_bytes=256 * 1024 * 1024)
    result = SubprocessSandbox.execute(TARGET_MODULE, "echo", {"a": 1}, granted)
    assert result.success is True
    assert result.memory_limit_enforced is True, (
        "Windows Job Object memory containment should now be real, not the prior no-op."
    )
    assert result.cpu_limit_enforced is False, (
        "CPU-rate containment is not implemented on Windows in this pass -- must not be claimed."
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object containment is Windows-only.")
def test_windows_job_object_actually_kills_memory_hog_over_budget():
    """
    Real hostile proof, not just a metadata flag: a process granted only a 64MB job-object
    memory ceiling that tries to commit ~512MB of actually-touched (not just reserved) memory
    must be killed by the OS before it can report success.
    """
    granted = GrantedPermissions(wall_clock_budget_seconds=30.0, memory_budget_bytes=64 * 1024 * 1024)
    result = SubprocessSandbox.execute(TARGET_MODULE, "allocate_and_touch_memory", {"mb": 512}, granted)
    assert result.success is False, (
        "A process that committed far more memory than its job-object ceiling allows must not "
        "be able to report success -- the OS-level limit should have killed it first."
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object containment is Windows-only.")
def test_windows_job_object_allows_allocation_within_budget():
    """Sanity: a real memory limit must not falsely reject usage that stays under budget."""
    granted = GrantedPermissions(wall_clock_budget_seconds=30.0, memory_budget_bytes=512 * 1024 * 1024)
    result = SubprocessSandbox.execute(TARGET_MODULE, "allocate_and_touch_memory", {"mb": 32}, granted)
    assert result.success is True, result.error
    assert result.result == {"allocated_mb": 32}


# ---------------------------------------------------------------------------
# Permission request/grant separation
# ---------------------------------------------------------------------------

def test_grant_can_never_exceed_request():
    requested = PermissionRequest(
        filesystem_read_paths=frozenset({"/opt/allowed"}),
        network_egress_hosts=frozenset({"api.example.com"}),
    )
    # An operator/policy layer "approving" far more than was ever requested
    over_approved = PermissionRequest(
        filesystem_read_paths=frozenset({"/opt/allowed", "/etc/shadow", "/"}),
        network_egress_hosts=frozenset({"api.example.com", "*"}),
    )
    granted = GrantedPermissions.restrict_to_request(requested, over_approved)
    assert granted.filesystem_read_paths == frozenset({"/opt/allowed"})
    assert granted.network_egress_hosts == frozenset({"api.example.com"})
    assert "/etc/shadow" not in granted.filesystem_read_paths
    assert "*" not in granted.network_egress_hosts


def test_manifest_cannot_self_authorize_by_declaring_broad_request():
    """A manifest requesting everything still only receives what an independent approval intersects to."""
    greedy_request = PermissionRequest(
        filesystem_read_paths=frozenset({"/"}),
        filesystem_write_paths=frozenset({"/"}),
        network_egress_hosts=frozenset({"*"}),
        secret_references=frozenset({"vault:prod/*"}),
    )
    minimal_approval = PermissionRequest()  # policy layer approves nothing
    granted = GrantedPermissions.restrict_to_request(greedy_request, minimal_approval)
    assert granted == GrantedPermissions.empty()


def test_empty_grant_is_the_zero_trust_default():
    assert GrantedPermissions.empty().filesystem_read_paths == frozenset()
    assert GrantedPermissions.empty().network_egress_hosts == frozenset()
    assert GrantedPermissions.empty().secret_references == frozenset()


def test_permission_kind_enum_covers_declared_dimensions():
    assert PermissionKind.FILESYSTEM_READ.value == "FILESYSTEM_READ"
    assert PermissionKind.SECRET_REFERENCE.value == "SECRET_REFERENCE"


# ---------------------------------------------------------------------------
# Secret-reference resolution (hostile-review BLOCKER #3 fix): reuses the
# canonical Engine SecretConsumer authority; only granted references are ever
# resolved or handed to the child; values never touch env/argv.
# ---------------------------------------------------------------------------

def test_granted_secret_reference_is_resolved_and_passed_to_child():
    from akaalEngine.connection.security.secret_consumer import InMemorySecretResolver, SecretConsumer

    resolver = InMemorySecretResolver({"db/password": "s3cr3t-value"})
    consumer = SecretConsumer(resolver=resolver)
    granted = GrantedPermissions(
        wall_clock_budget_seconds=10.0,
        secret_references=frozenset({"db/password"}),
    )
    result = SubprocessSandbox.execute(
        TARGET_MODULE, "read_secret", {"secret_ref": "db/password"}, granted, secret_consumer=consumer
    )
    assert result.success is True
    assert result.result == {"value": "s3cr3t-value"}


def test_ungranted_secret_reference_is_never_resolved_even_if_requested_by_name():
    """
    The extension asks for a reference it was never GRANTED (only requested elsewhere, or
    just guessed at) -- SecretConsumer must never even be consulted for it, proving the
    grant (not the extension's own request) is the enforcement boundary.
    """
    from akaalEngine.connection.security.secret_consumer import InMemorySecretResolver, SecretConsumer

    resolver = InMemorySecretResolver({"db/password": "s3cr3t-value", "other/secret": "should-never-leak"})
    consumer = SecretConsumer(resolver=resolver)
    granted = GrantedPermissions(
        wall_clock_budget_seconds=10.0,
        secret_references=frozenset({"db/password"}),  # "other/secret" NOT granted
    )
    result = SubprocessSandbox.execute(
        TARGET_MODULE, "read_secret", {"secret_ref": "other/secret"}, granted, secret_consumer=consumer
    )
    assert result.success is True
    assert result.result == {"value": None}, "Ungranted secret reference leaked into the sandboxed child."


def test_no_secret_consumer_means_no_secrets_ever_passed():
    granted = GrantedPermissions(
        wall_clock_budget_seconds=10.0,
        secret_references=frozenset({"db/password"}),  # granted, but no consumer supplied
    )
    result = SubprocessSandbox.execute(
        TARGET_MODULE, "read_secret", {"secret_ref": "db/password"}, granted, secret_consumer=None
    )
    assert result.success is True
    assert result.result == {"value": None}


def test_secret_resolution_failure_does_not_silently_omit_but_is_reported():
    from akaalEngine.connection.security.secret_consumer import InMemorySecretResolver, SecretConsumer

    resolver = InMemorySecretResolver({})  # "db/password" is not in the store
    consumer = SecretConsumer(resolver=resolver)
    granted = GrantedPermissions(
        wall_clock_budget_seconds=10.0,
        secret_references=frozenset({"db/password"}),
    )
    # SecretConsumer.resolve() itself fails closed (raises SecretResolutionError) for an
    # unresolvable granted reference -- proving the sandbox doesn't swallow that failure
    # into a silently-empty secret.
    from akaalEngine.connection.models.errors import SecretResolutionError
    with pytest.raises(SecretResolutionError):
        SubprocessSandbox.execute(
            TARGET_MODULE, "read_secret", {"secret_ref": "db/password"}, granted, secret_consumer=consumer
        )


def test_single_argument_extension_callable_still_works_without_secrets_param():
    """An extension callable that only accepts `payload` (no secrets awareness) must keep working."""
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0)
    result = SubprocessSandbox.execute(TARGET_MODULE, "echo", {"x": 1}, granted)
    assert result.success is True
    assert result.result == {"echoed": {"x": 1}}


# ---------------------------------------------------------------------------
# IsolationManager: SUBPROCESS is now real, WASM/REMOTE remain honestly unimplemented
# ---------------------------------------------------------------------------

def test_isolation_manager_now_accepts_subprocess():
    result = IsolationManager.verify_isolation_mode(IsolationMode.SUBPROCESS, TrustTier.VERIFIED_PARTNER)
    assert result == IsolationMode.SUBPROCESS


def test_isolation_manager_still_rejects_wasm_and_remote_honestly():
    with pytest.raises(ExtensionRegistrationError):
        IsolationManager.verify_isolation_mode(IsolationMode.WASM_UNSUPPORTED, TrustTier.VERIFIED_PARTNER)
    with pytest.raises(ExtensionRegistrationError):
        IsolationManager.verify_isolation_mode(IsolationMode.REMOTE_UNSUPPORTED, TrustTier.VERIFIED_PARTNER)


def test_isolation_manager_still_accepts_in_process():
    result = IsolationManager.verify_isolation_mode(IsolationMode.IN_PROCESS, TrustTier.CORE_TRUSTED)
    assert result == IsolationMode.IN_PROCESS


# ---------------------------------------------------------------------------
# Hostile-review Blocker #1: sandbox assurance downgrade must fail closed.
# A required isolation stronger than what this Engine can actually provide must
# deny execution BEFORE any untrusted code runs -- not silently proceed under
# weaker isolation than was required.
# ---------------------------------------------------------------------------

from akaalEngine.extensions.sandbox.permissions import IsolationAssurance, assurance_satisfies, stricter_assurance


def test_os_enforced_filesystem_requirement_denies_execution_before_any_subprocess_spawn():
    """
    The extension/policy requires OS_ENFORCED filesystem isolation. This Engine only
    provides HOST_MEDIATED. Execution must be denied BEFORE subprocess.Popen is ever
    called -- proven by patching Popen to raise if invoked, not merely by checking the
    result flag.
    """
    import unittest.mock as mock

    granted = GrantedPermissions(
        wall_clock_budget_seconds=10.0,
        required_filesystem_isolation=IsolationAssurance.OS_ENFORCED,
    )
    with mock.patch("subprocess.Popen", side_effect=AssertionError("Popen must never be called when assurance is denied")):
        result = SubprocessSandbox.execute(TARGET_MODULE, "echo", {"x": 1}, granted)

    assert result.success is False
    assert result.denied_by_assurance_policy is True
    assert result.result is None


def test_os_enforced_network_requirement_denies_execution_before_any_subprocess_spawn():
    import unittest.mock as mock

    granted = GrantedPermissions(
        wall_clock_budget_seconds=10.0,
        required_network_isolation=IsolationAssurance.OS_ENFORCED,
    )
    with mock.patch("subprocess.Popen", side_effect=AssertionError("Popen must never be called when assurance is denied")):
        result = SubprocessSandbox.execute(TARGET_MODULE, "echo", {"x": 1}, granted)

    assert result.success is False
    assert result.denied_by_assurance_policy is True


def test_extension_side_effect_never_occurs_when_assurance_denied():
    """
    Real sentinel proof, not just a metadata flag: a callable with a real, observable
    side effect (writes a marker file) must never execute when the assurance gate denies.
    """
    import tempfile

    marker_dir = tempfile.mkdtemp()
    marker_path = os.path.join(marker_dir, "sentinel_marker.txt")
    assert not os.path.exists(marker_path)

    granted = GrantedPermissions(
        wall_clock_budget_seconds=10.0,
        required_network_isolation=IsolationAssurance.OS_ENFORCED,
        filesystem_write_paths=frozenset({marker_dir}),
    )
    result = SubprocessSandbox.execute(
        TARGET_MODULE, "write_marker_file", {"path": marker_path}, granted
    )
    assert result.success is False
    assert result.denied_by_assurance_policy is True
    assert not os.path.exists(marker_path), (
        "Extension side effect occurred despite the assurance gate denying execution."
    )


def test_default_host_mediated_requirement_proceeds_normally():
    """The default (HOST_MEDIATED required) is satisfied by what this Engine provides -- must proceed."""
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0)  # defaults to HOST_MEDIATED/HOST_MEDIATED
    result = SubprocessSandbox.execute(TARGET_MODULE, "echo", {"x": 1}, granted)
    assert result.success is True
    assert result.denied_by_assurance_policy is False
    assert result.result == {"echoed": {"x": 1}}


def test_explicit_host_mediated_requirement_proceeds_normally():
    """A policy that explicitly says HOST_MEDIATED is sufficient must be allowed to proceed."""
    granted = GrantedPermissions(
        wall_clock_budget_seconds=10.0,
        required_filesystem_isolation=IsolationAssurance.HOST_MEDIATED,
        required_network_isolation=IsolationAssurance.HOST_MEDIATED,
    )
    result = SubprocessSandbox.execute(TARGET_MODULE, "echo", {"x": 1}, granted)
    assert result.success is True
    assert result.denied_by_assurance_policy is False


def test_extension_cannot_weaken_policy_mandated_requirement():
    """
    restrict_to_request must take the STRICTER of extension-requested and policy-approved
    isolation -- an extension declaring a weaker requirement than the owner's policy floor
    must not be able to downgrade the effective requirement.
    """
    policy_floor = PermissionRequest(required_filesystem_isolation=IsolationAssurance.OS_ENFORCED)
    extension_request = PermissionRequest(required_filesystem_isolation=IsolationAssurance.HOST_MEDIATED)
    granted = GrantedPermissions.restrict_to_request(requested=extension_request, approved=policy_floor)
    assert granted.required_filesystem_isolation == IsolationAssurance.OS_ENFORCED


def test_extension_declaring_stronger_requirement_than_policy_is_honored():
    """The inverse: if the extension itself wants MORE isolation than policy mandates, honor that too."""
    policy_floor = PermissionRequest(required_network_isolation=IsolationAssurance.HOST_MEDIATED)
    extension_request = PermissionRequest(required_network_isolation=IsolationAssurance.OS_ENFORCED)
    granted = GrantedPermissions.restrict_to_request(requested=extension_request, approved=policy_floor)
    assert granted.required_network_isolation == IsolationAssurance.OS_ENFORCED


def test_assurance_satisfies_ordering():
    assert assurance_satisfies(IsolationAssurance.OS_ENFORCED, IsolationAssurance.HOST_MEDIATED) is True
    assert assurance_satisfies(IsolationAssurance.HOST_MEDIATED, IsolationAssurance.HOST_MEDIATED) is True
    assert assurance_satisfies(IsolationAssurance.HOST_MEDIATED, IsolationAssurance.OS_ENFORCED) is False


def test_stricter_assurance_never_returns_the_weaker_of_the_two():
    assert stricter_assurance(IsolationAssurance.HOST_MEDIATED, IsolationAssurance.OS_ENFORCED) == IsolationAssurance.OS_ENFORCED
    assert stricter_assurance(IsolationAssurance.OS_ENFORCED, IsolationAssurance.HOST_MEDIATED) == IsolationAssurance.OS_ENFORCED
    assert stricter_assurance(IsolationAssurance.HOST_MEDIATED, IsolationAssurance.HOST_MEDIATED) == IsolationAssurance.HOST_MEDIATED


def test_sandbox_reports_remain_truthful_not_flipped_to_enforced():
    """
    Blocker #2 guard: closing Blocker #1 must NOT be done by relabeling NOT_ENFORCED as
    ENFORCED. A successful HOST_MEDIATED-sufficient execution must still truthfully report
    NOT_ENFORCED for OS isolation -- the fix is a pre-execution gate, not a claim change.
    """
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0)
    result = SubprocessSandbox.execute(TARGET_MODULE, "echo", {"x": 1}, granted)
    assert result.success is True
    assert result.filesystem_access_model == "HOST_MEDIATED"
    assert result.filesystem_os_isolation == "NOT_ENFORCED"
    assert result.network_access_model == "HOST_MEDIATED"
    assert result.network_os_isolation == "NOT_ENFORCED"
