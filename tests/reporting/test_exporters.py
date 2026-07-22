"""
Unit tests for Report Exporters (PDF, HTML, JSON, CSV).
"""

import pytest
from akaal.reporting.exporters.csv import CSVExporter
from akaal.reporting.exporters.html import HTMLExporter
from akaal.reporting.exporters.json import JSONExporter
from akaal.reporting.exporters.pdf import PDFExporter
from akaal.reporting.reports.premigration import PreMigrationReport


def test_all_exporters():
    gen = PreMigrationReport()
    art = gen.generate("mig-202", {"table_count": 10}, {"db_name": "target"})

    html_exp = HTMLExporter()
    json_exp = JSONExporter()
    csv_exp = CSVExporter()
    pdf_exp = PDFExporter()

    html_bytes = html_exp.export(art)
    assert b"<!DOCTYPE html>" in html_bytes

    json_bytes = json_exp.export(art)
    assert b"metadata" in json_bytes

    csv_bytes = csv_exp.export(art)
    assert b"Section,Title,Content" in csv_bytes

    pdf_bytes = pdf_exp.export(art)
    assert pdf_bytes.startswith(b"%PDF-1.7")
