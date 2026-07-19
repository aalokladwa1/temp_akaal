"""
Akaal Coverage Tracer — Metrics & Classification Models
========================================================
Defines coverage models, threshold classification rules, and priority assignment algorithms.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set


class CoverageClassification(Enum):
    PASS = "PASS"                       # 95-100%
    GOOD = "GOOD"                       # 90-94%
    ACCEPTABLE = "ACCEPTABLE"           # 80-89%
    NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT" # 70-79%
    CRITICAL = "CRITICAL"               # Below 70%

    @classmethod
    def classify(cls, percentage: float) -> "CoverageClassification":
        p = round(percentage, 1)
        if p >= 95.0:
            return cls.PASS
        elif p >= 90.0:
            return cls.GOOD
        elif p >= 80.0:
            return cls.ACCEPTABLE
        elif p >= 70.0:
            return cls.NEEDS_IMPROVEMENT
        else:
            return cls.CRITICAL


class MissingLinePriority(Enum):
    HIGH = "HIGH"       # Core engine/validator/registry or <70% coverage
    MEDIUM = "MEDIUM"   # 70-89% coverage
    LOW = "LOW"          # >=90% coverage


@dataclass
class MissingLineDetail:
    """Missing coverage details for a specific module."""
    module_name: str
    filepath: str
    coverage_pct: float
    classification: CoverageClassification
    missing_line_numbers: List[int]
    priority: MissingLinePriority
    reason: str


@dataclass
class ModuleMetrics:
    """Coverage metrics for a single module."""
    module_name: str
    filepath: str
    rel_filepath: str
    total_lines: int
    executable_statements: int
    executed_statements: int
    missing_statements: int
    coverage_pct: float
    classification: CoverageClassification
    class_count: int
    function_count: int
    missing_lines: List[int]


@dataclass
class PackageMetrics:
    """Aggregated coverage metrics for a package."""
    package_name: str
    total_modules: int
    executable_statements: int
    executed_statements: int
    coverage_pct: float
    classification: CoverageClassification
    average_module_coverage: float


@dataclass
class CoverageSummary:
    """Repository or platform-wide summary metrics."""
    target_name: str
    timestamp: str
    python_version: str
    operating_system: str
    execution_duration_sec: float
    total_packages: int
    total_modules: int
    total_classes: int
    total_functions: int
    total_executable_statements: int
    executed_statements: int
    missing_executable_statements: int
    overall_coverage_pct: float
    overall_classification: CoverageClassification
    lowest_covered_module: str
    highest_covered_module: str
    average_package_coverage: float
    modules_below_threshold: int
    packages_below_threshold: int
