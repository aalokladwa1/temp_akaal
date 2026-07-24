"""
AKAAL Platform 11 — Audit Export Packager.
"""

import datetime
import hashlib
import uuid
from akaal.trust_certification.domain.models import AuditExportPackage


class AuditExportPackager:
    """Exports audit-grade compliance and certification packages."""

    def export_audit_package(self, migration_id: str, format_type: str = "ZIP_JSON") -> AuditExportPackage:
        exp_id = f"exp-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        export_hash = hashlib.sha256(f"{migration_id}:{format_type}:{now}".encode('utf-8')).hexdigest()

        return AuditExportPackage(
            export_id=exp_id,
            target_migration_id=migration_id,
            archive_format=format_type,
            export_hash=export_hash,
            exported_at=now,
        )
