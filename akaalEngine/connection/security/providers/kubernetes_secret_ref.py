"""akaalEngine.connection.security.providers.kubernetes_secret_ref
====================================================================
P7B.4 -- Controlled Kubernetes Secret references.

Reads secret material from the standard Kubernetes Secret-volume-mount filesystem
convention (a Secret projected as a file under a mount path), which is the safe,
zero-additional-RBAC way for a workload to consume its own bound Secrets -- it does NOT
call the Kubernetes API server directly (that would require broader `secrets: get`
RBAC than a workload should need for its own mounted Secrets, and would duplicate
kubelet's own Secret-projection mechanism).

Fail-closed guarantees:
- Every reference is resolved only under an explicit, caller-configured allowlist of
  mount roots -- refuses any reference_id that would resolve (after normalization)
  outside that allowlist, blocking path traversal (`../../etc/shadow`-style references).
- A missing file, a directory, or an unreadable file all raise a typed error; none of
  them fall back to a default or empty string.
- Round-6 hostile-review closure: the literal (pre-symlink-resolution) path is checked
  against the allowlist AND, separately, the fully symlink-resolved real path
  (`os.path.realpath`) is checked against the allowlist a second time -- a symlink
  placed inside an allowed mount root that points OUTSIDE it (directly, or through a
  chain of nested symlinks) is now rejected before the file is ever opened, closing the
  real escape this module previously only disclosed rather than closed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


class KubernetesSecretRefError(RuntimeError):
    """Raised on any Kubernetes Secret-reference resolution failure."""


@dataclass(frozen=True)
class KubernetesSecretRefConfig:
    allowed_mount_roots: Tuple[str, ...] = field(default_factory=lambda: ("/var/run/secrets/akaal",))


class KubernetesSecretRefProvider:
    """SecretResolverCallback-compatible Kubernetes Secret-volume-mount reader."""

    def __init__(self, config: Optional[KubernetesSecretRefConfig] = None) -> None:
        self.config = config or KubernetesSecretRefConfig()
        if not self.config.allowed_mount_roots:
            raise KubernetesSecretRefError("KubernetesSecretRefConfig.allowed_mount_roots must be non-empty.")

    def __call__(self, reference_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        return self.resolve(reference_id)

    def resolve(self, reference_id: str) -> str:
        """`reference_id` is a path relative to one of the configured allowed mount roots,
        e.g. 'db-credentials/password'."""
        if not reference_id or reference_id.strip() != reference_id:
            raise KubernetesSecretRefError(f"Malformed Kubernetes secret reference_id: {reference_id!r}")

        resolved_path: Optional[str] = None
        for root in self.config.allowed_mount_roots:
            candidate = os.path.normpath(os.path.join(root, reference_id))
            root_normalized = os.path.normpath(root)
            # Path-traversal guard: candidate must remain strictly inside the allowed root.
            if candidate == root_normalized or candidate.startswith(root_normalized + os.sep):
                resolved_path = candidate
                break

        if resolved_path is None:
            raise KubernetesSecretRefError(
                f"Kubernetes secret reference {reference_id!r} does not resolve under any "
                f"configured allowed_mount_roots {self.config.allowed_mount_roots!r}; refusing "
                f"(path-traversal guard)."
            )

        # Round-6 hostile-review closure: the literal path passed the string-prefix
        # check above, but that check says nothing about what the path ACTUALLY points
        # to if any component of it (or the file itself) is a symlink. Resolve it fully
        # (following every symlink in the chain, including nested ones) and re-check the
        # REAL destination against the same allowlist -- a symlink escape is rejected
        # here even though the literal reference string looked legitimate.
        real_resolved_path = os.path.realpath(resolved_path)
        real_root_allowed = any(
            real_resolved_path == os.path.realpath(root) or real_resolved_path.startswith(os.path.realpath(root) + os.sep)
            for root in self.config.allowed_mount_roots
        )
        if not real_root_allowed:
            raise KubernetesSecretRefError(
                f"Kubernetes secret reference {reference_id!r} resolves (after following "
                f"symlinks) to {real_resolved_path!r}, which is OUTSIDE every configured "
                f"allowed_mount_root; refusing (symlink-escape guard). If this reference is "
                f"expected to be a legitimate symlink, the platform-level mount (Kubernetes "
                f"projected-secret volume semantics, not this in-process check) is the "
                f"correct place to guarantee it cannot point outside the pod's own secret "
                f"volume -- this function fails closed rather than assume that guarantee "
                f"holds when it cannot verify it directly."
            )

        if not os.path.isfile(resolved_path):
            raise KubernetesSecretRefError(f"Kubernetes secret file not found or is not a regular file: {reference_id!r}")

        try:
            with open(resolved_path, "r", encoding="utf-8") as fh:
                return fh.read().rstrip("\n")
        except OSError as exc:
            raise KubernetesSecretRefError(f"Failed to read Kubernetes secret file {reference_id!r}: {exc}") from exc
