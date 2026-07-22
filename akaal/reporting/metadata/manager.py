"""
Report Metadata & Correlation Manager.
"""

import hashlib
import json
from typing import Optional
from akaal.reporting.models.report import ReportMetadata, ReportVersion


class MetadataManager:
    """Manager for injecting metadata, correlation IDs, timestamps, and SHA-256 checksums."""

    def create_metadata(
        self,
        title: str,
        report_type: str,
        migration_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> ReportMetadata:
        meta = ReportMetadata(
            title=title,
            report_type=report_type,
            migration_id=migration_id,
            version=ReportVersion(major=1, minor=0, patch=0, version_string="1.0.0"),
        )
        if correlation_id:
            meta.correlation_id = correlation_id
        return meta

    def compute_checksum(self, payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()
