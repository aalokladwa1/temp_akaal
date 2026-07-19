"""
Akaal Coverage Tracer — CSV Formatter
=====================================
Exports coverage metrics to CSV format for enterprise CI metrics aggregation.
"""

import csv
import io
from typing import List
from akaal.coverage.metrics import CoverageSummary, ModuleMetrics, PackageMetrics, MissingLineDetail


class CSVReportFormatter:
    """Exports CSV coverage report data."""

    @classmethod
    def format_report(
        cls,
        summary: CoverageSummary,
        modules: List[ModuleMetrics],
        packages: List[PackageMetrics],
        missing_details: List[MissingLineDetail],
    ) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Module Name",
            "File Path",
            "Executed Statements",
            "Total Statements",
            "Missing Statements",
            "Coverage %",
            "Classification",
            "Classes",
            "Functions",
            "Missing Line Numbers",
        ])

        for m in sorted(modules, key=lambda x: x.coverage_pct):
            missing_str = ";".join(map(str, m.missing_lines)) if m.missing_lines else ""
            writer.writerow([
                m.module_name,
                m.rel_filepath,
                m.executed_statements,
                m.executable_statements,
                m.missing_statements,
                f"{m.coverage_pct:.1f}",
                m.classification.value,
                m.class_count,
                m.function_count,
                missing_str,
            ])

        return output.getvalue()
