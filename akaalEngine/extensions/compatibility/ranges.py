"""
akaalEngine.extensions.compatibility.ranges
===========================================
SemVer range expression parsing and evaluation.
Supports standard NPM/Cargo style SemVer range operators (^, ~, >=, <=, >, <, =, -, *).
"""

from __future__ import annotations

import re
from typing import Callable, List, Tuple

from akaalEngine.extensions.compatibility.semver import SemVer


class VersionComparator:
    """Evaluates a single operator comparator (e.g. '>=1.0.0', '<2.0.0', '=1.5.0')."""
    def __init__(self, operator: str, target_ver: SemVer) -> None:
        self.operator = operator
        self.target_ver = target_ver

    def matches(self, ver: SemVer) -> bool:
        if self.operator in ("=", "=="):
            return ver == self.target_ver
        elif self.operator == ">":
            return ver > self.target_ver
        elif self.operator == ">=":
            return ver >= self.target_ver
        elif self.operator == "<":
            return ver < self.target_ver
        elif self.operator == "<=":
            return ver <= self.target_ver
        elif self.operator == "!=":
            return ver != self.target_ver
        return False

    def __str__(self) -> str:
        return f"{self.operator}{self.target_ver}"


class VersionRangeMatcher:
    """
    Parses and evaluates complex SemVer range expressions.
    """
    def __init__(self, expression: str) -> None:
        self.expression = expression.strip()
        self._comparators: List[List[VersionComparator]] = []  # OR of ANDs
        self._is_any = (self.expression in ("*", "", "all"))
        if not self._is_any:
            self._parse_expression(self.expression)

    def _parse_expression(self, expr: str) -> None:
        # Split by OR ('||')
        or_clauses = expr.split("||")
        for or_clause in or_clauses:
            clause = or_clause.strip()
            if not clause:
                continue
            and_comparators: List[VersionComparator] = []

            # Check for hyphen range: '1.0.0 - 2.0.0'
            hyphen_match = re.match(r"^(\S+)\s+-\s+(\S+)$", clause)
            if hyphen_match:
                v1 = SemVer.parse(hyphen_match.group(1))
                v2 = SemVer.parse(hyphen_match.group(2))
                and_comparators.append(VersionComparator(">=", v1))
                and_comparators.append(VersionComparator("<=", v2))
                self._comparators.append(and_comparators)
                continue

            # Split comma or whitespace separated terms (e.g. '>=1.0.0, <2.0.0' or '>=1.0.0 <2.0.0')
            terms = [t.strip() for t in re.split(r"[, ]+", clause) if t.strip()]
            for term in terms:
                if term == "*":
                    continue
                # Caret range: ^1.2.3 -> >=1.2.3, <2.0.0 (if major > 0)
                if term.startswith("^"):
                    base_v = SemVer.parse(term[1:])
                    and_comparators.append(VersionComparator(">=", base_v))
                    if base_v.major > 0:
                        and_comparators.append(VersionComparator("<", SemVer(base_v.major + 1, 0, 0)))
                    elif base_v.minor > 0:
                        and_comparators.append(VersionComparator("<", SemVer(0, base_v.minor + 1, 0)))
                    else:
                        and_comparators.append(VersionComparator("<", SemVer(0, 0, base_v.patch + 1)))
                # Tilde range: ~1.2.3 -> >=1.2.3, <1.3.0
                elif term.startswith("~"):
                    base_v = SemVer.parse(term[1:])
                    and_comparators.append(VersionComparator(">=", base_v))
                    and_comparators.append(VersionComparator("<", SemVer(base_v.major, base_v.minor + 1, 0)))
                else:
                    m = re.match(r"^(>=|<=|>|<|==|=|!=)?\s*(.+)$", term)
                    if m:
                        op = m.group(1) or "="
                        ver_str = m.group(2)
                        base_v = SemVer.parse(ver_str)
                        and_comparators.append(VersionComparator(op, base_v))
                    else:
                        base_v = SemVer.parse(term)
                        and_comparators.append(VersionComparator("=", base_v))

            if and_comparators:
                self._comparators.append(and_comparators)

    def matches(self, version: str | SemVer) -> bool:
        """Evaluates whether a version satisfies this range expression."""
        if self._is_any:
            return True
        ver = version if isinstance(version, SemVer) else SemVer.parse(version)
        if not self._comparators:
            return True

        # At least one OR branch must satisfy all its AND comparators
        for and_branch in self._comparators:
            if all(cmp.matches(ver) for cmp in and_branch):
                return True
        return False
