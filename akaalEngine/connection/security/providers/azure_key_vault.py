"""akaalEngine.connection.security.providers.azure_key_vault
==============================================================
P7B.4 -- Azure Key Vault secret provider.

Real azure-keyvault-secrets-backed client implementing the SecretResolverCallback
protocol (see akaalEngine.connection.security.providers.vault_provider for the sanctioned
extension pattern this mirrors).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from akaalEngine.connection.security.redaction import redact_text


class AzureKeyVaultError(RuntimeError):
    """Raised on any Azure Key Vault resolution failure. Message is redacted."""


@dataclass(frozen=True)
class AzureKeyVaultConfig:
    vault_url: str  # e.g. "https://myvault.vault.azure.net/"


class AzureKeyVaultProvider:
    """SecretResolverCallback-compatible Azure Key Vault client wrapper."""

    def __init__(self, config: AzureKeyVaultConfig, client=None, credential=None) -> None:
        self.config = config
        if client is not None:
            self._client = client
        else:
            try:
                from azure.keyvault.secrets import SecretClient
            except ImportError as exc:
                raise AzureKeyVaultError(
                    "'azure-keyvault-secrets' is not installed; cannot resolve Azure Key Vault references."
                ) from exc
            if credential is None:
                try:
                    from azure.identity import DefaultAzureCredential
                except ImportError as exc:
                    raise AzureKeyVaultError(
                        "'azure-identity' is not installed; cannot authenticate to Azure Key Vault."
                    ) from exc
                credential = DefaultAzureCredential()
            self._client = SecretClient(vault_url=config.vault_url, credential=credential)

    def __call__(self, reference_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        return self.resolve(reference_id)

    def resolve(self, reference_id: str) -> str:
        """`reference_id` is the Key Vault secret name, optionally with '/version'."""
        name, _, version = reference_id.partition("/")

        try:
            secret = self._client.get_secret(name, version=version or None)
        except Exception as exc:
            msg = str(exc)
            if "SecretNotFound" in msg or "404" in msg:
                raise AzureKeyVaultError(f"Azure Key Vault secret {name!r} not found.") from exc
            if "Forbidden" in msg or "403" in msg or "Unauthorized" in msg or "401" in msg:
                raise AzureKeyVaultError(f"Access denied resolving Azure Key Vault secret {name!r}: {redact_text(msg)}") from exc
            if "429" in msg or "TooManyRequests" in msg:
                raise AzureKeyVaultError(f"Azure Key Vault throttled resolving {name!r}: {redact_text(msg)}") from exc
            raise AzureKeyVaultError(f"Azure Key Vault resolution failed for {name!r}: {redact_text(msg)}") from exc

        if secret is None or getattr(secret, "value", None) is None:
            raise AzureKeyVaultError(f"Azure Key Vault secret {name!r} resolved with no value.")

        properties = getattr(secret, "properties", None)
        if properties is not None and getattr(properties, "enabled", True) is False:
            raise AzureKeyVaultError(f"Azure Key Vault secret {name!r} is disabled; refusing to return a disabled secret's value.")

        return secret.value
