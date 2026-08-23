"""
akaalEngine.connection.security.secret_consumer
===============================================
Ephemeral secret reference resolution, bounded lifetime execution, rotation notification,
and zero-persistence credential handling.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    SecretResolutionError,
)
from akaalEngine.connection.security.redaction import redact_text, REDACTED_PLACEHOLDER

logger = logging.getLogger("akaalEngine.connection.security")


@dataclass
class ResolvedSecret:
    """
    Ephemeral in-memory container for a resolved credential.
    Provides explicit wipe/cleanup semantics to prevent long-lived credential retention.
    """
    secret_value: str
    reference_id: str
    version: str = "1"
    resolved_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    _wiped: bool = False

    def __enter__(self) -> ResolvedSecret:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.wipe()

    def get_value(self) -> str:
        if self._wiped:
            raise RuntimeError(f"Secret reference '{self.reference_id}' has already been wiped from memory.")
        if self.expires_at and time.time() > self.expires_at:
            self.wipe()
            raise RuntimeError(f"Secret reference '{self.reference_id}' has expired.")
        return self.secret_value

    def wipe(self) -> None:
        """Overwrites internal string memory representation where possible and marks as wiped."""
        self._wiped = True
        self.secret_value = ""

    def is_valid(self) -> bool:
        if self._wiped:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True

    def __repr__(self) -> str:
        return f"ResolvedSecret(reference_id='{self.reference_id}', version='{self.version}', wiped={self._wiped})"

    def __str__(self) -> str:
        return self.__repr__()


@runtime_checkable
class SecretResolverCallback(Protocol):
    """Callable protocol to resolve a secret reference string to plaintext."""
    def __call__(self, reference_id: str, context: Optional[dict[str, Any]] = None) -> str: ...


class InMemorySecretResolver:
    """
    Explicit in-memory secret resolver for test fixtures and development environments.
    Explicitly separates reference semantics from secret value resolution.
    """
    def __init__(self, secrets: Optional[dict[str, str]] = None) -> None:
        self._secrets: dict[str, str] = dict(secrets or {})

    def set_secret(self, reference_id: str, secret_value: str) -> None:
        self._secrets[reference_id] = secret_value

    def remove_secret(self, reference_id: str) -> None:
        self._secrets.pop(reference_id, None)

    def __call__(self, reference_id: str, context: Optional[dict[str, Any]] = None) -> str:
        if reference_id in self._secrets:
            return self._secrets[reference_id]
        raise KeyError(f"Secret reference '{reference_id}' not found in in-memory resolver store.")


class SecretConsumer:
    """
    Bounded ephemeral secret consumer for Connection Authority.
    Does NOT persist raw secrets; resolves them immediately before driver consumption.
    Enforces strict fail-closed resolution: unresolved secret references raise typed errors.
    """

    def __init__(self, resolver: Optional[SecretResolverCallback] = None) -> None:
        self._resolver = resolver
        self._rotation_callbacks: list[Callable[[str, str], None]] = []

    def set_resolver(self, resolver: Optional[SecretResolverCallback]) -> None:
        """Sets the active system secret resolver callback."""
        self._resolver = resolver

    def register_resolver(self, resolver: Optional[SecretResolverCallback]) -> None:
        """Alias for set_resolver."""
        self.set_resolver(resolver)

    def register_rotation_listener(self, callback: Callable[[str, str], None]) -> None:
        """Registers a listener to be notified when a secret reference is rotated."""
        self._rotation_callbacks.append(callback)

    def notify_rotation(self, secret_ref: str, new_version: str) -> None:
        """Notifies all registered listeners (e.g. pools) that a secret has rotated."""
        logger.info(f"[SecretConsumer] Secret rotation notification for ref: '{secret_ref}', new version: '{new_version}'")
        for cb in self._rotation_callbacks:
            try:
                cb(secret_ref, new_version)
            except Exception as exc:
                logger.error(f"[SecretConsumer] Error in rotation callback: {redact_text(str(exc))}")

    def resolve(
        self,
        secret_ref: Optional[str],
        version: str = "1",
        ttl_seconds: float = 60.0,
        context: Optional[dict[str, Any]] = None,
    ) -> Optional[ResolvedSecret]:
        """
        Resolves an ephemeral secret reference with bounded in-memory lifetime.
        If secret_ref is None or empty, returns None.
        If secret_ref cannot be resolved, fails closed with SecretResolutionError.
        """
        if not secret_ref:
            return None

        # 1. Use custom resolver callback if registered
        if self._resolver is not None:
            try:
                val = self._resolver(secret_ref, context)
                return ResolvedSecret(
                    secret_value=val,
                    reference_id=secret_ref,
                    version=version,
                    expires_at=time.time() + ttl_seconds,
                )
            except Exception as exc:
                msg = f"Failed to resolve secret reference '{secret_ref}': {redact_text(str(exc))}"
                failure = ConnectionFailure(
                    error_code="SECRET_RESOLUTION_FAILED",
                    category=FailureCategory.AUTHENTICATION_FAILURE,
                    message=msg,
                    retryable=False,
                    provider_id="security",
                    remediation="Verify secret reference exists and is accessible in the vault/store.",
                )
                raise SecretResolutionError(failure) from exc

        # 2. No resolver configured: Fail closed! (Zero plaintext fallback)
        msg = (
            f"No SecretResolver configured to resolve secret reference '{secret_ref}'. "
            f"Plaintext fallback is disabled. Configure a valid SecretResolverCallback."
        )
        failure = ConnectionFailure(
            error_code="SECRET_RESOLVER_UNCONFIGURED",
            category=FailureCategory.AUTHENTICATION_FAILURE,
            message=msg,
            retryable=False,
            provider_id="security",
            remediation="Register a SecretResolverCallback on SecretConsumer or provide an InMemorySecretResolver.",
        )
        raise SecretResolutionError(failure)


def create_testing_consumer(secrets: Optional[dict[str, str]] = None) -> SecretConsumer:
    """Convenience helper to create a SecretConsumer backed by an InMemorySecretResolver for tests."""
    resolver = InMemorySecretResolver(secrets or {})
    return SecretConsumer(resolver=resolver)


# Global default secret consumer instance (fails closed by default)
default_secret_consumer = SecretConsumer()
