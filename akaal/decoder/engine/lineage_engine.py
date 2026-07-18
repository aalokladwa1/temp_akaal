"""
Akaal — Lineage Engine
======================
Single-responsibility engine tracking transformation lineage across Decoder normalization stages.
"""

from typing import Dict, Any
from akaal.decoder.models.canonical_lineage import CanonicalLineage
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph


class LineageEngine:
    """Records Stage 1 transformation lineage for canonical objects."""

    def record_lineage(self, graph: CanonicalObjectGraph, correlation_id: str) -> CanonicalLineage:
        lineage = CanonicalLineage(lineage_id=correlation_id)

        for obj in graph.get_all_objects():
            lineage.record_stage(
                stage_name="DecoderNormalization",
                source_id=obj.identity.source_identifier or obj.name,
                target_id=obj.identity.canonical_id,
                tx_description=f"Normalized object '{obj.name}' to CanonicalObject node.",
            )

        return lineage
