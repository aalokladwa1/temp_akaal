"""
akaalEngine.extensions.compatibility
====================================
Deterministic Semantic Versioning, range matchers, and compatibility evaluation.
"""

from akaalEngine.extensions.compatibility.semver import SemVer
from akaalEngine.extensions.compatibility.ranges import VersionComparator, VersionRangeMatcher
from akaalEngine.extensions.compatibility.evaluator import (
    CompatibilityEvaluator,
    default_compatibility_evaluator,
)

__all__ = [
    "SemVer",
    "VersionComparator",
    "VersionRangeMatcher",
    "CompatibilityEvaluator",
    "default_compatibility_evaluator",
]
