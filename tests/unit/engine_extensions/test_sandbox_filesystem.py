"""
tests.unit.engine_extensions.test_sandbox_filesystem
=====================================================
Hostile verification of Blocker #3 Filesystem Sandbox Enforcement:
- Model B: Host-Mediated Capability Execution is the real security boundary.
- Canonical path resolution, symlink/junction escape defense, traversal rejection.
- Zero-trust default-deny when no read/write roots are granted.
- Protection against unauthorized home directory, repo root, and config file access.
- In-worker defense-in-depth guard intercepts direct open() calls.
- Truthful reporting of HOST_MEDIATED access model vs OS isolation boundary.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import pytest

from akaalEngine.extensions.sandbox.host_mediated import (
    HostMediatedFilesystemService,
    SandboxFilesystemClient,
    SandboxSecurityError,
)
from akaalEngine.extensions.sandbox.permissions import GrantedPermissions
from akaalEngine.extensions.sandbox.process_isolation import SubprocessSandbox
from akaalEngine.extensions.sandbox.worker_guards import DirectIOException, install_worker_filesystem_guard

TARGET_MODULE = "tests.unit.engine_extensions.fixtures.sandbox_worker_targets"


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_read = os.path.join(tmpdir, "allowed_read")
        allowed_write = os.path.join(tmpdir, "allowed_write")
        forbidden = os.path.join(tmpdir, "forbidden")
        os.makedirs(allowed_read, exist_ok=True)
        os.makedirs(allowed_write, exist_ok=True)
        os.makedirs(forbidden, exist_ok=True)

        read_file = os.path.join(allowed_read, "data.txt")
        with open(read_file, "w") as f:
            f.write("allowed content")

        forbidden_file = os.path.join(forbidden, "secret.key")
        with open(forbidden_file, "w") as f:
            f.write("top secret")

        yield {
            "root": tmpdir,
            "allowed_read": allowed_read,
            "allowed_write": allowed_write,
            "forbidden": forbidden,
            "read_file": read_file,
            "forbidden_file": forbidden_file,
        }


def test_allowed_read_succeeds(temp_workspace):
    granted = GrantedPermissions(
        filesystem_read_paths=frozenset({temp_workspace["allowed_read"]})
    )
    svc = HostMediatedFilesystemService(granted)
    client = SandboxFilesystemClient(svc)

    data = client.read_file(temp_workspace["read_file"])
    assert data == b"allowed content"


def test_denied_read_fails_closed(temp_workspace):
    granted = GrantedPermissions(
        filesystem_read_paths=frozenset({temp_workspace["allowed_read"]})
    )
    svc = HostMediatedFilesystemService(granted)

    with pytest.raises(SandboxSecurityError) as exc_info:
        svc.read_file(temp_workspace["forbidden_file"])
    assert "outside granted roots" in str(exc_info.value)


def test_zero_trust_default_deny_when_no_paths_granted(temp_workspace):
    granted = GrantedPermissions.empty()
    svc = HostMediatedFilesystemService(granted)

    with pytest.raises(SandboxSecurityError) as exc_info:
        svc.read_file(temp_workspace["read_file"])
    assert "no filesystem read paths granted" in str(exc_info.value)


def test_allowed_write_succeeds_where_granted(temp_workspace):
    granted = GrantedPermissions(
        filesystem_write_paths=frozenset({temp_workspace["allowed_write"]})
    )
    svc = HostMediatedFilesystemService(granted)

    out_file = os.path.join(temp_workspace["allowed_write"], "output.log")
    written = svc.write_file(out_file, b"sample log output")
    assert written == len(b"sample log output")

    with open(out_file, "rb") as f:
        assert f.read() == b"sample log output"


def test_denied_write_fails(temp_workspace):
    # Only allowed_write is granted, attempting to write to forbidden or allowed_read must fail
    granted = GrantedPermissions(
        filesystem_write_paths=frozenset({temp_workspace["allowed_write"]})
    )
    svc = HostMediatedFilesystemService(granted)

    out_file = os.path.join(temp_workspace["forbidden"], "hack.txt")
    with pytest.raises(SandboxSecurityError):
        svc.write_file(out_file, b"malicious content")


def test_directory_traversal_fails(temp_workspace):
    # Granted allowed_read, attempting ../ traversal to escape to forbidden
    granted = GrantedPermissions(
        filesystem_read_paths=frozenset({temp_workspace["allowed_read"]})
    )
    svc = HostMediatedFilesystemService(granted)

    traversal_path = os.path.join(temp_workspace["allowed_read"], "..", "forbidden", "secret.key")
    with pytest.raises(SandboxSecurityError):
        svc.read_file(traversal_path)


def test_absolute_path_escape_fails(temp_workspace):
    granted = GrantedPermissions(
        filesystem_read_paths=frozenset({temp_workspace["allowed_read"]})
    )
    svc = HostMediatedFilesystemService(granted)

    system_path = "C:\\Windows\\System32\\drivers\\etc\\hosts" if os.name == "nt" else "/etc/passwd"
    with pytest.raises(SandboxSecurityError):
        svc.read_file(system_path)


def test_unauthorized_home_directory_access_fails(temp_workspace):
    granted = GrantedPermissions(
        filesystem_read_paths=frozenset({temp_workspace["allowed_read"]})
    )
    svc = HostMediatedFilesystemService(granted)

    home_file = os.path.join(str(Path.home()), ".ssh", "id_rsa")
    with pytest.raises(SandboxSecurityError):
        svc.read_file(home_file)


def test_symlink_escape_fails_if_supported(temp_workspace):
    # Test symlink escape if OS supports creating symlinks in the test environment
    symlink_path = os.path.join(temp_workspace["allowed_read"], "symlink_escape")
    try:
        os.symlink(temp_workspace["forbidden_file"], symlink_path)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not permitted in current OS/user environment.")

    granted = GrantedPermissions(
        filesystem_read_paths=frozenset({temp_workspace["allowed_read"]})
    )
    svc = HostMediatedFilesystemService(granted)

    with pytest.raises(SandboxSecurityError):
        svc.read_file(symlink_path)


def test_null_byte_in_path_rejected(temp_workspace):
    granted = GrantedPermissions(
        filesystem_read_paths=frozenset({temp_workspace["allowed_read"]})
    )
    svc = HostMediatedFilesystemService(granted)

    with pytest.raises(SandboxSecurityError) as exc_info:
        svc.read_file(temp_workspace["read_file"] + "\x00.exe")
    assert "Null bytes" in str(exc_info.value)


def test_worker_filesystem_guard_intercepts_direct_open(temp_workspace):
    """
    install_worker_filesystem_guard() monkey-patches builtins.open process-globally --
    not scoped to this test. Without an explicit uninstall in finally, every subsequent
    test in this pytest session would have builtins.open replaced by the guarded version,
    breaking unrelated tests that use ordinary file I/O (reproduced as a real regression
    before this fix). In production this guard only ever runs inside an isolated sandboxed
    CHILD process whose exit naturally undoes the patch.
    """
    from akaalEngine.extensions.sandbox.worker_guards import uninstall_worker_filesystem_guard

    install_worker_filesystem_guard(allowed_dirs=[temp_workspace["allowed_read"]])
    try:
        # Direct open on allowed dir succeeds
        with open(temp_workspace["read_file"], "r") as f:
            assert f.read() == "allowed content"

        # Direct open on forbidden dir raises DirectIOException
        with pytest.raises(DirectIOException):
            open(temp_workspace["forbidden_file"], "r")
    finally:
        uninstall_worker_filesystem_guard()


def test_worker_filesystem_guard_is_fully_restored_after_uninstall(temp_workspace):
    """Proves the guard doesn't leak: after uninstall, an ordinary open() outside any allowed dir works again."""
    from akaalEngine.extensions.sandbox.worker_guards import uninstall_worker_filesystem_guard

    install_worker_filesystem_guard(allowed_dirs=[temp_workspace["allowed_read"]])
    uninstall_worker_filesystem_guard()

    # forbidden_file is outside the guard's allowed_dirs -- if the guard were still
    # installed this would raise DirectIOException; it must succeed once uninstalled.
    with open(temp_workspace["forbidden_file"], "r") as f:
        f.read()


def test_truthful_execution_result_reports_host_mediated_boundary():
    granted = GrantedPermissions(wall_clock_budget_seconds=10.0)
    result = SubprocessSandbox.execute(
        TARGET_MODULE, "echo", {"test": "val"}, granted
    )
    assert result.success is True
    assert result.filesystem_access_model == "HOST_MEDIATED"
    assert result.filesystem_os_isolation == "NOT_ENFORCED"
    assert result.network_access_model == "HOST_MEDIATED"
    assert result.network_os_isolation == "NOT_ENFORCED"
