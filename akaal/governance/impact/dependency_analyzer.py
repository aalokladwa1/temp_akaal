"""
AKAAL Platform 6 — Governance Dependency Impact Analyzer.
"""

from typing import Dict, List, Set


class DependencyImpactAnalyzer:
    """Calculates cascade blast radius when a governance artifact is modified or retired."""

    def calculate_blast_radius(self, target_id: str, dependency_map: Dict[str, List[str]]) -> Set[str]:
        affected = set()
        stack = [target_id]

        while stack:
            curr = stack.pop()
            for artifact_id, deps in dependency_map.items():
                if curr in deps and artifact_id not in affected:
                    affected.add(artifact_id)
                    stack.append(artifact_id)

        return affected
