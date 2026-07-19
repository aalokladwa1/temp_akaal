"""
AKAAL Official Enterprise Coverage Infrastructure Package
=========================================================
Exports official enterprise coverage tracer components and reporting engine.
"""

from akaal.coverage.ast_analyzer import ASTSourceAnalyzer, SourceAnalysis
from akaal.coverage.collector import CoverageCollector
from akaal.coverage.metrics import (
    CoverageClassification,
    CoverageSummary,
    MissingLineDetail,
    MissingLinePriority,
    ModuleMetrics,
    PackageMetrics,
)
from akaal.coverage.tracer import AKAALCoverageTracer

__all__ = [
    "AKAALCoverageTracer",
    "ASTSourceAnalyzer",
    "CoverageCollector",
    "CoverageClassification",
    "CoverageSummary",
    "ModuleMetrics",
    "PackageMetrics",
    "MissingLineDetail",
    "MissingLinePriority",
    "SourceAnalysis",
]
