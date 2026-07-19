"""
Akaal Official Enterprise Coverage Tracer Engine
================================================
Enterprise-grade coverage orchestrator collecting actual execution metrics via AST parsing
and bytecode tracing. Exporting Console, Markdown, JSON, and CSV reports.
"""

import datetime
import glob
import os
import platform
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

import pytest

from akaal.coverage.ast_analyzer import ASTSourceAnalyzer
from akaal.coverage.collector import CoverageCollector
from akaal.coverage.formatters.console_formatter import ConsoleReportFormatter
from akaal.coverage.formatters.csv_formatter import CSVReportFormatter
from akaal.coverage.formatters.json_formatter import JSONReportFormatter
from akaal.coverage.formatters.markdown_formatter import MarkdownReportFormatter
from akaal.coverage.metrics import (
    CoverageClassification,
    CoverageSummary,
    MissingLineDetail,
    MissingLinePriority,
    ModuleMetrics,
    PackageMetrics,
)


class AKAALCoverageTracer:
    """Enterprise Coverage Tracer for AKAAL Platform."""

    def __init__(
        self,
        target_directory: str,
        target_name: str = "AKAAL Platform",
        threshold_target_pct: float = 90.0,
    ) -> None:
        self.target_directory = os.path.abspath(target_directory)
        self.target_name = target_name
        self.threshold_target_pct = threshold_target_pct

    def run_pytest_and_report(
        self,
        pytest_args: Optional[List[str]] = None,
        output_directory: str = "reports/coverage",
    ) -> Tuple[CoverageSummary, List[ModuleMetrics], List[PackageMetrics], List[MissingLineDetail]]:
        """Run pytest suite under tracer, compute metrics, and export reports."""
        p_args = pytest_args or ["tests/unit/test_advisor_platform.py", "-q"]
        start_time = time.perf_counter()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Collect Execution Trace
        collector = CoverageCollector(self.target_directory)
        executed_map = collector.run_target(pytest.main, p_args)
        duration_sec = time.perf_counter() - start_time

        # 2. Discover Source Files
        pattern = os.path.join(self.target_directory, "**", "*.py")
        all_files = sorted(glob.glob(pattern, recursive=True))

        modules: List[ModuleMetrics] = []
        packages_dict: Dict[str, List[ModuleMetrics]] = {}

        total_executable_stmts = 0
        total_executed_stmts = 0
        total_classes = 0
        total_functions = 0

        # 3. Analyze File Metrics
        for filepath in all_files:
            rel_path = os.path.relpath(filepath, start=os.getcwd())
            analysis = ASTSourceAnalyzer.analyze_file(filepath)

            # Skip __init__.py files with 0 executable statements if desired, or include them
            mod_name = os.path.splitext(os.path.basename(filepath))[0]
            pkg_name = os.path.relpath(os.path.dirname(filepath), start=os.getcwd()).replace(os.sep, ".")

            exec_lines_set = analysis.executable_lines
            num_executable = len(exec_lines_set)

            # Get executed lines recorded for this file
            file_executed_lines = executed_map.get(os.path.abspath(filepath), set())
            num_executed = len(exec_lines_set.intersection(file_executed_lines))

            missing_lines = sorted(list(exec_lines_set - file_executed_lines))
            num_missing = len(missing_lines)

            cov_pct = (num_executed / num_executable * 100.0) if num_executable > 0 else 100.0
            classification = CoverageClassification.classify(cov_pct)

            mod_metrics = ModuleMetrics(
                module_name=mod_name,
                filepath=filepath,
                rel_filepath=rel_path,
                total_lines=analysis.total_lines,
                executable_statements=num_executable,
                executed_statements=num_executed,
                missing_statements=num_missing,
                coverage_pct=cov_pct,
                classification=classification,
                class_count=len(analysis.class_names),
                function_count=len(analysis.function_names),
                missing_lines=missing_lines,
            )

            modules.append(mod_metrics)
            if pkg_name not in packages_dict:
                packages_dict[pkg_name] = []
            packages_dict[pkg_name].append(mod_metrics)

            total_executable_stmts += num_executable
            total_executed_stmts += num_executed
            total_classes += len(analysis.class_names)
            total_functions += len(analysis.function_names)

        # 4. Aggregated Package Metrics
        packages: List[PackageMetrics] = []
        for pkg_name, pkg_mods in packages_dict.items():
            pkg_exec = sum(m.executed_statements for m in pkg_mods)
            pkg_total = sum(m.executable_statements for m in pkg_mods)
            pkg_cov = (pkg_exec / pkg_total * 100.0) if pkg_total > 0 else 100.0
            avg_mod_cov = sum(m.coverage_pct for m in pkg_mods) / len(pkg_mods)

            packages.append(
                PackageMetrics(
                    package_name=pkg_name,
                    total_modules=len(pkg_mods),
                    executable_statements=pkg_total,
                    executed_statements=pkg_exec,
                    coverage_pct=pkg_cov,
                    classification=CoverageClassification.classify(pkg_cov),
                    average_module_coverage=round(avg_mod_cov, 1),
                )
            )

        # 5. Overall Summary
        overall_cov = (total_executed_stmts / total_executable_stmts * 100.0) if total_executable_stmts > 0 else 0.0
        sorted_by_cov = sorted(modules, key=lambda m: m.coverage_pct)
        lowest_mod = f"{sorted_by_cov[0].module_name} ({sorted_by_cov[0].coverage_pct:.1f}%)" if sorted_by_cov else "N/A"
        highest_mod = f"{sorted_by_cov[-1].module_name} ({sorted_by_cov[-1].coverage_pct:.1f}%)" if sorted_by_cov else "N/A"
        avg_pkg_cov = (sum(p.coverage_pct for p in packages) / len(packages)) if packages else 0.0

        mods_below = sum(1 for m in modules if m.coverage_pct < self.threshold_target_pct)
        pkgs_below = sum(1 for p in packages if p.coverage_pct < self.threshold_target_pct)

        summary = CoverageSummary(
            target_name=self.target_name,
            timestamp=timestamp,
            python_version=platform.python_version(),
            operating_system=f"{platform.system()} {platform.release()}",
            execution_duration_sec=round(duration_sec, 2),
            total_packages=len(packages),
            total_modules=len(modules),
            total_classes=total_classes,
            total_functions=total_functions,
            total_executable_statements=total_executable_stmts,
            executed_statements=total_executed_stmts,
            missing_executable_statements=total_executable_stmts - total_executed_stmts,
            overall_coverage_pct=round(overall_cov, 1),
            overall_classification=CoverageClassification.classify(overall_cov),
            lowest_covered_module=lowest_mod,
            highest_covered_module=highest_mod,
            average_package_coverage=round(avg_pkg_cov, 1),
            modules_below_threshold=mods_below,
            packages_below_threshold=pkgs_below,
        )

        # 6. Missing Line Breakdown & Priority
        missing_details: List[MissingLineDetail] = []
        for m in modules:
            if m.coverage_pct < self.threshold_target_pct and m.missing_lines:
                if any(core in m.module_name for core in ("engine", "validator", "registry")) or m.coverage_pct < 70.0:
                    prio = MissingLinePriority.HIGH
                    reason = "Core component or critical coverage level (<70%)"
                elif m.coverage_pct < 85.0:
                    prio = MissingLinePriority.MEDIUM
                    reason = "Needs improvement to reach target 90% threshold"
                else:
                    prio = MissingLinePriority.LOW
                    reason = "Minor unexecuted fallback branches"

                missing_details.append(
                    MissingLineDetail(
                        module_name=m.module_name,
                        filepath=m.rel_filepath,
                        coverage_pct=m.coverage_pct,
                        classification=m.classification,
                        missing_line_numbers=m.missing_lines,
                        priority=prio,
                        reason=reason,
                    )
                )

        # 7. Export Reports
        os.makedirs(output_directory, exist_ok=True)
        md_content = MarkdownReportFormatter.format_report(summary, modules, packages, missing_details)
        json_content = JSONReportFormatter.format_report(summary, modules, packages, missing_details)
        csv_content = CSVReportFormatter.format_report(summary, modules, packages, missing_details)

        with open(os.path.join(output_directory, "coverage_report.md"), "w", encoding="utf-8") as f:
            f.write(md_content)
        with open(os.path.join(output_directory, "coverage_report.json"), "w", encoding="utf-8") as f:
            f.write(json_content)
        with open(os.path.join(output_directory, "coverage_report.csv"), "w", encoding="utf-8") as f:
            f.write(csv_content)

        return summary, modules, packages, missing_details
