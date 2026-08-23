"""
akaalEngine.connection.security
===============================
Security, redaction, ephemeral secret consumption, authentication managers, and TLS builders.
"""

from akaalEngine.connection.security.redaction import (
    redact_text,
    redact_url,
    redact_mapping,
    redact_sequence,
    is_sensitive_key,
    SafeReprMixin,
    REDACTED_PLACEHOLDER,
)

from akaalEngine.connection.security.secret_consumer import (
    ResolvedSecret,
    SecretConsumer,
    SecretResolverCallback,
    default_secret_consumer,
)

from akaalEngine.connection.security.authentication import (
    AuthenticationHandler,
    PasswordAuthenticationHandler,
    CertificateAuthenticationHandler,
    TokenAuthenticationHandler,
    CloudIAMAuthenticationHandler,
    AuthenticationManager,
)

from akaalEngine.connection.security.tls import (
    TLSContextBuilder,
)

__all__ = [
    # Redaction
    "redact_text",
    "redact_url",
    "redact_mapping",
    "redact_sequence",
    "is_sensitive_key",
    "SafeReprMixin",
    "REDACTED_PLACEHOLDER",
    # Secret Consumer
    "ResolvedSecret",
    "SecretConsumer",
    "SecretResolverCallback",
    "default_secret_consumer",
    # Authentication
    "AuthenticationHandler",
    "PasswordAuthenticationHandler",
    "CertificateAuthenticationHandler",
    "TokenAuthenticationHandler",
    "CloudIAMAuthenticationHandler",
    "AuthenticationManager",
    # TLS
    "TLSContextBuilder",
]
