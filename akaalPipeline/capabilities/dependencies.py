"""akaalPipeline.capabilities.dependencies
==========================================
Dependency evaluator for capability prerequisites.
"""

from __future__ import annotations

from typing import List, Set
from akaalPipeline.capabilities.catalog import CapabilityCatalog, CapabilityDescriptor


class DependencyEvaluator:
    def __init__(self, catalog: CapabilityCatalog) -> None:
        self.catalog = catalog

    def evaluate_dependencies(self, capability_ids: List[str]) -> tuple[bool, Set[str]]:
        """Returns (is_satisfied, missing_dependencies_set)."""
        provided = set(capability_ids)
        missing: Set[str] = set()

        for cap_id in capability_ids:
            desc = self.catalog.get(cap_id)
            if desc:
                for dep in desc.dependencies:
                    if dep not in provided:
                        missing.add(dep)

        return (len(missing) == 0, missing)
