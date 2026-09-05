"""
akaalEngine.extensions.sandbox.worker_guards
============================================
In-worker defense-in-depth guards for sandboxed child OS processes.

DISCLOSED BOUNDARY:
These guards hook direct Python runtime I/O primitives inside the child process
to provide fast-fail detection if an untrusted extension attempts direct I/O
instead of utilizing the canonical HostMediatedFilesystemService or
HostMediatedNetworkService.
They do NOT claim kernel-level OS sandboxing. The primary security boundary is
the Host-Mediated Capability Execution Model.
"""

from __future__ import annotations

import builtins
import io
import os
import socket
from typing import Any, Optional, Sequence


class DirectIOException(PermissionError):
    """Raised when an extension tries direct OS I/O bypassing host mediation."""
    pass


# Real, process-global monkey-patches -- MUST be restored via the matching uninstall_*
# function. These guards are meant to run only inside an isolated sandboxed CHILD OS
# process (see process_isolation.py's worker script), whose entire process exits when the
# sandboxed call completes, so the monkey-patch's process-lifetime is naturally bounded
# there. Calling install_* directly in a long-lived process (e.g. a test runner) without
# calling the matching uninstall_* leaves builtins.open/socket.socket.connect permanently
# patched for that process -- this was a real, reproduced defect (a network-guard test
# left every subsequent test in the same pytest session unable to open a real socket).
_ORIGINAL_OPEN: Optional[Any] = None
_ORIGINAL_SOCKET_CONNECT: Optional[Any] = None


def uninstall_worker_filesystem_guard() -> None:
    """Restores builtins.open to its pre-guard state. Idempotent -- safe to call even if not installed."""
    global _ORIGINAL_OPEN
    if _ORIGINAL_OPEN is not None:
        builtins.open = _ORIGINAL_OPEN
        _ORIGINAL_OPEN = None


def uninstall_worker_network_guard() -> None:
    """Restores socket.socket.connect to its pre-guard state. Idempotent -- safe to call even if not installed."""
    global _ORIGINAL_SOCKET_CONNECT
    if _ORIGINAL_SOCKET_CONNECT is not None:
        socket.socket.connect = _ORIGINAL_SOCKET_CONNECT
        _ORIGINAL_SOCKET_CONNECT = None


def install_worker_filesystem_guard(
    allowed_dirs: Optional[Sequence[str]] = None,
) -> None:
    """
    Installs worker-level defense-in-depth filesystem guard. Direct calls to
    builtins.open or io.open outside permitted directories immediately fail fast.
    Call uninstall_worker_filesystem_guard() to restore original behavior.
    """
    global _ORIGINAL_OPEN
    if _ORIGINAL_OPEN is None:
        _ORIGINAL_OPEN = builtins.open
    orig_open = _ORIGINAL_OPEN
    norm_allowed = [
        os.path.normcase(os.path.realpath(os.path.abspath(d)))
        for d in (allowed_dirs or []) if d
    ]

    def guarded_open(file, mode="r", *args, **kwargs):
        # Allow internal standard descriptors or Python machinery
        if isinstance(file, int):
            return orig_open(file, mode, *args, **kwargs)

        try:
            target = os.path.normcase(os.path.realpath(os.path.abspath(str(file))))
        except Exception:
            raise DirectIOException(f"Direct filesystem access to '{file}' rejected by worker guard.")

        # Check if file resides in allowed_dirs (e.g. child's scratch directory)
        is_allowed = False
        for root in norm_allowed:
            try:
                if os.path.commonpath([root, target]) == root:
                    is_allowed = True
                    break
            except (ValueError, OSError):
                continue

        if not is_allowed:
            raise DirectIOException(
                f"Direct filesystem access to '{file}' is forbidden in sandbox. "
                f"Use HostMediatedFilesystemService for authorized file access."
            )

        return orig_open(file, mode, *args, **kwargs)

    builtins.open = guarded_open


def install_worker_network_guard() -> None:
    """
    Installs worker-level defense-in-depth network guard. Direct raw socket
    connect attempts immediately fail fast.
    Call uninstall_worker_network_guard() to restore original behavior.
    """
    global _ORIGINAL_SOCKET_CONNECT
    if _ORIGINAL_SOCKET_CONNECT is None:
        _ORIGINAL_SOCKET_CONNECT = socket.socket.connect

    def guarded_connect(self, address):
        raise DirectIOException(
            f"Direct raw socket connection to '{address}' is forbidden in sandbox. "
            f"Use HostMediatedNetworkService and canonical RouteSpec for authorized network access."
        )

    socket.socket.connect = guarded_connect
