"""
akaalEngine.extensions.compatibility.evaluator
==============================================
Compatibility evaluator verifying extension, provider, and contract versions against engine and authority requirements.
"""

from __future__ import annotations

from typing import Optional

from akaalEngine.extensions.compatibility.ranges import VersionRangeMatcher
from akaalEngine.extensions.compatibility.semver import SemVer
from akaalEngine.extensions.models.compatibility import (
    CompatibilityRange,
    CompatibilityResult,
    CompatibilityStatus,
)


class CompatibilityEvaluator:
    """
    Evaluates version compatibility against configured SemVer range expressions.
    """

    @classmethod
    def evaluate(
        cls,
        target_name: str,
        version_str: str,
        required_range: CompatibilityRange | str,
    ) -> CompatibilityResult:
        """
        Evaluates whether version_str satisfies required_range.
        Returns a structured CompatibilityResult.
        """
        range_obj = required_range if isinstance(required_range, CompatibilityRange) else CompatibilityRange(required_range)
        try:
            target_ver = SemVer.parse(version_str)
            matcher = VersionRangeMatcher(range_obj.raw_expression)
            is_ok = matcher.matches(target_ver)

            if is_ok:
                return CompatibilityResult(
                    target_name=target_name,
                    target_version=str(target_ver),
                    required_range=range_obj,
                    status=CompatibilityStatus.COMPATIBLE,
                    is_compatible=True,
                )
            else:
                return CompatibilityResult(
                    target_name=target_name,
                    target_version=str(target_ver),
                    required_range=range_obj,
                    status=CompatibilityStatus.RANGE_MISMATCH,
                    is_compatible=False,
                    diagnostic=f"{target_name} version '{version_str}' does not satisfy required range '{range_obj.raw_expression}'.",
                )
        except Exception as exc:
            return CompatibilityResult(
                target_name=target_name,
                target_version=version_str,
                required_range=range_obj,
                status=CompatibilityStatus.PARSE_ERROR,
                is_compatible=False,
                diagnostic=f"Failed to evaluate compatibility for {target_name}: {exc}",
            )


default_compatibility_evaluator = CompatibilityEvaluator()
