"""akaalEngine.connection.security.providers.aws_secrets_manager
=================================================================
P7B.4 -- AWS Secrets Manager secret provider.

Real boto3-backed client implementing the
akaalEngine.connection.security.secret_consumer.SecretResolverCallback protocol, so it
can be registered directly on a SecretConsumer without changing that authority's
resolution semantics -- this is the sanctioned P7.7 extension point (see
secret_consumer.py's module docstring), not a new secret authority.

Fail-closed guarantees:
- No secret value ever appears in a raised exception message (all provider errors are
  redacted via akaalEngine.connection.security.redaction.redact_text).
- A resource-not-found, access-denied, or throttled response raises a distinct, typed
  error; none of them fall back to a cached or default value.
- account_id, when supplied, is verified against the resolved secret ARN before the
  value is ever returned -- a secret that truthfully lives in a different AWS account
  than the caller declared is refused rather than silently served (P7B "wrong account"
  hostile case, applied at the secrets layer too).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.security.providers.aws_secrets_manager")


class AWSSecretsManagerError(RuntimeError):
    """Raised on any AWS Secrets Manager resolution failure. Message is redacted."""


@dataclass(frozen=True)
class AWSSecretsManagerConfig:
    account_id: Optional[str] = None  # if set, resolved secret ARN account must match
    region_name: Optional[str] = None


class AWSSecretsManagerProvider:
    """SecretResolverCallback-compatible AWS Secrets Manager client wrapper."""

    def __init__(self, config: Optional[AWSSecretsManagerConfig] = None, client=None) -> None:
        self.config = config or AWSSecretsManagerConfig()
        if client is not None:
            self._client = client
        else:
            try:
                import boto3
            except ImportError as exc:
                raise AWSSecretsManagerError(
                    "'boto3' is not installed; cannot resolve AWS Secrets Manager references."
                ) from exc
            self._client = boto3.client("secretsmanager", region_name=self.config.region_name)

    def __call__(self, reference_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        return self.resolve(reference_id)

    def resolve(self, reference_id: str) -> str:
        """`reference_id` is the Secrets Manager secret name or ARN, optionally with
        '#json_key' to select one field out of a JSON secret blob."""
        secret_id, _, json_key = reference_id.partition("#")

        try:
            resp = self._client.get_secret_value(SecretId=secret_id)
        except Exception as exc:
            msg = str(exc)
            if "ResourceNotFoundException" in msg:
                raise AWSSecretsManagerError(f"AWS secret {secret_id!r} not found.") from exc
            if "AccessDeniedException" in msg:
                raise AWSSecretsManagerError(f"Access denied resolving AWS secret {secret_id!r}: {redact_text(msg)}") from exc
            if "ThrottlingException" in msg or "TooManyRequestsException" in msg:
                raise AWSSecretsManagerError(f"AWS Secrets Manager throttled resolving {secret_id!r}: {redact_text(msg)}") from exc
            raise AWSSecretsManagerError(f"AWS Secrets Manager resolution failed for {secret_id!r}: {redact_text(msg)}") from exc

        arn = resp.get("ARN", "")
        if self.config.account_id and arn:
            arn_account = arn.split(":")[4] if arn.count(":") >= 4 else None
            if arn_account and arn_account != self.config.account_id:
                raise AWSSecretsManagerError(
                    f"Secret {secret_id!r} resolved to ARN in account {arn_account!r}, which "
                    f"does not match the configured account_id {self.config.account_id!r}; refusing."
                )

        if "SecretString" in resp:
            value = resp["SecretString"]
        elif "SecretBinary" in resp:
            value = resp["SecretBinary"].decode("utf-8", errors="replace") if isinstance(resp["SecretBinary"], bytes) else str(resp["SecretBinary"])
        else:
            raise AWSSecretsManagerError(f"AWS secret {secret_id!r} response contained neither SecretString nor SecretBinary.")

        if json_key:
            import json as _json
            try:
                parsed = _json.loads(value)
            except Exception as exc:
                raise AWSSecretsManagerError(f"AWS secret {secret_id!r} is not valid JSON; cannot extract key {json_key!r}.") from exc
            if json_key not in parsed:
                raise AWSSecretsManagerError(f"AWS secret {secret_id!r} JSON has no key {json_key!r}.")
            return str(parsed[json_key])

        return value
