"""
Unit tests for Audit Package Builder.
"""

import pytest
from akaal.reporting.audit.builder import AuditPackageBuilder
from akaal.reporting.reports.premigration import PreMigrationReport
from akaal.reporting.reports.progress import MigrationProgressReport


def test_audit_package_builder():
    builder = AuditPackageBuilder()
    gen1 = PreMigrationReport()
    gen2 = MigrationProgressReport()

    art1 = gen1.generate("mig-99", {}, {})
    art2 = gen2.generate("mig-99", {"rows_copied": 100, "total_rows": 1000})

    pkg = builder.build_package("mig-99", [art1, art2], [b"payload1", b"payload2"])
    assert pkg.migration_id == "mig-99"
    assert pkg.reports_count == 2
    assert len(pkg.manifest_sha256) == 64
    assert pkg.package_signature.startswith("x509:")
