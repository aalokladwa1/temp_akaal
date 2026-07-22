"""
Unit tests for Report Version Manager and Metadata Manager.
"""

import pytest
from akaal.reporting.metadata.manager import MetadataManager
from akaal.reporting.reports.premigration import PreMigrationReport
from akaal.reporting.versioning.manager import ReportVersionManager


def test_metadata_manager():
    mgr = MetadataManager()
    meta = mgr.create_metadata("Title", "PRE_MIGRATION", migration_id="mig-1", correlation_id="c-123")
    assert meta.title == "Title"
    assert meta.correlation_id == "c-123"

    checksum = mgr.compute_checksum(b"test data")
    assert len(checksum) == 64


def test_version_manager():
    v_mgr = ReportVersionManager()
    gen = PreMigrationReport()
    art = gen.generate("mig-1", {}, {})
    art.metadata.report_id = "same-report-id"

    v1 = v_mgr.register_version(art)
    assert v1.version_string == "1.0.0"

    v2 = v_mgr.register_version(art)
    assert v2.version_string == "1.1.0"

    history = v_mgr.get_version_history("same-report-id")
    assert len(history) == 2
