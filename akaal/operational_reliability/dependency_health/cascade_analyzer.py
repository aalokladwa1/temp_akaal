"""
AKAAL Platform 7 — Cascade Failure Analyzer.
"""

from typing import List, Set
from akaal.operational_reliability.dependency_health.monitor import DependencyHealthMonitor


class CascadeFailureAnalyzer:
    """Analyzes upstream/downstream blast radius when a dependent service experiences failure."""

    def analyze_cascade_impact(self, monitor: DependencyHealthMonitor, failed_service_id: str) -> Set[str]:
        impacted = set()
        stack = [failed_service_id]

        while stack:
            curr = stack.pop()
            deps = monitor.list_dependencies_for_service(curr)
            for d in deps:
                if d.source_service_id == curr and d.target_service_id not in impacted:
                    impacted.add(d.target_service_id)
                    stack.append(d.target_service_id)

        return impacted
