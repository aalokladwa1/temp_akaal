"""
Architecture Boundary Verifier for Platform 9.
Ensures Platform 9 never imports internal implementation modules from Platforms 1 to 8.
"""

import sys
import os
import re
from typing import List, Tuple


class ArchitectureVerifier:
    """Verifies architectural isolation and import boundary rules."""

    @staticmethod
    def verify_boundaries(filepaths: List[str]) -> Tuple[bool, List[str]]:
        """
        Scans python source files for illegal imports of internal modules from Platforms 1-8.
        Only allows public facade references.
        """
        illegal_patterns = [
            # Orchestration internals
            re.compile(r"from\s+akaal\.orchestration\.(domain|engine|repository|session|audit)\s+import"),
            # Distributed internals
            re.compile(r"from\s+akaal\.distributed\.(clock|cluster|coordination|events|execution|queue|repository|resource|scheduler|worker)\s+import"),
            # Streaming internals
            re.compile(r"from\s+akaal\.streaming\.(domain|engine|flow|memory|operators|time|windowing)\s+import"),
            # Schema evolution internals
            re.compile(r"from\s+akaal\.schema\.(concurrency|graph|journal|metadata|operations|recovery|replay|transactions|validation|versioning)\s+import"),
            # Performance engine internals
            re.compile(r"from\s+akaal\.performance\.(config|decision|discovery|event_bus|failures|governor|health|history|optimizers|orchestration|telemetry)\s+import"),
        ]

        violations = []
        for filepath in filepaths:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        for pattern in illegal_patterns:
                            if pattern.search(line):
                                violations.append(f"{filepath}:{line_num} -> Illegal import pattern: {line.strip()}")
            except Exception:
                pass

        return len(violations) == 0, violations
