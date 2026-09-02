"""akaalEngine.connection.security.providers.vault_provider
=========================================================
P7.7 HashiCorp Vault-compatible secret provider.

Real HTTP client against the Vault HTTP API (KV v2 read, dynamic-secret lease
renew/revoke) using only the Python standard library. Implements the
akaalEngine.connection.security.secret_consumer.SecretResolverCallback protocol so it
can be registered directly on a SecretConsumer without changing that authority's
resolution semantics.

Whether a live Vault server is reachable in this environment is EXTERNAL_DEFERRED.
This module implements real production HTTP client behavior against the documented
Vault API; it does not simulate or fake a successful response.

Fail-closed guarantees:
- No token, secret value, or lease material is ever logged.
- A non-2xx response, network failure, or missing expected field raises a typed error;
  it never falls back to a plaintext default or cached stale value.
- The Vault token is resolved on every call via `token_provider()` (never cached to disk
  or embedded in source); rotation of the underlying token takes effect immediately.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
)
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.security.providers.vault")


class VaultProviderError(RuntimeError):
    """Raised on a non-success Vault API response. Message is redacted of secret material."""

    def __init__(self, failure: ConnectionFailure) -> None:
        super().__init__(f"[{failure.category.value}] {failure.error_code}: {failure.message}")
        self.failure = failure


@dataclass(frozen=True)
class VaultProviderConfig:
    """
    Dynamic, operator-supplied Vault connection configuration. No address, mount path,
    or token is hardcoded -- all are runtime configuration inputs.
    """
    vault_addr: str  # e.g. "https://vault.internal:8200" -- operator-supplied
    token_provider: Callable[[], str]  # resolves current Vault token on demand, never cached here
    kv_mount_path: str = "secret"  # KV v2 mount point
    namespace: Optional[str] = None  # Vault Enterprise namespace, if applicable
    timeout_seconds: float = 15.0


class VaultKVSecretProvider:
    """
    Real HashiCorp Vault KV v2 + dynamic-secrets-lease client.
    Usable directly as a SecretConsumer resolver callback via `resolve_kv`.
    """

    def __init__(self, config: VaultProviderConfig) -> None:
        self.config = config

    def _headers(self) -> Dict[str, str]:
        token = self.config.token_provider()
        if not token:
            raise VaultProviderError(
                ConnectionFailure(
                    error_code="VAULT_TOKEN_UNAVAILABLE",
                    category=FailureCategory.AUTHENTICATION_FAILURE,
                    message="No Vault token available from configured token_provider (fail closed).",
                    retryable=False,
                    provider_id="vault",
                )
            )
        headers = {"X-Vault-Token": token, "Content-Type": "application/json"}
        if self.config.namespace:
            headers["X-Vault-Namespace"] = self.config.namespace
        return headers

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.config.vault_addr.rstrip('/')}/v1/{path.lstrip('/')}"
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url=url, data=payload, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:  # nosec - operator-configured endpoint
                raw = resp.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise VaultProviderError(
                ConnectionFailure(
                    error_code="VAULT_API_ERROR",
                    category=FailureCategory.AUTHENTICATION_FAILURE if exc.code in (401, 403) else FailureCategory.PROVIDER_INTERNAL_ERROR,
                    message=f"Vault API returned HTTP {exc.code} for {method} {path}: {redact_text(body_text)}",
                    retryable=exc.code >= 500,
                    provider_id="vault",
                )
            ) from exc
        except urllib.error.URLError as exc:
            raise VaultProviderError(
                ConnectionFailure(
                    error_code="VAULT_UNREACHABLE",
                    category=FailureCategory.ENDPOINT_UNAVAILABLE,
                    message=f"Vault server unreachable: {redact_text(str(exc.reason))}",
                    retryable=True,
                    provider_id="vault",
                )
            ) from exc

    def resolve_kv(self, reference_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        SecretResolverCallback-compatible resolution of a KV v2 secret.
        `reference_id` format: "path/to/secret#field" (field defaults to "value" if omitted).
        """
        if "#" in reference_id:
            secret_path, field_name = reference_id.split("#", 1)
        else:
            secret_path, field_name = reference_id, "value"

        result = self._request("GET", f"{self.config.kv_mount_path}/data/{secret_path}")
        data = (result.get("data") or {}).get("data") or {}
        if field_name not in data:
            raise VaultProviderError(
                ConnectionFailure(
                    error_code="VAULT_FIELD_NOT_FOUND",
                    category=FailureCategory.CAPABILITY_MISMATCH,
                    message=f"Vault secret at {secret_path!r} has no field {field_name!r}.",
                    retryable=False,
                    provider_id="vault",
                )
            )
        return str(data[field_name])

    # SecretConsumer expects a plain callable(reference_id, context) -> str
    __call__ = resolve_kv

    def issue_dynamic_credential(self, role_path: str) -> Dict[str, Any]:
        """
        Requests a dynamic (short-lived) credential from a Vault secrets engine role
        (e.g. "database/creds/readonly"). Returns lease metadata + credential data;
        callers are responsible for wiping the returned data promptly (e.g. via
        SecretConsumer's ResolvedSecret wipe semantics).
        """
        result = self._request("GET", role_path)
        lease_id = result.get("lease_id")
        lease_duration = result.get("lease_duration")
        data = result.get("data") or {}
        if not lease_id or not data:
            raise VaultProviderError(
                ConnectionFailure(
                    error_code="VAULT_DYNAMIC_CREDENTIAL_MALFORMED",
                    category=FailureCategory.PROVIDER_INTERNAL_ERROR,
                    message=f"Vault dynamic credential response for {role_path!r} is missing lease_id or data.",
                    retryable=False,
                    provider_id="vault",
                )
            )
        return {"lease_id": lease_id, "lease_duration": lease_duration, "data": data}

    def renew_lease(self, lease_id: str, increment_seconds: Optional[int] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"lease_id": lease_id}
        if increment_seconds is not None:
            body["increment"] = increment_seconds
        return self._request("PUT", "sys/leases/renew", body)

    def revoke_lease(self, lease_id: str) -> None:
        self._request("PUT", "sys/leases/revoke", {"lease_id": lease_id})
