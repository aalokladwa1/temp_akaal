"""akaalEngine.intelligence.gateway.http_adapter
=================================================
P7C.4 -- the REAL production model endpoint adapter (Blocker-2 closure). A
generic, provider-independent governed HTTP endpoint invoker -- NOT coupled to
any single commercial vendor's SDK, so it can truthfully address organization-
hosted, private, or cloud model endpoints alike, per the P7C brief's own model
gateway law.

This module performs REAL network I/O via `httpx` (already a repository
dependency -- verified present, no new dependency added) against whatever
`endpoint_url` its `GovernedEndpointConfig` names: given a real reachable
endpoint and a real secret, it issues a genuine outbound HTTP call and parses
whatever comes back -- no canned or invented response anywhere in this file.
What this environment lacks is a *live commercial/private model endpoint and
credentials* -- that specific absence is EXTERNAL_DEFERRED (see module-level
tests, which exercise this adapter against a real local loopback HTTP server
instead, proving the actual transport/serialization/error-mapping stack).

Secrets: `secret_resolver` is injected (never owned) -- in production it closes
over the repository's real secret authority (akaalEngine.connection.security.
secret_consumer). The resolved secret value is used exactly once, for exactly
one outbound header, and is NEVER placed in any exception message, log record,
returned response, or persisted artifact -- `_redact` scrubs it defensively
from any error text as a second layer even though the primary discipline is
"never construct a string containing it" in the first place.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional

from akaalEngine.intelligence.models.errors import IntelligenceError


class ModelEndpointError(IntelligenceError):
    code = "MODEL_ENDPOINT_ERROR"


class ModelEndpointAuthenticationError(ModelEndpointError):
    """401/403 from the endpoint -- credentials rejected."""

    code = "MODEL_ENDPOINT_AUTHENTICATION_FAILED"


class ModelEndpointRateLimitedError(ModelEndpointError):
    """429 from the endpoint. `retry_after_seconds` is populated from the
    Retry-After header when the endpoint supplies one, never guessed."""

    code = "MODEL_ENDPOINT_RATE_LIMITED"

    def __init__(self, message: str, *, retry_after_seconds: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ModelEndpointUnavailableError(ModelEndpointError):
    """5xx from the endpoint -- classified retryable; caller/gateway may retry
    or fail over to another policy-permitted provider (never a prohibited one)."""

    code = "MODEL_ENDPOINT_UNAVAILABLE"
    retryable = True


class ModelEndpointRequestRejectedError(ModelEndpointError):
    """Other 4xx -- the request itself was rejected (not a credential/rate
    problem); not retryable without changing the request."""

    code = "MODEL_ENDPOINT_REQUEST_REJECTED"
    retryable = False


class ModelEndpointTimeoutError(ModelEndpointError):
    code = "MODEL_ENDPOINT_TIMEOUT"
    retryable = True


class ModelEndpointConnectionError(ModelEndpointError):
    code = "MODEL_ENDPOINT_CONNECTION_FAILED"
    retryable = True


class ModelEndpointResponseParsingError(ModelEndpointError):
    """The endpoint returned 2xx but the body was not parseable/well-formed
    per the structured-output contract -- never silently coerced into an
    invented successful result (P7C brief 'hostile structured-output boundary')."""

    code = "MODEL_ENDPOINT_RESPONSE_MALFORMED"


SecretResolver = Callable[[str], str]


@dataclass(frozen=True)
class GovernedEndpointConfig:
    endpoint_url: str
    provider: str
    model_id: str
    model_version: str
    secret_reference: str
    deployment_id: Optional[str] = None
    region: Optional[str] = None
    timeout_seconds: float = 30.0
    verify_tls: bool = True
    max_response_bytes: int = 5_000_000

    def __post_init__(self) -> None:
        if not self.endpoint_url:
            raise ValueError("GovernedEndpointConfig.endpoint_url cannot be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("GovernedEndpointConfig.timeout_seconds must be positive")
        if not self.secret_reference:
            raise ValueError("GovernedEndpointConfig.secret_reference cannot be empty (no plaintext secrets)")


def _redact(text: str, secret_value: Optional[str]) -> str:
    if secret_value and secret_value in text:
        return text.replace(secret_value, "[REDACTED]")
    return text


@dataclass(frozen=True)
class ModelEndpointResponse:
    status_code: int
    content: Mapping[str, Any]
    usage: Mapping[str, Any] = field(default_factory=dict)
    model_provenance: Mapping[str, Any] = field(default_factory=dict)
    latency_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "status_code": self.status_code,
            "content": dict(self.content),
            "usage": dict(self.usage),
            "model_provenance": dict(self.model_provenance),
            "latency_seconds": self.latency_seconds,
        }


class HTTPModelProviderAdapter:
    """Real production model endpoint adapter over actual HTTP transport."""

    def __init__(self, config: GovernedEndpointConfig, secret_resolver: SecretResolver, *, client: Optional[Any] = None) -> None:
        self.config = config
        self._secret_resolver = secret_resolver
        self._client = client  # injectable for tests; defaults to a real httpx.Client per call

    def invoke(
        self,
        request_payload: Mapping[str, Any],
        *,
        cancellation_token: Optional[Any] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> ModelEndpointResponse:
        import httpx

        if cancellation_token is not None and getattr(cancellation_token, "is_cancelled", lambda: False)():
            from akaalEngine.intelligence.models.errors import IntelligenceCancelledError

            raise IntelligenceCancelledError("Model endpoint invocation was cancelled before dispatch.")

        secret_value = self._secret_resolver(self.config.secret_reference)
        headers = {
            "Authorization": f"Bearer {secret_value}",
            "Content-Type": "application/json",
            "X-Akaal-Model-Id": self.config.model_id,
            "X-Akaal-Model-Version": self.config.model_version,
        }
        if extra_headers:
            headers.update(extra_headers)

        owns_client = self._client is None
        client = self._client or httpx.Client(verify=self.config.verify_tls, timeout=self.config.timeout_seconds)
        start = time.monotonic()
        try:
            try:
                response = client.post(self.config.endpoint_url, json=dict(request_payload), headers=headers)
            except httpx.TimeoutException as exc:
                raise ModelEndpointTimeoutError(
                    _redact(f"Model endpoint request timed out after {self.config.timeout_seconds}s: {exc}", secret_value)
                ) from None
            except httpx.ConnectError as exc:
                raise ModelEndpointConnectionError(
                    _redact(f"Model endpoint connection failed: {exc}", secret_value)
                ) from None
            except httpx.HTTPError as exc:
                raise ModelEndpointError(_redact(f"Model endpoint request failed: {exc}", secret_value)) from None

            latency = time.monotonic() - start

            if response.status_code in (401, 403):
                raise ModelEndpointAuthenticationError(
                    _redact(f"Model endpoint rejected credentials (HTTP {response.status_code}).", secret_value)
                )
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ModelEndpointRateLimitedError(
                    "Model endpoint rate-limited this request (HTTP 429).",
                    retry_after_seconds=float(retry_after) if retry_after and retry_after.isdigit() else None,
                )
            if 500 <= response.status_code < 600:
                raise ModelEndpointUnavailableError(f"Model endpoint returned server error (HTTP {response.status_code}).")
            if 400 <= response.status_code < 500:
                raise ModelEndpointRequestRejectedError(
                    _redact(f"Model endpoint rejected request (HTTP {response.status_code}): {response.text[:500]}", secret_value)
                )

            if len(response.content) > self.config.max_response_bytes:
                raise ModelEndpointResponseParsingError(
                    f"Model endpoint response exceeded max_response_bytes ({self.config.max_response_bytes})."
                )

            try:
                body = response.json()
            except ValueError as exc:
                raise ModelEndpointResponseParsingError(f"Model endpoint returned non-JSON or malformed body: {exc}") from None

            if not isinstance(body, Mapping):
                raise ModelEndpointResponseParsingError("Model endpoint response body must be a JSON object.")

            return ModelEndpointResponse(
                status_code=response.status_code,
                content=body,
                usage=body.get("usage") or {},
                model_provenance={
                    "provider": self.config.provider,
                    "model_id": self.config.model_id,
                    "model_version": self.config.model_version,
                    "deployment_id": self.config.deployment_id,
                    "region": self.config.region,
                },
                latency_seconds=latency,
            )
        finally:
            if owns_client:
                client.close()
