"""
Akaal — Validation Engine
========================
Single-responsibility engine checking ValidationProfile constraints before model assembly.
"""

from typing import List, Tuple
from akaal.decoder.models.decoder_context import DecoderContext, ValidationProfile
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph
from akaal.decoder.models.canonical_diagnostic import CanonicalDiagnostic, DiagnosticSeverity


class ValidationEngine:
    """Validates object graph integrity according to ValidationProfile."""

    def validate_graph(self, graph: CanonicalObjectGraph, ctx: DecoderContext) -> Tuple[bool, List[CanonicalDiagnostic]]:
        diagnostics: List[CanonicalDiagnostic] = []
        is_valid = True

        profile = ctx.validation_profile

        for obj in graph.get_all_objects():
            if not obj.name:
                is_valid = False
                diagnostics.append(CanonicalDiagnostic(
                    diagnostic_id=f"DIAG-VAL-NAME-{obj.identity.canonical_id}",
                    severity=DiagnosticSeverity.ERROR,
                    category="MISSING_NAME",
                    affected_objects=[obj.identity.canonical_id],
                    root_cause="Canonical object is missing a name attribute.",
                    recommended_resolution="Ensure all objects carry valid names.",
                ))

            if profile == ValidationProfile.STRICT and getattr(obj, "data_type", None) and obj.data_type.family == "OPAQUE":
                diagnostics.append(CanonicalDiagnostic(
                    diagnostic_id=f"DIAG-VAL-STRICT-{obj.identity.canonical_id}",
                    severity=DiagnosticSeverity.WARNING,
                    category="OPAQUE_TYPE_STRICT",
                    affected_objects=[obj.identity.canonical_id],
                    root_cause=f"Strict profile flag: Object '{obj.name}' has OpaqueType.",
                    recommended_resolution="Provide explicit type mapping for opaque types.",
                ))

        return is_valid, diagnostics
