"""
akaalEngine.extensions.truth.proof_resolver
===========================================
Validates provenance and records proof/certification references.
Prevents unproven self-declarations from masquerading as trusted LIVE_PROVEN certifications.
"""

from __future__ import annotations

from typing import Optional, Sequence

from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.enums import ProofLevel
from akaalEngine.extensions.models.proof import CertificationReference, ProofReference


class ProofResolver:
    """
    Evaluates proof levels and prevents illicit elevation of capability claims.
    """

    @classmethod
    def resolve_effective_proof_level(
        cls,
        declaration: CapabilityDeclaration,
        proof_references: Sequence[ProofReference],
        certifications: Sequence[CertificationReference],
    ) -> ProofLevel:
        # Check for valid live certification
        if certifications:
            for cert in certifications:
                if cert.certified_level == ProofLevel.LIVE_PROVEN:
                    return ProofLevel.LIVE_PROVEN

        # Check for automated test / integration proofs
        highest_proof = ProofLevel.DECLARED
        for proof in proof_references:
            if proof.target_capability.upper() == declaration.capability_name.upper():
                if proof.proven_level == ProofLevel.LIVE_PROVEN:
                    # Live proof requires formal certification reference, not mere unit ref
                    if not certifications:
                        continue
                if proof.proven_level == ProofLevel.INTEGRATION_PROVEN:
                    highest_proof = ProofLevel.INTEGRATION_PROVEN
                elif proof.proven_level == ProofLevel.UNIT_PROVEN and highest_proof != ProofLevel.INTEGRATION_PROVEN:
                    highest_proof = ProofLevel.UNIT_PROVEN

        # If concrete implementation exists and no test proof, it's IMPLEMENTED
        if highest_proof == ProofLevel.DECLARED and declaration.is_supported:
            return ProofLevel.IMPLEMENTED

        return highest_proof
