"""akaalEngine.connection.security.providers.gcp_secret_manager
=================================================================
P7B.4 -- Google Cloud Secret Manager secret provider.

Real google-cloud-secret-manager-backed client implementing the SecretResolverCallback
protocol (see akaalEngine.connection.security.providers.vault_provider for the sanctioned
extension pattern this mirrors).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from akaalEngine.connection.security.redaction import redact_text


class GCPSecretManagerError(RuntimeError):
    """Raised on any GCP Secret Manager resolution failure. Message is redacted."""


@dataclass(frozen=True)
class GCPSecretManagerConfig:
    project_id: str


class GCPSecretManagerProvider:
    """SecretResolverCallback-compatible GCP Secret Manager client wrapper."""

    def __init__(self, config: GCPSecretManagerConfig, client=None) -> None:
        self.config = config
        if not config.project_id:
            raise GCPSecretManagerError("GCPSecretManagerConfig.project_id is required.")
        if client is not None:
            self._client = client
        else:
            try:
                from google.cloud import secretmanager
            except ImportError as exc:
                raise GCPSecretManagerError(
                    "'google-cloud-secret-manager' is not installed; cannot resolve GCP secrets."
                ) from exc
            self._client = secretmanager.SecretManagerServiceClient()

    def __call__(self, reference_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        return self.resolve(reference_id)

    def resolve(self, reference_id: str) -> str:
        """`reference_id` is the secret short name, optionally with '/versions/<n>' (default 'latest')."""
        if "/versions/" in reference_id:
            name, version_part = reference_id.split("/versions/", 1)
            version = version_part
        else:
            name, version = reference_id, "latest"

        resource_name = f"projects/{self.config.project_id}/secrets/{name}/versions/{version}"

        try:
            response = self._client.access_secret_version(name=resource_name)
        except Exception as exc:
            msg = str(exc)
            if "NotFound" in msg or "404" in msg:
                raise GCPSecretManagerError(f"GCP secret {resource_name!r} not found.") from exc
            if "PermissionDenied" in msg or "403" in msg:
                raise GCPSecretManagerError(f"Access denied resolving GCP secret {resource_name!r}: {redact_text(msg)}") from exc
            if "ResourceExhausted" in msg or "429" in msg:
                raise GCPSecretManagerError(f"GCP Secret Manager throttled resolving {resource_name!r}: {redact_text(msg)}") from exc
            raise GCPSecretManagerError(f"GCP Secret Manager resolution failed for {resource_name!r}: {redact_text(msg)}") from exc

        payload = getattr(response, "payload", None)
        data = getattr(payload, "data", None) if payload is not None else None
        if not data:
            raise GCPSecretManagerError(f"GCP secret {resource_name!r} resolved with no payload data.")

        return data.decode("utf-8") if isinstance(data, bytes) else str(data)
