"""
akaalEngine.extensions.models.provenance
=========================================
Package provenance/supply-chain identity for third-party extension packages.
Distinct from ExtensionManifest (declared capability contract): this models the
physical package artifact's cryptographic integrity and publisher attribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass(frozen=True)
class PackageProvenance:
    """
    Cryptographic provenance record accompanying a third-party extension package.
    Carries no trust by itself -- PackageIntegrityValidator is the only authority
    that may convert this into an admission decision.
    """
    extension_id: str
    version: str
    artifact_digest_hex: str
    digest_algorithm: str
    signature: bytes
    signer_certificate_pem: str
    intermediate_certificates_pem: Sequence[str] = field(default_factory=tuple)
    publisher_id: str = ""
    signed_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.extension_id:
            raise ValueError("PackageProvenance.extension_id must not be empty.")
        if not self.version:
            raise ValueError("PackageProvenance.version must not be empty.")
        if not self.artifact_digest_hex:
            raise ValueError("PackageProvenance.artifact_digest_hex must not be empty.")
        if self.digest_algorithm != "sha256":
            raise ValueError(f"Unsupported digest_algorithm '{self.digest_algorithm}'; only 'sha256' is supported.")
        if not self.signature:
            raise ValueError("PackageProvenance.signature must not be empty.")
        if not self.signer_certificate_pem:
            raise ValueError("PackageProvenance.signer_certificate_pem must not be empty.")
        object.__setattr__(self, "intermediate_certificates_pem", tuple(self.intermediate_certificates_pem))
