"""
akaalEngine.extensions.sandbox
===============================
Real, truthfully-scoped extension execution isolation: capability-based permission
requests distinct from grants, and a real OS-process sandbox boundary (SUBPROCESS
isolation mode). WASM/REMOTE isolation remain honestly unimplemented -- no WASM
runtime or remote worker infrastructure exists in this repository or environment.
"""

from akaalEngine.extensions.sandbox.host_mediated import (
    HostMediatedFilesystemService,
    HostMediatedNetworkService,
    SandboxFilesystemClient,
    SandboxSecurityError,
)
from akaalEngine.extensions.sandbox.permissions import (
    GrantedPermissions,
    IsolationAssurance,
    PermissionKind,
    PermissionRequest,
    assurance_satisfies,
    stricter_assurance,
)
from akaalEngine.extensions.sandbox.process_isolation import (
    SandboxExecutionResult,
    SubprocessSandbox,
)
from akaalEngine.extensions.sandbox.worker_guards import (
    DirectIOException,
    install_worker_filesystem_guard,
    install_worker_network_guard,
    uninstall_worker_filesystem_guard,
    uninstall_worker_network_guard,
)

__all__ = [
    "PermissionKind",
    "PermissionRequest",
    "GrantedPermissions",
    "IsolationAssurance",
    "assurance_satisfies",
    "stricter_assurance",
    "SubprocessSandbox",
    "SandboxExecutionResult",
    "HostMediatedFilesystemService",
    "HostMediatedNetworkService",
    "SandboxFilesystemClient",
    "SandboxSecurityError",
    "DirectIOException",
    "install_worker_filesystem_guard",
    "install_worker_network_guard",
    "uninstall_worker_filesystem_guard",
    "uninstall_worker_network_guard",
]
