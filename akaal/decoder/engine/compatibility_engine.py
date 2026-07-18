"""
Akaal — Compatibility Engine
============================
Single-responsibility engine evaluating Semantic Mapping & Equivalence metadata across storage model transitions.
"""

from typing import Dict, Any, List
from akaal.decoder.models.canonical_equivalence import SemanticEquivalence, SemanticEquivalenceType
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph


class CompatibilityEngine:
    """Evaluates SemanticEquivalence metadata for normalized objects."""

    def evaluate_compatibility(self, graph: CanonicalObjectGraph) -> Dict[str, Any]:
        mappings: Dict[str, Any] = {}
        lossless_count = 0
        total_count = len(graph.get_all_objects())

        for obj in graph.get_all_objects():
            # Check for opaque types or custom handlers
            is_opaque = False
            if hasattr(obj, "data_type") and obj.data_type and obj.data_type.family == "OPAQUE":
                is_opaque = True

            if is_opaque:
                obj.semantic_equivalence = SemanticEquivalence(
                    equivalence_type=SemanticEquivalenceType.PARTIAL,
                    confidence_score=75.0,
                    is_lossless=False,
                    reason="Opaque data type encountered",
                    fallback_strategy="EMULATED_STRING",
                )
            else:
                obj.semantic_equivalence = SemanticEquivalence(
                    equivalence_type=SemanticEquivalenceType.EQUIVALENT,
                    confidence_score=100.0,
                    is_lossless=True,
                    reason="Direct canonical mapping",
                )
                lossless_count += 1

            mappings[obj.identity.canonical_id] = obj.semantic_equivalence.to_dict()

        return {
            "total_objects_evaluated": total_count,
            "lossless_count": lossless_count,
            "lossless_percentage": round((lossless_count / total_count * 100.0) if total_count > 0 else 100.0, 2),
            "mappings": mappings,
        }
