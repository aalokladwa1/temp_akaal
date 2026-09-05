"""
akaalEngine.extensions.truth.proof_resolver
===========================================
Validates provenance and records proof/certification references.
Prevents unproven self-declarations from masquerading as trusted LIVE_PROVEN certifications.
"""

from __future__ import annotations

from typing import Optional, Sequence

from akaalEngine.extensions.truth.authority_store import CertificationAuthorityStore
from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.enums import ProofLevel
from akaalEngine.extensions.models.proof import CertificationReference, ProofReference


class ProofResolver:
    """
    Evaluates proof levels and prevents illicit elevation of capability claims.

    Security-critical: a CertificationReference attached to a StrategyContribution is a
    CLAIM, not proof by itself -- it is only honored if it resolves, by certification_id,
    to an authoritative CertificationRecord in the supplied CertificationAuthorityStore,
    with EVERY identity dimension (extension_id, extension_version, provider_id,
    capability_name) matching exactly, and the record neither expired nor revoked. Without
    an authority_store, no CertificationReference can elevate a proof level at all --
    self-declared claims never do so on their own, closing the self-elevation path where
    a strategy_factory could otherwise construct its own "LIVE_PROVEN" claim.
    """

    @classmethod
    def resolve_effective_proof_level(
        cls,
        declaration: CapabilityDeclaration,
        proof_references: Sequence[ProofReference],
        certifications: Sequence[CertificationReference],
        authority_store: Optional[CertificationAuthorityStore] = None,
        extension_id: Optional[str] = None,
        extension_version: Optional[str] = None,
        provider_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> ProofLevel:
        # Check for an AUTHORITATIVE live certification -- never trust the claim directly.
        authoritative_live_certified = False
        if authority_store is not None and certifications and extension_id and extension_version and provider_id:
            for cert in certifications:
                resolved_level = authority_store.resolve_authoritative_level(
                    certification_id=cert.certification_id,
                    extension_id=extension_id,
                    extension_version=extension_version,
                    provider_id=provider_id,
                    capability_name=declaration.capability_name,
                    strategy_id=strategy_id,
                )
                if resolved_level == ProofLevel.LIVE_PROVEN:
                    authoritative_live_certified = True
                    break

        if authoritative_live_certified:
            return ProofLevel.LIVE_PROVEN

        # Check for automated test / integration proofs
        highest_proof = ProofLevel.DECLARED
        for proof in proof_references:
            if proof.target_capability.upper() == declaration.capability_name.upper():
                if proof.proven_level == ProofLevel.LIVE_PROVEN:
                    # Live proof requires an AUTHORITATIVE certification, not mere unit ref
                    # and never a bare (unverified) certifications claim.
                    if not authoritative_live_certified:
                        continue
                if proof.proven_level == ProofLevel.INTEGRATION_PROVEN:
                    highest_proof = ProofLevel.INTEGRATION_PROVEN
                elif proof.proven_level == ProofLevel.UNIT_PROVEN and highest_proof != ProofLevel.INTEGRATION_PROVEN:
                    highest_proof = ProofLevel.UNIT_PROVEN

        # If concrete implementation exists and no test proof, it's IMPLEMENTED
        if highest_proof == ProofLevel.DECLARED and declaration.is_supported:
            return ProofLevel.IMPLEMENTED

        return highest_proof
