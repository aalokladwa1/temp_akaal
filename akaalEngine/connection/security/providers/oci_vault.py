"""akaalEngine.connection.security.providers.oci_vault
========================================================
P7B.4 -- OCI Vault secret provider.

Real oci-SDK-backed client implementing the SecretResolverCallback protocol (see
akaalEngine.connection.security.providers.vault_provider for the sanctioned extension
pattern this mirrors).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Dict, Optional

from akaalEngine.connection.security.redaction import redact_text


class OCIVaultError(RuntimeError):
    """Raised on any OCI Vault resolution failure. Message is redacted."""


@dataclass(frozen=True)
class OCIVaultConfig:
    compartment_ocid: str


class OCIVaultProvider:
    """SecretResolverCallback-compatible OCI Vault (Secrets Retrieval) client wrapper."""

    def __init__(self, config: OCIVaultConfig, client=None) -> None:
        self.config = config
        if not config.compartment_ocid.startswith("ocid1.compartment."):
            raise OCIVaultError(f"compartment_ocid must start with 'ocid1.compartment.'; got {config.compartment_ocid!r}")
        if client is None:
            raise OCIVaultError(
                "No OCI secrets.SecretsClient instance supplied; production resolution "
                "requires an authenticated client constructed by the caller's OCI workload "
                "identity flow (see akaalEngine.fabric.workload_identity.oci)."
            )
        self._client = client

    def __call__(self, reference_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        return self.resolve(reference_id)

    def resolve(self, reference_id: str) -> str:
        """`reference_id` is the secret OCID (ocid1.vaultsecret...)."""
        if not reference_id.startswith("ocid1.vaultsecret."):
            raise OCIVaultError(f"OCI Vault reference_id must be a secret OCID; got {reference_id!r}")

        try:
            response = self._client.get_secret_bundle(secret_id=reference_id)
        except Exception as exc:
            status = getattr(exc, "status", None)
            if status in (401, 403):
                raise OCIVaultError(f"Access denied resolving OCI secret {reference_id!r}: {redact_text(str(exc))}") from exc
            if status == 404:
                raise OCIVaultError(f"OCI secret {reference_id!r} not found.") from exc
            if status == 429:
                raise OCIVaultError(f"OCI Vault throttled resolving {reference_id!r}: {redact_text(str(exc))}") from exc
            raise OCIVaultError(f"OCI Vault resolution failed for {reference_id!r}: {redact_text(str(exc))}") from exc

        data = getattr(response, "data", response)
        content = getattr(data, "secret_bundle_content", None)
        b64_content = getattr(content, "content", None) if content is not None else None
        if not b64_content:
            raise OCIVaultError(f"OCI secret {reference_id!r} resolved with no bundle content.")

        return base64.b64decode(b64_content).decode("utf-8")
