"""
akaalEngine.extensions.supply_chain.trust_store
================================================
Publisher trust-root registry for third-party extension package signing.

A registered root is a claim by the operator, not a claim by the package.
An artifact's signer certificate must chain to one of these roots for its
package to be admitted -- see PackageIntegrityValidator.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional, Sequence, Set

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from akaalEngine.extensions.errors.taxonomy import PackageCertificateInvalidError


class PublisherTrustStore:
    """
    Thread-safe registry of trusted publisher root certificates and revoked
    signer serial numbers. In-memory only -- durable persistence, if required,
    is the caller's composition-root responsibility (this class holds no I/O).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._roots: Dict[str, x509.Certificate] = {}
        self._revoked_serials: Set[int] = set()

    def register_trust_root(self, root_id: str, root_certificate_pem: str) -> None:
        """Registers a publisher root/intermediate CA certificate as trusted."""
        if not root_id:
            raise ValueError("root_id must not be empty.")
        try:
            cert = x509.load_pem_x509_certificate(root_certificate_pem.encode("utf-8"), default_backend())
        except Exception as exc:
            raise PackageCertificateInvalidError(
                f"Trust root '{root_id}' is not a valid PEM certificate: {exc}"
            ) from exc
        with self._lock:
            self._roots[root_id] = cert

    def revoke_trust_root(self, root_id: str) -> None:
        """Removes a previously-registered trust root. Packages signed by chains through it stop verifying."""
        with self._lock:
            self._roots.pop(root_id, None)

    def revoke_signer_serial(self, serial_number: int) -> None:
        """Marks a specific signer certificate serial number as revoked, independent of its root's status."""
        with self._lock:
            self._revoked_serials.add(serial_number)

    def is_serial_revoked(self, serial_number: int) -> bool:
        with self._lock:
            return serial_number in self._revoked_serials

    def get_trust_anchors(self) -> Sequence[x509.Certificate]:
        with self._lock:
            return tuple(self._roots.values())

    def get_trust_root(self, root_id: str) -> Optional[x509.Certificate]:
        with self._lock:
            return self._roots.get(root_id)


default_publisher_trust_store = PublisherTrustStore()
