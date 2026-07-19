"""
Akaal Coverage Tracer — JSON Formatter
======================================
Serializes coverage metrics, summaries, and missing line details to structured JSON.
"""

import json
from dataclasses import asdict
from typing import Any, Dict, List
from akaal.coverage.metrics import CoverageSummary, ModuleMetrics, PackageMetrics, MissingLineDetail


class JSONReportFormatter:
    """Renders structured JSON coverage reports."""

    @classmethod
    def format_report(
        cls,
        summary: CoverageSummary,
        modules: List[ModuleMetrics],
        packages: List[PackageMetrics],
        missing_details: List[MissingLineDetail],
    ) -> str:
        data: Dict[str, Any] = {
            "summary": {
                "target_name": summary.target_name,
                "timestamp": summary.timestamp,
                "python_version": summary.python_version,
                "operating_system": summary.operating_system,
                "execution_duration_sec": summary.execution_duration_sec,
                "total_packages": summary.total_packages,
                "total_modules": summary.total_modules,
                "total_classes": summary.total_classes,
                "total_functions": summary.total_functions,
                "total_executable_statements": summary.total_executable_statements,
                "executed_statements": summary.executed_statements,
                "missing_executable_statements": summary.missing_executable_statements,
                "overall_coverage_pct": summary.overall_coverage_pct,
                "overall_classification": summary.overall_classification.value,
                "lowest_covered_module": summary.lowest_covered_module,
                "highest_covered_module": summary.highest_covered_module,
                "average_package_coverage": summary.average_package_coverage,
                "modules_below_threshold": summary.modules_below_threshold,
                "packages_below_threshold": summary.packages_below_threshold,
            },
            "packages": [
                {
                    "package_name": p.package_name,
                    "total_modules": p.total_modules,
                    "executable_statements": p.executable_statements,
                    "executed_statements": p.executed_statements,
                    "coverage_pct": p.coverage_pct,
                    "classification": p.classification.value,
                    "average_module_coverage": p.average_module_coverage,
                }
                for p in packages
            ],
            "modules": [
                {
                    "module_name": m.module_name,
                    "rel_filepath": m.rel_filepath,
                    "executable_statements": m.executable_statements,
                    "executed_statements": m.executed_statements,
                    "missing_statements": m.missing_statements,
                    "coverage_pct": m.coverage_pct,
                    "classification": m.classification.value,
                    "class_count": m.class_count,
                    "function_count": m.function_count,
                    "missing_lines": m.missing_lines,
                }
                for m in sorted(modules, key=lambda x: x.coverage_pct)
            ],
            "missing_coverage_details": [
                {
                    "module_name": md.module_name,
                    "coverage_pct": md.coverage_pct,
                    "classification": md.classification.value,
                    "priority": md.priority.value,
                    "missing_line_numbers": md.missing_line_numbers,
                    "reason": md.reason,
                }
                for md in sorted(missing_details, key=lambda x: x.coverage_pct)
            ],
        }
        return json.dumps(data, indent=2)
