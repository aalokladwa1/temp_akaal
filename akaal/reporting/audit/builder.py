"""
Enterprise Audit Package Builder & Integrity Manifest Generator.
"""

from typing import List, Optional
import base64
import datetime
import hashlib
import json
import uuid

from akaal.reporting.contracts.dto import AuditPackageDTO, ReportArtifactDTO
from akaal.reporting.models.report import ReportArtifact
from akaal.reporting.signing.base import ISigningProvider
from akaal.reporting.signing.x509 import X509SigningProvider


class AuditPackageBuilder:
    """Enterprise Audit Package Builder."""

    def __init__(self, signing_provider: Optional[ISigningProvider] = None) -> None:
        self.signer = signing_provider or X509SigningProvider()

    def build_package(self, migration_id: str, artifacts: List[ReportArtifact], raw_payloads: List[bytes]) -> AuditPackageDTO:
        package_id = f"aud-pkg-{uuid.uuid4().hex[:10]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        report_dtos = []
        manifest_hashes = []

        for art, payload in zip(artifacts, raw_payloads):
            h = hashlib.sha256(payload).hexdigest()
            sig = self.signer.sign_payload(payload)
            b64_content = base64.b64encode(payload).decode("utf-8")

            dto = ReportArtifactDTO(
                report_id=art.metadata.report_id,
                report_type=art.metadata.report_type,
                format=art.format,
                content_b64=b64_content,
                checksum_sha256=h,
                generated_at=art.metadata.generated_at,
                signature=sig,
            )
            report_dtos.append(dto)
            manifest_hashes.append(f"{art.metadata.report_id}:{h}")

        # Hash-chain manifest computation
        manifest_str = f"MANIFEST:{migration_id}:{':'.join(manifest_hashes)}"
        manifest_sha = hashlib.sha256(manifest_str.encode("utf-8")).hexdigest()
        package_sig = self.signer.sign_payload(manifest_str.encode("utf-8"))

        return AuditPackageDTO(
            package_id=package_id,
            migration_id=migration_id,
            reports_count=len(report_dtos),
            manifest_sha256=manifest_sha,
            artifacts=report_dtos,
            package_signature=package_sig,
            timestamp=now,
        )
