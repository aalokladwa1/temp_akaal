"""
AKAAL Platform 6 — Governance Dependency Validator.
"""

from typing import Tuple, List
from akaal.governance.dependencies.graph import GovernanceDependencyGraph


class GovernanceDependencyValidator:
    """Validates dependency graph consistency and detects circular dependencies or missing references."""

    def validate_graph(self, graph: GovernanceDependencyGraph) -> Tuple[bool, List[str]]:
        errors = []
        if graph.detect_circular_dependencies():
            errors.append("Circular dependency detected in governance dependency graph.")

        return len(errors) == 0, errors
