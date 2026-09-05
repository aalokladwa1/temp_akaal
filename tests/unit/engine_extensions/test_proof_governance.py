"""
tests.unit.engine_extensions.test_proof_governance
==================================================
Tests for proof governance, provenance verification, and rejection of self-awarded live certification.
"""

from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.enums import ProofLevel
from akaalEngine.extensions.models.proof import CertificationReference, ProofReference
from akaalEngine.extensions.truth.authority_store import CertificationAuthorityStore, CertificationRecord
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
    """
    Corrected under the P7A.2/P7A.5 hostile-review fix (CertificationAuthorityStore):
    previously this test's second half asserted that ANY CertificationReference object --
    including one a strategy_factory could construct itself with no AKAAL-issued backing
    record -- was treated as "genuine" and elevated to LIVE_PROVEN. That was the exact
    self-awarded-certification vulnerability this test's own name describes, just not yet
    closed when it was written. The assertion is corrected to what the test's name always
    claimed: a certification claim with no matching CertificationAuthorityStore record is
    rejected (stays IMPLEMENTED), and only a certification_id that resolves to a genuine,
    identity-matched, non-expired, non-revoked record in the store elevates to LIVE_PROVEN.
    """
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

    # A self-attached CertificationReference with NO backing authority-store record is a
    # bare claim, not proof -- must NOT elevate, regardless of what it asserts about itself.
    self_awarded_cert = CertificationReference(
        certification_id="cert-oracle-live-1",
        certifier_authority="AKAAL-QA-LAB",
        certified_level=ProofLevel.LIVE_PROVEN,
        certified_target="Oracle 19c Enterprise",
        valid_from="2026-08-22",
    )
    p_self_awarded = ProofResolver.resolve_effective_proof_level(
        decl,
        proof_references=(),
        certifications=(self_awarded_cert,),
        authority_store=CertificationAuthorityStore(),  # empty -- nothing registered
        extension_id="ext.oracle-connector",
        extension_version="1.0.0",
        provider_id="oracle",
    )
    assert p_self_awarded == ProofLevel.IMPLEMENTED  # NOT LIVE_PROVEN -- this is the fix

    # Only a genuinely registered, identity-matched CertificationRecord elevates to LIVE_PROVEN.
    store = CertificationAuthorityStore()
    store.register_certification(
        CertificationRecord(
            certification_id="cert-oracle-live-1",
            extension_id="ext.oracle-connector",
            extension_version="1.0.0",
            provider_id="oracle",
            capability_name="CDC_CAPTURE",
            certifier_authority="AKAAL-QA-LAB",
            certified_level=ProofLevel.LIVE_PROVEN,
            issued_at="2026-08-22T00:00:00+00:00",
        )
    )
    p_authoritative = ProofResolver.resolve_effective_proof_level(
        decl,
        proof_references=(),
        certifications=(self_awarded_cert,),
        authority_store=store,
        extension_id="ext.oracle-connector",
        extension_version="1.0.0",
        provider_id="oracle",
    )
    assert p_authoritative == ProofLevel.LIVE_PROVEN
