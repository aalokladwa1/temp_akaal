"""
Akaal Coverage Tracer — Markdown Formatter
==========================================
Generates GitHub-flavored Markdown reports with tables, alert blocks, and missing line breakdowns.
"""

from typing import List
from akaal.coverage.metrics import CoverageSummary, ModuleMetrics, PackageMetrics, MissingLineDetail


class MarkdownReportFormatter:
    """Renders formatted GitHub-flavored Markdown reports."""

    @classmethod
    def format_report(
        cls,
        summary: CoverageSummary,
        modules: List[ModuleMetrics],
        packages: List[PackageMetrics],
        missing_details: List[MissingLineDetail],
    ) -> str:
        lines: List[str] = []
        lines.extend([
            f"# AKAAL Official Enterprise Coverage Report — {summary.target_name}",
            "",
            "> [!NOTE]",
            f"> **Execution Environment**: OS: `{summary.operating_system}` | Python: `{summary.python_version}` | Duration: `{summary.execution_duration_sec:.2f}s` | Timestamp: `{summary.timestamp}`",
            "",
            "## 1. Executive Summary",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| **Overall Statement Coverage** | **`{summary.overall_coverage_pct:.1f}%`** (`{summary.overall_classification.value}`) |",
            f"| **Executed Statements** | `{summary.executed_statements}` / `{summary.total_executable_statements}` |",
            f"| **Missing Executable Statements** | `{summary.missing_executable_statements}` |",
            f"| **Total Packages / Modules** | `{summary.total_packages}` Packages / `{summary.total_modules}` Modules |",
            f"| **Total Classes / Functions** | `{summary.total_classes}` Classes / `{summary.total_functions}` Functions |",
            f"| **Lowest Covered Module** | `{summary.lowest_covered_module}` |",
            f"| **Highest Covered Module** | `{summary.highest_covered_module}` |",
            f"| **Average Package Coverage** | `{summary.average_package_coverage:.1f}%` |",
            "",
            "## 2. Package Coverage Summary",
            "",
            "| Package Name | Modules | Executed Statements | Total Statements | Coverage % | Status |",
            "| --- | --- | --- | --- | --- | --- |",
        ])

        for p in sorted(packages, key=lambda pkg: pkg.coverage_pct):
            lines.append(
                f"| `{p.package_name}` | `{p.total_modules}` | `{p.executed_statements}` | `{p.executable_statements}` | `{p.coverage_pct:.1f}%` | `{p.classification.value}` |"
            )

        lines.extend([
            "",
            "## 3. Module Coverage Breakdown (Sorted Lowest -> Highest Coverage)",
            "",
            "| Module File | Executed Statements | Total Statements | Coverage % | Status | Classes | Functions |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])

        sorted_modules = sorted(modules, key=lambda m: m.coverage_pct)
        for m in sorted_modules:
            lines.append(
                f"| `{m.rel_filepath}` | `{m.executed_statements}` | `{m.executable_statements}` | `{m.coverage_pct:.1f}%` | `{m.classification.value}` | `{m.class_count}` | `{m.function_count}` |"
            )

        lines.extend([
            "",
            "## 4. Missing Coverage Line Details",
            "",
        ])

        if missing_details:
            lines.extend([
                "| Module Name | Coverage % | Priority | Missing Line Numbers | Reason / Assessment |",
                "| --- | --- | --- | --- | --- |",
            ])
            for md in sorted(missing_details, key=lambda d: d.coverage_pct):
                missing_str = ", ".join(map(str, md.missing_line_numbers)) if md.missing_line_numbers else "None"
                lines.append(
                    f"| `{md.module_name}` | `{md.coverage_pct:.1f}%` (`{md.classification.value}`) | `{md.priority.value}` | `{missing_str}` | {md.reason} |"
                )
        else:
            lines.append("_No modules below target threshold._")

        lines.extend([
            "",
            "---",
            "_Report generated automatically by AKAAL Official Enterprise Coverage Tracer._",
        ])

        return "\n".join(lines)
