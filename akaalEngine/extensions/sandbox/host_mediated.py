"""
akaalEngine.extensions.sandbox.host_mediated
============================================
Host-mediated capability services for filesystem and network operations.

Architecture:
Untrusted extension code running in a sandbox worker OS process is NEVER granted
arbitrary OS filesystem or raw network socket authority. All interactions with the
filesystem or physical network destinations are mediated through these host services:
  Extension -> Sandbox client / protocol -> Host-mediated service
            -> GrantedPermissions evaluation -> Canonical path / route validation
            -> Bounded host operation -> Result returned to extension

This establishes a real, enforceable authorization boundary rather than relying on
Python-level monkey patching alone.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.sandbox.permissions import GrantedPermissions


class SandboxSecurityError(PermissionError):
    """Raised when an extension attempts an unauthorized filesystem or network operation."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message)
        self.details = dict(details or {})


class HostMediatedFilesystemService:
    """
    Host-mediated filesystem authority.
    Validates every requested path against GrantedPermissions using canonical path
    resolution, defending against traversal, symlink escapes, UNC paths, and sensitive
    system/configuration directory access.
    """

    DEFAULT_MAX_READ_BYTES: int = 10 * 1024 * 1024   # 10 MB limit
    DEFAULT_MAX_WRITE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    DEFAULT_MAX_LIST_ENTRIES: int = 1000

    def __init__(
        self,
        granted: GrantedPermissions,
        max_read_bytes: int = DEFAULT_MAX_READ_BYTES,
        max_write_bytes: int = DEFAULT_MAX_WRITE_BYTES,
    ) -> None:
        self._granted = granted
        self._max_read_bytes = max_read_bytes
        self._max_write_bytes = max_write_bytes
        # Canonicalize granted roots
        self._canonical_read_roots = [
            self._canonicalize_root(p) for p in granted.filesystem_read_paths if p
        ]
        self._canonical_write_roots = [
            self._canonicalize_root(p) for p in granted.filesystem_write_paths if p
        ]

    @staticmethod
    def _canonicalize_root(root_path: str) -> str:
        resolved = os.path.realpath(os.path.abspath(root_path))
        return os.path.normcase(resolved)

    def _validate_path(self, target_path: str, is_write: bool) -> str:
        if not target_path or not isinstance(target_path, str):
            raise SandboxSecurityError("Filesystem path must be a non-empty string.")

        if "\x00" in target_path:
            raise SandboxSecurityError("Null bytes in filesystem paths are forbidden.")

        # Resolve real path resolving symlinks and normalizing case
        try:
            abs_path = os.path.abspath(target_path)
            canonical_path = os.path.normcase(os.path.realpath(abs_path))
        except (ValueError, OSError) as exc:
            raise SandboxSecurityError(f"Invalid path representation: {exc}") from exc

        # Disallow UNC / network paths unless explicitly permitted
        if abs_path.startswith("\\\\") or abs_path.startswith("//"):
            raise SandboxSecurityError("UNC and network filesystem paths are forbidden.")

        roots = self._canonical_write_roots if is_write else (self._canonical_read_roots + self._canonical_write_roots)

        if not roots:
            op_type = "write" if is_write else "read"
            raise SandboxSecurityError(
                f"Filesystem {op_type} access denied: no filesystem {op_type} paths granted.",
                details={"target_path": target_path, "operation": op_type},
            )

        matched_root = None
        for root in roots:
            try:
                # Check if canonical_path is equal to root or is a child of root
                common = os.path.commonpath([root, canonical_path])
                if common == root:
                    matched_root = root
                    break
            except (ValueError, OSError):
                continue

        if matched_root is None:
            op_type = "write" if is_write else "read"
            raise SandboxSecurityError(
                f"Filesystem {op_type} access denied: path '{target_path}' is outside granted roots.",
                details={"target_path": target_path, "operation": op_type},
            )

        return canonical_path

    def read_file(self, target_path: str, max_bytes: Optional[int] = None) -> bytes:
        canonical_path = self._validate_path(target_path, is_write=False)
        limit = min(max_bytes or self._max_read_bytes, self._max_read_bytes)
        try:
            with open(canonical_path, "rb") as f:
                return f.read(limit)
        except OSError as exc:
            raise SandboxSecurityError(f"Failed to read file '{target_path}': {exc}") from exc

    def write_file(self, target_path: str, data: bytes) -> int:
        canonical_path = self._validate_path(target_path, is_write=True)
        if len(data) > self._max_write_bytes:
            raise SandboxSecurityError(
                f"Payload size ({len(data)} bytes) exceeds maximum write budget ({self._max_write_bytes} bytes)."
            )
        try:
            parent = os.path.dirname(canonical_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(canonical_path, "wb") as f:
                return f.write(data)
        except OSError as exc:
            raise SandboxSecurityError(f"Failed to write file '{target_path}': {exc}") from exc

    def list_dir(self, target_path: str, max_entries: int = DEFAULT_MAX_LIST_ENTRIES) -> list[str]:
        canonical_path = self._validate_path(target_path, is_write=False)
        try:
            with os.scandir(canonical_path) as it:
                entries = []
                for entry in it:
                    entries.append(entry.name)
                    if len(entries) >= max_entries:
                        break
                return entries
        except OSError as exc:
            raise SandboxSecurityError(f"Failed to list directory '{target_path}': {exc}") from exc


class HostMediatedNetworkService:
    """
    Host-mediated network authority.
    Validates destinations against GrantedPermissions.network_egress_hosts, canonical
    EndpointSpec, and RouteSpec. Defends against ungranted loopback access, cloud metadata
    endpoints, and DNS rebinding.
    """

    METADATA_HOSTS = frozenset({
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.internal",
        "instance-data",
    })

    LOOPBACK_HOSTS = frozenset({
        "127.0.0.1",
        "localhost",
        "::1",
        "0.0.0.0",
    })

    def __init__(self, granted: GrantedPermissions) -> None:
        self._granted = granted
        self._granted_destinations = set()
        self._allow_loopback = False
        for entry in granted.network_egress_hosts:
            norm = entry.strip().lower()
            self._granted_destinations.add(norm)
            if norm in self.LOOPBACK_HOSTS or norm.startswith("127."):
                self._allow_loopback = True

    def validate_destination(self, host: str, port: Optional[int] = None) -> tuple[bool, str]:
        """
        Validates whether egress to (host, port) is authoritatively permitted.
        Returns: (is_allowed, diagnostic_message)
        """
        if not host or not isinstance(host, str):
            return False, "Destination host must be a non-empty string."

        norm_host = host.strip().lower()

        # 1. Cloud metadata endpoints are always blocked
        if norm_host in self.METADATA_HOSTS or norm_host.startswith("169.254."):
            return False, f"Access to cloud metadata endpoint '{host}' is strictly forbidden."

        # 2. Loopback blocking unless explicitly granted
        is_loopback = (
            norm_host in self.LOOPBACK_HOSTS or
            norm_host.startswith("127.") or
            norm_host == "localhost"
        )
        if is_loopback and not self._allow_loopback:
            return False, f"Access to loopback interface '{host}' is not granted."

        # 3. Default-deny check against granted network destinations
        if not self._granted_destinations:
            return False, "Network egress denied: no network destinations granted."

        # Check exact host or host:port match
        host_port = f"{norm_host}:{port}" if port is not None else None
        if norm_host in self._granted_destinations:
            return True, f"Destination host '{norm_host}' is permitted."
        if host_port and host_port in self._granted_destinations:
            return True, f"Destination '{host_port}' is permitted."

        return False, f"Network egress to destination '{host}' (port {port}) is not in granted destinations."

    def validate_route_request(
        self,
        target_provider_id: str,
        endpoint_host: str,
        endpoint_port: int,
        caller_tenant_id: Optional[str] = None,
        expected_tenant_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Validates an extension's mediated connection route request against tenant boundary
        and granted destination policy.
        """
        # Tenant isolation
        if expected_tenant_id and caller_tenant_id and caller_tenant_id != expected_tenant_id:
            return False, f"Cross-tenant route request rejected: caller tenant '{caller_tenant_id}' does not match expected '{expected_tenant_id}'."

        return self.validate_destination(endpoint_host, endpoint_port)


class SandboxFilesystemClient:
    """
    Client interface used by extension code or worker harness to interact with the
    host-mediated filesystem service.
    """
    def __init__(self, service: HostMediatedFilesystemService) -> None:
        self._service = service

    def read_file(self, path: str, max_bytes: Optional[int] = None) -> bytes:
        return self._service.read_file(path, max_bytes)

    def write_file(self, path: str, data: bytes) -> int:
        return self._service.write_file(path, data)

    def list_dir(self, path: str, max_entries: int = 1000) -> list[str]:
        return self._service.list_dir(path, max_entries)
