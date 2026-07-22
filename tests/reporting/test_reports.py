"""
Unit tests for Platform 8 Report Generators.
"""

import pytest
from akaal.reporting.reports.cutover import CutoverReport
from akaal.reporting.reports.executive import ExecutiveSummaryReport
from akaal.reporting.reports.postmigration import PostMigrationReport
from akaal.reporting.reports.premigration import PreMigrationReport
from akaal.reporting.reports.progress import MigrationProgressReport
from akaal.reporting.reports.validation import GBValidationReport


def test_premigration_report():
    gen = PreMigrationReport()
    art = gen.generate("mig-101", {"table_count": 50}, {"db_name": "target_db"})
    assert art.metadata.report_type == "PRE_MIGRATION"
    assert len(art.sections) == 2


def test_progress_report():
    gen = MigrationProgressReport()
    art = gen.generate("mig-101", {"rows_copied": 2500000, "total_rows": 10000000})
    assert art.metadata.report_type == "PROGRESS"
    assert art.summary_metrics["completion_percentage"] == 25.0


def test_gb_validation_report():
    gen = GBValidationReport()
    art = gen.generate("mig-101", {"status": "PASSED", "mismatches": 0})
    assert art.metadata.report_type == "GB_VALIDATION"
    assert art.summary_metrics["verification_status"] == "PASSED"


def test_cutover_report():
    gen = CutoverReport()
    art = gen.generate("mig-101", {"downtime_minutes": 10, "rollback_ready": True})
    assert art.metadata.report_type == "CUTOVER"


def test_postmigration_report():
    gen = PostMigrationReport()
    art = gen.generate("mig-101", {"final_row_count": 10000000})
    assert art.metadata.report_type == "POST_MIGRATION"


def test_executive_summary_report():
    gen = ExecutiveSummaryReport()
    art = gen.generate("mig-101", {"success_rate": "99.999%"})
    assert art.metadata.report_type == "EXECUTIVE_SUMMARY"
