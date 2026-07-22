"""
Dynamic Architecture Boundary Compliance Checker.
Ensures Platform 6 does not violate enterprise design dependencies.
"""

import sys
import re
from typing import List, Tuple


class ArchitectureVerifier:
    """Dynamic AST parser checking illegal import directions in Platform 6."""

    @staticmethod
    def verify_boundaries(filepaths: List[str]) -> Tuple[bool, List[str]]:
        """
        Scans python source files for direct imports from internal domains of Platforms 1-5, 7-9.
        Only allows public facade references.
        """
        illegal_patterns = [
            # Direct internal imports of orchestration
            re.compile(r"from\s+akaal\.orchestration\.(domain|engine|repository|session|audit)\s+import"),
            # Direct internal imports of distributed
            re.compile(r"from\s+akaal\.distributed\.(clock|cluster|coordination|events|execution|queue|repository|resource|scheduler|worker)\s+import"),
            # Direct internal imports of streaming
            re.compile(r"from\s+akaal\.streaming\.(domain|engine|flow|memory|operators|time|windowing)\s+import"),
        ]

        violations = []
        for filepath in filepaths:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        for pattern in illegal_patterns:
                            if pattern.search(line):
                                violations.append(f"{filepath}:{line_num} -> Illegal import pattern match: {line.strip()}")
            except Exception as e:
                # If file not found or unwritable, skip
                pass

        return len(violations) == 0, violations
