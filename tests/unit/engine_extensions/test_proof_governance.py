"""
tests.unit.engine_extensions.test_proof_governance
==================================================
Tests for proof governance, provenance verification, and rejection of self-awarded live certification.
"""

from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.enums import ProofLevel
from akaalEngine.extensions.models.proof import CertificationReference, ProofReference
from akaalEngine.extensions.truth.proof_resolver import ProofResolver


def test_proof_level_derivation_from_unit_and_integration_proofs():
    decl = CapabilityDeclaration(capability_name="BULK_READ", is_supported=True)

    # 1. Self declaration without test proof -> IMPLEMENTED
    p1 = ProofResolver.resolve_effective_proof_level(decl, proof_references=(), certifications=())
    assert p1 == ProofLevel.IMPLEMENTED

    # 2. Automated unit test proof -> UNIT_PROVEN
    unit_proof = ProofReference(
        proof_id="proof-1",
        target_capability="BULK_READ",
        proven_level=ProofLevel.UNIT_PROVEN,
        test_suite_ref="tests/unit/test_bulk.py",
        verified_at="2026-08-22",
        verifier_identity="pytest-ci",
    )
    p2 = ProofResolver.resolve_effective_proof_level(decl, proof_references=(unit_proof,), certifications=())
    assert p2 == ProofLevel.UNIT_PROVEN

    # 3. Integration test proof -> INTEGRATION_PROVEN
    integ_proof = ProofReference(
        proof_id="proof-2",
        target_capability="BULK_READ",
        proven_level=ProofLevel.INTEGRATION_PROVEN,
        test_suite_ref="tests/integration/test_emulator.py",
        verified_at="2026-08-22",
        verifier_identity="emulator-ci",
    )
    p3 = ProofResolver.resolve_effective_proof_level(decl, proof_references=(unit_proof, integ_proof), certifications=())
    assert p3 == ProofLevel.INTEGRATION_PROVEN


def test_self_awarded_live_certification_rejected():
    decl = CapabilityDeclaration(capability_name="CDC_CAPTURE", is_supported=True)

    # Unit proof trying to claim LIVE_PROVEN without formal certification reference is rejected
    fraudulent_unit_proof = ProofReference(
        proof_id="fake-live",
        target_capability="CDC_CAPTURE",
        proven_level=ProofLevel.LIVE_PROVEN,
        test_suite_ref="tests/mock.py",
        verified_at="2026-08-22",
        verifier_identity="self",
    )
    p_fake = ProofResolver.resolve_effective_proof_level(
        decl,
        proof_references=(fraudulent_unit_proof,),
        certifications=(),
    )
    assert p_fake == ProofLevel.IMPLEMENTED  # Cannot elevate to LIVE_PROVEN

    # Genuine CertificationReference elevates to LIVE_PROVEN
    cert = CertificationReference(
        certification_id="cert-oracle-live-1",
        certifier_authority="AKAAL-QA-LAB",
        certified_level=ProofLevel.LIVE_PROVEN,
        certified_target="Oracle 19c Enterprise",
        valid_from="2026-08-22",
    )
    p_real = ProofResolver.resolve_effective_proof_level(
        decl,
        proof_references=(),
        certifications=(cert,),
    )
    assert p_real == ProofLevel.LIVE_PROVEN
