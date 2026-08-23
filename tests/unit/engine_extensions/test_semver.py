"""
tests.unit.engine_extensions.test_semver
========================================
Tests for SemVer parsing, comparisons, range matchers, and malformed version rejection.
"""

import pytest
from akaalEngine.extensions.compatibility.semver import SemVer
from akaalEngine.extensions.compatibility.ranges import VersionRangeMatcher
from akaalEngine.extensions.compatibility.evaluator import CompatibilityEvaluator


def test_semver_parsing_and_comparisons():
    v1 = SemVer.parse("1.2.3")
    assert v1.major == 1 and v1.minor == 2 and v1.patch == 3
    assert str(v1) == "1.2.3"

    v2 = SemVer.parse("1.2.4")
    v3 = SemVer.parse("1.3.0")
    v4 = SemVer.parse("2.0.0")

    assert v1 < v2
    assert v2 < v3
    assert v3 < v4
    assert v1 <= v1
    assert v4 > v1
    assert v1 == SemVer(1, 2, 3)

    # Prereleases
    v_pre = SemVer.parse("1.0.0-alpha.1")
    v_norm = SemVer.parse("1.0.0")
    assert v_pre < v_norm


def test_semver_malformed_rejection():
    with pytest.raises(ValueError):
        SemVer.parse("invalid-semver")
    with pytest.raises(ValueError):
        SemVer.parse("")
    with pytest.raises(ValueError):
        SemVer.parse("1.2.3.4.5")


def test_version_range_matching():
    matcher_star = VersionRangeMatcher("*")
    assert matcher_star.matches("1.0.0")
    assert matcher_star.matches("99.99.99")

    matcher_caret = VersionRangeMatcher("^1.2.0")
    assert matcher_caret.matches("1.2.0")
    assert matcher_caret.matches("1.2.5")
    assert matcher_caret.matches("1.9.0")
    assert not matcher_caret.matches("2.0.0")
    assert not matcher_caret.matches("1.1.9")

    matcher_tilde = VersionRangeMatcher("~1.2.0")
    assert matcher_tilde.matches("1.2.0")
    assert matcher_tilde.matches("1.2.9")
    assert not matcher_tilde.matches("1.3.0")

    matcher_range = VersionRangeMatcher(">=1.0.0, <2.0.0")
    assert matcher_range.matches("1.0.0")
    assert matcher_range.matches("1.9.9")
    assert not matcher_range.matches("2.0.0")
    assert not matcher_range.matches("0.9.9")

    matcher_hyphen = VersionRangeMatcher("1.0.0 - 2.0.0")
    assert matcher_hyphen.matches("1.0.0")
    assert matcher_hyphen.matches("2.0.0")
    assert matcher_hyphen.matches("1.5.0")
    assert not matcher_hyphen.matches("2.0.1")


def test_compatibility_evaluator():
    res_ok = CompatibilityEvaluator.evaluate("TestPkg", "1.5.0", ">=1.0.0, <2.0.0")
    assert res_ok.is_compatible
    assert res_ok.status.value == "COMPATIBLE"

    res_fail = CompatibilityEvaluator.evaluate("TestPkg", "2.1.0", ">=1.0.0, <2.0.0")
    assert not res_fail.is_compatible
    assert res_fail.status.value == "RANGE_MISMATCH"
    assert "does not satisfy" in (res_fail.diagnostic or "")
