"""
akaalEngine.connection.security.tls
==================================
Enforceable TLS context construction, certificate validation, mTLS binding,
peer identity extraction, and SHA-256 certificate fingerprint verification.
"""

from __future__ import annotations

import hashlib
import logging
import os
import ssl
import tempfile
from typing import TYPE_CHECKING, Any, Optional, Tuple

if TYPE_CHECKING:
    from akaalEngine.connection.models.endpoint import TLSBinding

from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    TLSVerificationError,
)
from akaalEngine.connection.security.redaction import redact_text
from akaalEngine.connection.security.secret_consumer import SecretConsumer, default_secret_consumer

logger = logging.getLogger("akaalEngine.connection.security.tls")


class TLSContextBuilder:
    """
    Constructs and configures Python standard ssl.SSLContext instances from TLSBinding.
    """

    def __init__(self, secret_consumer: Optional[SecretConsumer] = None) -> None:
        self.secret_consumer = secret_consumer or default_secret_consumer

    def build_ssl_context(
        self,
        binding: Optional[Any],
        provider_id: str = "generic",
    ) -> Optional[ssl.SSLContext]:
        """
        Builds an ssl.SSLContext based on the TLSBinding mode and certificates.
        Returns None if TLSMode is DISABLED.
        """
        if binding is None:
            return None

        mode_val = binding.mode.value if hasattr(binding.mode, "value") else str(binding.mode).upper()
        if mode_val == "DISABLED":
            return None

        try:
            # 1. Base SSL Context with secure defaults
            ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

            # 2. Min TLS Version
            if hasattr(ssl, "TLSVersion"):
                min_ver = getattr(binding, "tls_min_version", "TLSv1.2")
                if min_ver == "TLSv1.3":
                    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
                else:
                    ctx.minimum_version = ssl.TLSVersion.TLSv1_2

            allow_self_signed = getattr(binding, "allow_self_signed", False)

            # 3. Verification Modes
            if mode_val in ("DISABLED", "PREFERRED"):
                if allow_self_signed:
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
            elif mode_val == "REQUIRED":
                if allow_self_signed:
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                else:
                    ctx.verify_mode = ssl.CERT_REQUIRED
                    ctx.check_hostname = True
            elif mode_val == "VERIFY_CA":
                ctx.verify_mode = ssl.CERT_REQUIRED
                ctx.check_hostname = False
            elif mode_val == "VERIFY_FULL":
                ctx.verify_mode = ssl.CERT_REQUIRED
                ctx.check_hostname = True

            # 4. Custom CA Certificates
            ca_path = getattr(binding, "ca_cert_path", None)
            ca_pem = getattr(binding, "ca_cert_pem", None)
            if ca_path:
                ctx.load_verify_locations(cafile=ca_path)
            elif ca_pem:
                ctx.load_verify_locations(cadata=ca_pem)

            # 5. mTLS Client Certificate & Key
            client_cert = getattr(binding, "client_cert_path", None)
            client_key_ref = getattr(binding, "client_key_ref", None)
            if client_cert:
                key_path = None
                key_file_temp = None
                resolved_key = None
                try:
                    if client_key_ref:
                        resolved_key = self.secret_consumer.resolve(client_key_ref)
                        if resolved_key:
                            fd, temp_path = tempfile.mkstemp(prefix="akaal_mtls_", suffix=".pem")
                            with os.fdopen(fd, "w") as f:
                                f.write(resolved_key.get_value())
                            key_path = temp_path
                            key_file_temp = temp_path
                    ctx.load_cert_chain(certfile=client_cert, keyfile=key_path)
                finally:
                    if resolved_key is not None:
                        resolved_key.wipe()
                    if key_file_temp and os.path.exists(key_file_temp):
                        try:
                            os.remove(key_file_temp)
                        except OSError:
                            pass

            return ctx

        except Exception as exc:
            msg = f"Failed to build TLS context for provider '{provider_id}': {redact_text(str(exc))}"
            failure = ConnectionFailure(
                error_code="TLS_CONTEXT_BUILD_FAILED",
                category=FailureCategory.TLS_FAILURE,
                message=msg,
                retryable=False,
                provider_id=provider_id,
                remediation="Verify CA certificate paths, permissions, and TLS version compatibility.",
            )
            raise TLSVerificationError(failure) from exc

    @staticmethod
    def extract_cert_fingerprint(cert_der: bytes) -> str:
        """Computes SHA-256 fingerprint string from DER-encoded certificate bytes."""
        return hashlib.sha256(cert_der).hexdigest().lower()

    @staticmethod
    def verify_peer_certificate(
        ssl_sock: ssl.SSLSocket,
        expected_fingerprint: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Extracts peer certificate info and verifies expected SHA-256 fingerprint if configured.
        Returns: (is_valid, cipher_name, cert_fingerprint)
        """
        try:
            cipher = ssl_sock.cipher()
            cipher_name = cipher[0] if cipher else None

            peer_cert_der = ssl_sock.getpeercert(binary_form=True)
            cert_fp = None
            if peer_cert_der:
                cert_fp = TLSContextBuilder.extract_cert_fingerprint(peer_cert_der)

            if expected_fingerprint and cert_fp:
                if cert_fp != expected_fingerprint.lower().replace(":", "").strip():
                    logger.warning(
                        f"[TLSContextBuilder] Peer cert fingerprint mismatch: expected {expected_fingerprint}, got {cert_fp}"
                    )
                    return False, cipher_name, cert_fp

            return True, cipher_name, cert_fp
        except Exception as exc:
            logger.error(f"[TLSContextBuilder] Error during peer certificate verification: {redact_text(str(exc))}")
            return False, None, None
