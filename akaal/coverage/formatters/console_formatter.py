"""
Akaal Coverage Tracer — Console Formatter
=========================================
Renders terminal coverage tables sorted from lowest to highest coverage,
missing line breakdowns, and project summaries.
"""

from typing import List
from akaal.coverage.metrics import CoverageSummary, ModuleMetrics, PackageMetrics, MissingLineDetail


class ConsoleReportFormatter:
    """Renders formatted ASCII console reports."""

    @classmethod
    def format_report(
        cls,
        summary: CoverageSummary,
        modules: List[ModuleMetrics],
        packages: List[PackageMetrics],
        missing_details: List[MissingLineDetail],
    ) -> str:
        lines: List[str] = []
        lines.append("\n" + "=" * 85)
        lines.append(f"AKAAL OFFICIAL ENTERPRISE COVERAGE TRACER REPORT — {summary.target_name.upper()}")
        lines.append("=" * 85)
        lines.append(f"Timestamp: {summary.timestamp} | OS: {summary.operating_system} | Python: {summary.python_version}")
        lines.append(f"Execution Duration: {summary.execution_duration_sec:.2f}s | Target: {summary.target_name}")
        lines.append("-" * 85)
        lines.append(f"Overall Coverage: {summary.overall_coverage_pct:.1f}% [{summary.overall_classification.value}]")
        lines.append(f"Statements: {summary.executed_statements} / {summary.total_executable_statements} executed ({summary.missing_executable_statements} missing)")
        lines.append(f"Scope: {summary.total_packages} Packages | {summary.total_modules} Modules | {summary.total_classes} Classes | {summary.total_functions} Functions")
        lines.append(f"Lowest Module: {summary.lowest_covered_module} | Highest Module: {summary.highest_covered_module}")
        lines.append("=" * 85)

        # Module Table (Sorted lowest to highest coverage)
        lines.append(f"\nMODULE COVERAGE BREAKDOWN (Sorted Lowest -> Highest Coverage):")
        lines.append(f"{'FILE / MODULE':<48} | {'EXEC':<5} | {'TOTAL':<5} | {'COV %':<7} | {'STATUS'}")
        lines.append("-" * 85)

        sorted_modules = sorted(modules, key=lambda m: m.coverage_pct)
        for m in sorted_modules:
            lines.append(
                f"{m.rel_filepath:<48} | {m.executed_statements:<5} | {m.executable_statements:<5} | {m.coverage_pct:>5.1f}% | {m.classification.value}"
            )
        lines.append("-" * 85)

        # Package Summary Table
        lines.append(f"\nPACKAGE COVERAGE SUMMARY:")
        lines.append(f"{'PACKAGE NAME':<40} | {'MODS':<5} | {'EXEC':<5} | {'TOTAL':<5} | {'COV %':<7} | {'STATUS'}")
        lines.append("-" * 85)
        for p in sorted(packages, key=lambda pkg: pkg.coverage_pct):
            lines.append(
                f"{p.package_name:<40} | {p.total_modules:<5} | {p.executed_statements:<5} | {p.executable_statements:<5} | {p.coverage_pct:>5.1f}% | {p.classification.value}"
            )
        lines.append("-" * 85)

        # Missing Lines Breakdown
        if missing_details:
            lines.append(f"\nMISSING COVERAGE LINE BREAKDOWN (Modules Below Target Threshold):")
            lines.append("=" * 85)
            for md in sorted(missing_details, key=lambda d: d.coverage_pct):
                missing_str = ", ".join(map(str, md.missing_line_numbers)) if md.missing_line_numbers else "None"
                lines.append(f"Module: {md.module_name}")
                lines.append(f"  Coverage: {md.coverage_pct:.1f}% [{md.classification.value}] | Priority: {md.priority.value}")
                lines.append(f"  Missing Line Numbers: {missing_str}")
                lines.append(f"  Reason / Assessment: {md.reason}")
                lines.append("-" * 45)

        lines.append("=" * 85 + "\n")
        return "\n".join(lines)
