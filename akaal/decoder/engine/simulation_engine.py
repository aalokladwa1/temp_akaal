"""
Akaal — Simulation Engine
=========================
Single-responsibility engine producing read-only simulation dry-run summaries for Decoder.
"""

from typing import Dict, Any, List
from akaal.decoder.models.decoder_context import DecoderContext
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph
from akaal.decoder.models.canonical_diagnostic import CanonicalDiagnostic


class SimulationEngine:
    """Executes dry-run normalization simulation."""

    def simulate(
        self,
        ctx: DecoderContext,
        graph: CanonicalObjectGraph,
        diagnostics: List[CanonicalDiagnostic],
    ) -> Dict[str, Any]:
        objs = graph.get_all_objects()
        return {
            "simulation_mode": True,
            "validation_profile": ctx.validation_profile.value,
            "total_objects_normalized": len(objs),
            "diagnostics_count": len(diagnostics),
            "diagnostics": [d.to_dict() for d in diagnostics],
        }
