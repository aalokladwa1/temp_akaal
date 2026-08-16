"""
Akaal — Dynamic Compatibility Matrix Generator (P4.8)
=====================================================
Generates the complete directed N x N enterprise compatibility matrix dynamically
from registered ConnectorCapabilityContracts and universal compatibility rules.
Matrix is a generated output, NEVER a hardcoded dictionary.
"""

from typing import Dict, Any, List
from akaal.connectors.compatibility_engine import UniversalCompatibilityEngine


class DynamicCompatibilityMatrixGenerator:
    """Generates directed N x N cross-system compatibility matrix dynamically."""

    def __init__(self, engine: UniversalCompatibilityEngine) -> None:
        self.engine = engine

    def generate_matrix(self) -> Dict[str, Any]:
        """
        Dynamically iterates over all registered system contracts and computes
        every directed (source -> target) migration compatibility evaluation.
        """
        registered_systems = sorted(list(self.engine._registered_contracts.keys()))
        matrix: Dict[str, Dict[str, Any]] = {}
        total_combinations = len(registered_systems) * len(registered_systems)
        supported_count = 0

        for src in registered_systems:
            matrix[src] = {}
            for tgt in registered_systems:
                eval_res = self.engine.evaluate_cross_system_compatibility(src, tgt)
                matrix[src][tgt] = eval_res
                if eval_res.get("is_viable"):
                    supported_count += 1

        return {
            "registered_systems": registered_systems,
            "system_count": len(registered_systems),
            "total_directed_combinations": total_combinations,
            "viable_combinations": supported_count,
            "matrix": matrix,
        }
