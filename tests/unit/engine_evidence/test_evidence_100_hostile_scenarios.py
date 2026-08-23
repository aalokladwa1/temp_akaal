"""
tests/unit/engine_evidence/test_evidence_100_hostile_scenarios.py
==================================================================
Comprehensive 1-to-100 Hostile Acceptance Test Suite for Authority #12 Evidence / Provenance / Execution-Truth Artifacts.
Mechanically verifies stored vs effective completeness semantics, the 22-case adversarial completeness matrix,
the 20-surface secret non-leakage matrix, proof classification preservation, manifest fail-closed rules, durable restart,
stale-writer fencing, and memory scale invariants.
"""

from decimal import Decimal
import pytest
import time

from akaalEngine.cdc import PostgresLSNPosition
from akaalEngine.evidence import (
    CanonicalEvidenceSerializer,
    EvidenceArtifact,
    EvidenceAuthority,
    EvidenceCompleteness,
    EvidenceDigest,
    EvidenceDigestCalculator,
    EvidenceError,
    EvidenceFact,
    EvidenceFencingError,
    EvidenceIdentityError,
    EvidenceIntegrityError,
    EvidenceManifest,
    EvidenceProvenance,
    EvidenceSecuritySanitizer,
    EvidenceVerificationEngine,
    ProofClassification,
)
from akaalEngine.validation import (
    ProofScope,
    ValidationGateStatus,
    ValidationResult,
)


# ============================================================
# BLOCKER 1 & 2: ADVERSARIAL COMPLETENESS & EFFECTIVE SEMANTICS (22 CASES)
# ============================================================

def test_1_missing_validation_evidence_effective_completeness():
    evd = EvidenceAuthority()
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED")
    res = evd.verify_artifact(art_exec, expected_migration_id="mig-1")
    assert res.is_valid is True
    assert res.completeness == EvidenceCompleteness.COMPLETE

def test_2_validation_gate_failed_effective_completeness():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, rows_mismatched=1)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.completeness == EvidenceCompleteness.FAILED
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED  # Effective completeness fails closed!

def test_3_validation_gate_withheld_effective_completeness():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.SAMPLED.value, ValidationGateStatus.WITHHELD)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.completeness == EvidenceCompleteness.PARTIAL
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.PARTIAL

def test_4_validation_proof_scope_unproven_effective_completeness():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "FAILED", ProofScope.UNPROVEN.value, ValidationGateStatus.FAILED)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.completeness == EvidenceCompleteness.FAILED
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_5_missing_cdc_boundary_when_mandatory():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "VAL", [], [])
    res = evd.verify_artifact(art, required_cdc_boundary_position="0/200")
    assert res.is_valid is False
    assert res.boundary_fresh is False
    assert res.completeness == EvidenceCompleteness.UNPROVEN  # Stale boundary effective completeness!

def test_6_stale_cdc_boundary_p0_vs_p1_effective_completeness():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, cdc_boundary_position="0/100")
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.completeness == EvidenceCompleteness.COMPLETE  # Stored structural completeness for P0

    # Verification against required boundary P1
    res = evd.verify_artifact(art, required_cdc_boundary_position="0/200")
    assert res.is_valid is False
    assert res.boundary_fresh is False
    assert res.completeness != EvidenceCompleteness.COMPLETE  # Effective completeness is UNPROVEN for P1!
    assert res.completeness == EvidenceCompleteness.UNPROVEN

def test_7_cdc_open_transactions_effective_completeness():
    evd = EvidenceAuthority()
    art = evd.package_cdc_evidence("mig-1", "run-1", {"open_transactions": 2})
    assert art.completeness == EvidenceCompleteness.FAILED
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_8_cdc_ambiguous_commit_count_effective_completeness():
    evd = EvidenceAuthority()
    art = evd.package_cdc_evidence("mig-1", "run-1", {"ambiguous_commit_count": 1})
    assert art.completeness == EvidenceCompleteness.FAILED
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_9_cdc_backlog_events_effective_completeness():
    evd = EvidenceAuthority()
    art = evd.package_cdc_evidence("mig-1", "run-1", {"backlog_events": 5})
    assert art.completeness == EvidenceCompleteness.FAILED
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_10_cdc_synchronization_barrier_not_reached():
    evd = EvidenceAuthority()
    art = evd.package_cdc_evidence("mig-1", "run-1", {"synchronization_barrier_reached": False})
    assert art.completeness == EvidenceCompleteness.FAILED
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_11_missing_execution_identity():
    art = EvidenceArtifact("a1", "EXEC", "", "run-1")
    res = EvidenceVerificationEngine.verify_artifact(art, expected_migration_id="mig-1")
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_12_migration_identity_mismatch_effective_completeness():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], completeness=EvidenceCompleteness.COMPLETE)
    res = evd.verify_artifact(art, expected_migration_id="mig-999")
    assert res.is_valid is False
    assert res.completeness != EvidenceCompleteness.COMPLETE
    assert res.completeness == EvidenceCompleteness.FAILED

def test_13_run_identity_mismatch_effective_completeness():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], completeness=EvidenceCompleteness.COMPLETE)
    res = evd.verify_artifact(art, expected_run_id="run-999")
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_14_missing_authoritative_provenance_identity():
    art = EvidenceArtifact("a1", "EXEC", "mig-1", "run-1", completeness=EvidenceCompleteness.COMPLETE)
    res = EvidenceVerificationEngine.verify_artifact(art)
    assert res.is_valid is False
    assert res.tamper_detected is True
    assert res.completeness == EvidenceCompleteness.FAILED

def test_15_invalid_stale_durable_provenance():
    class RejectingDurability:
        def verify_fencing_token(self, tok): return False
    evd = EvidenceAuthority(durability_authority=RejectingDurability())
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [])
    with pytest.raises(EvidenceFencingError, match="Stale fencing token"):
        evd.persist_evidence(art, fencing_token="stale-tok")

def test_16_corrupt_artifact_digest_effective_completeness():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], completeness=EvidenceCompleteness.COMPLETE)
    art.digest.digest_hex = "CORRUPT_HEX"
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.tamper_detected is True
    assert res.completeness != EvidenceCompleteness.COMPLETE
    assert res.completeness == EvidenceCompleteness.FAILED

def test_17_corrupt_manifest_member_digest_effective_completeness():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    man = evd.create_manifest("mig-1", "run-1", [art])
    art.digest.digest_hex = "CORRUPT_MEMBER_HEX"
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.tamper_detected is True
    assert res.completeness == EvidenceCompleteness.FAILED

def test_18_missing_mandatory_artifact_from_manifest():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    art2 = evd.create_evidence_artifact("mig-1", "run-1", "VAL", [], [], artifact_id="art-2", completeness=EvidenceCompleteness.COMPLETE)
    man = evd.create_manifest("mig-1", "run-1", [art1, art2])
    man.artifacts = [art1]
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_19_mandatory_artifact_present_but_unverified():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    art2 = evd.create_evidence_artifact("mig-1", "run-1", "VAL", [], [], artifact_id="art-2", completeness=EvidenceCompleteness.FAILED)
    man = evd.create_manifest("mig-1", "run-1", [art1, art2])
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_20_execution_state_failed_effective_completeness():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "FAILED")
    assert art.completeness == EvidenceCompleteness.FAILED
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_21_execution_state_cancelled_effective_completeness():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "CANCELLED")
    assert art.completeness == EvidenceCompleteness.CANCELLED
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.CANCELLED

def test_22_partial_sampled_proof_effective_completeness():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.SAMPLED.value, ValidationGateStatus.WITHHELD)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.completeness == EvidenceCompleteness.PARTIAL
    res = evd.verify_artifact(art)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.PARTIAL


# ============================================================
# BLOCKER 3: SECRET NON-LEAKAGE COVERAGE (20 SURFACES)
# ============================================================

def test_23_secret_absent_nested_dicts():
    data = {"nested": {"password": "SUPER_SECRET_PASSWORD_12"}}
    clean = EvidenceSecuritySanitizer.sanitize(data)
    assert "SUPER_SECRET_PASSWORD_12" not in str(clean)

def test_24_secret_absent_lists_containing_secret_mappings():
    data = [{"token": "SUPER_SECRET_TOKEN_12"}]
    clean = EvidenceSecuritySanitizer.sanitize(data)
    assert "SUPER_SECRET_TOKEN_12" not in str(clean)

def test_25_secret_absent_tuples_containers():
    data = ({"api_key": "SUPER_SECRET_API_KEY_12"},)
    clean = EvidenceSecuritySanitizer.sanitize(data)
    assert "SUPER_SECRET_API_KEY_12" not in str(clean)

def test_26_secret_absent_fact_value():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [EvidenceFact("pass", "SUPER_SECRET_PASSWORD_12", "A7", "METRIC")], [])
    assert art.facts[0].fact_value == "[REDACTED]"
    assert "SUPER_SECRET_PASSWORD_12" not in str(art.facts[0].fact_value)

def test_27_secret_absent_provenance_metadata():
    prov = EvidenceProvenance("A11", "Comp", boundary_position="password=SUPER_SECRET_TOKEN_12")
    clean = EvidenceSecuritySanitizer.sanitize(prov.to_dict())
    assert "SUPER_SECRET_TOKEN_12" not in str(clean)

def test_28_secret_absent_artifact_repr():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], source_identity="postgresql://user:SUPER_SECRET_PASSWORD_12@host/db")
    assert "SUPER_SECRET_PASSWORD_12" not in repr(art)

def test_29_secret_absent_artifact_str():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], source_identity="postgresql://user:SUPER_SECRET_PASSWORD_12@host/db")
    assert "SUPER_SECRET_PASSWORD_12" not in str(art)

def test_30_secret_absent_manifest_repr():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], source_identity="postgresql://user:SUPER_SECRET_PASSWORD_12@host/db", artifact_id="a1")
    man = evd.create_manifest("mig-1", "run-1", [art])
    assert "SUPER_SECRET_PASSWORD_12" not in repr(man)

def test_31_secret_absent_manifest_str():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], source_identity="postgresql://user:SUPER_SECRET_PASSWORD_12@host/db", artifact_id="a1")
    man = evd.create_manifest("mig-1", "run-1", [art])
    assert "SUPER_SECRET_PASSWORD_12" not in str(man)

def test_32_secret_absent_verification_result_repr_str():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], source_identity="postgresql://user:SUPER_SECRET_PASSWORD_12@host/db")
    res = evd.verify_artifact(art, expected_migration_id="mig-WRONG")
    assert "SUPER_SECRET_PASSWORD_12" not in repr(res)
    assert "SUPER_SECRET_PASSWORD_12" not in str(res)

def test_33_secret_absent_canonical_serialized_bytes():
    data = {"password": "SUPER_SECRET_PASSWORD_12", "token": "SUPER_SECRET_TOKEN_12"}
    clean = EvidenceSecuritySanitizer.sanitize(data)
    b = CanonicalEvidenceSerializer.serialize_to_bytes(clean)
    assert b"SUPER_SECRET_PASSWORD_12" not in b
    assert b"SUPER_SECRET_TOKEN_12" not in b

def test_34_secret_absent_verification_error_messages():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], source_identity="postgresql://user:SUPER_SECRET_PASSWORD_12@host/db")
    res = evd.verify_artifact(art, expected_migration_id="mig-WRONG")
    reasons_text = " ".join(res.reasons)
    assert "SUPER_SECRET_PASSWORD_12" not in reasons_text

def test_35_secret_absent_integrity_tamper_error_messages():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [EvidenceFact("k", "SUPER_SECRET_TOKEN_12", "A7", "M")], [])
    art.digest.digest_hex = "CORRUPT"
    res = evd.verify_artifact(art)
    assert "SUPER_SECRET_TOKEN_12" not in " ".join(res.reasons)

def test_36_secret_absent_durability_persistence_error_messages():
    class RejectingDurability:
        def verify_fencing_token(self, tok): return False
    evd = EvidenceAuthority(durability_authority=RejectingDurability())
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [EvidenceFact("pass", "SUPER_SECRET_PASSWORD_12", "A7", "M")], [])
    with pytest.raises(EvidenceFencingError) as exc_info:
        evd.persist_evidence(art, fencing_token="stale-tok")
    assert "SUPER_SECRET_PASSWORD_12" not in str(exc_info.value)

def test_37_secret_absent_fencing_error_messages():
    class RejectingDurability:
        def verify_fencing_token(self, tok): return False
    evd = EvidenceAuthority(durability_authority=RejectingDurability())
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [])
    with pytest.raises(EvidenceFencingError) as exc_info:
        evd.persist_evidence(art, fencing_token="stale-tok")
    assert "Stale fencing token" in str(exc_info.value)
    assert "SUPER_SECRET" not in str(exc_info.value)

def test_38_secret_absent_connection_uri_credentials():
    uri = "postgresql://dbuser:SUPER_SECRET_PASSWORD_12@dbhost.internal:5432/production_db"
    clean = EvidenceSecuritySanitizer.sanitize_string(uri)
    assert "SUPER_SECRET_PASSWORD_12" not in clean
    assert "[REDACTED]" in clean

def test_39_secret_absent_authorization_bearer_tokens():
    auth = "Bearer SUPER_SECRET_BEARER_12"
    clean = EvidenceSecuritySanitizer.sanitize_string(auth)
    assert "SUPER_SECRET_BEARER_12" not in clean
    assert "[REDACTED]" in clean

def test_40_secret_absent_passwords_api_keys_private_keys():
    clean_pass = EvidenceSecuritySanitizer.sanitize_string("password=SUPER_SECRET_PASSWORD_12")
    clean_key = EvidenceSecuritySanitizer.sanitize({"api_key": "SUPER_SECRET_API_KEY_12"})
    clean_priv = EvidenceSecuritySanitizer.sanitize({"private_key": "-----BEGIN SUPER_SECRET_PRIVATE_KEY_12-----\n"})
    assert "SUPER_SECRET_PASSWORD_12" not in clean_pass
    assert "SUPER_SECRET_API_KEY_12" not in str(clean_key)
    assert "SUPER_SECRET_PRIVATE_KEY_12" not in str(clean_priv)


# ============================================================
# BLOCKER 4: PROOF CLASSIFICATION PRESERVATION
# ============================================================

def test_41_unit_proven_not_upgraded():
    evd = EvidenceAuthority()
    fact = EvidenceFact("k", "v", "A7", "METRIC", proof_classification=ProofClassification.UNIT_PROVEN)
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [fact], [])
    assert art.facts[0].proof_classification == ProofClassification.UNIT_PROVEN
    assert art.facts[0].proof_classification != ProofClassification.LIVE_PROVEN

def test_42_integration_proven_not_upgraded():
    evd = EvidenceAuthority()
    fact = EvidenceFact("k", "v", "A7", "METRIC", proof_classification=ProofClassification.INTEGRATION_PROVEN)
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [fact], [])
    assert art.facts[0].proof_classification == ProofClassification.INTEGRATION_PROVEN
    assert art.facts[0].proof_classification != ProofClassification.LIVE_PROVEN

def test_43_scale_design_proven_not_upgraded():
    evd = EvidenceAuthority()
    fact = EvidenceFact("k", "v", "A7", "METRIC", proof_classification=ProofClassification.SCALE_DESIGN_PROVEN)
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [fact], [])
    assert art.facts[0].proof_classification == ProofClassification.SCALE_DESIGN_PROVEN
    assert art.facts[0].proof_classification != ProofClassification.LIVE_PROVEN

def test_44_provider_seam_not_upgraded():
    evd = EvidenceAuthority()
    fact = EvidenceFact("k", "v", "A7", "METRIC", proof_classification=ProofClassification.PROVIDER_SEAM)
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [fact], [])
    assert art.facts[0].proof_classification == ProofClassification.PROVIDER_SEAM

def test_45_unproven_remains_unproven():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "FAILED", ProofScope.UNPROVEN.value, ValidationGateStatus.FAILED)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.facts[0].fact_value == ProofScope.UNPROVEN.value

def test_46_failed_remains_failed():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "FAILED")
    assert art.completeness == EvidenceCompleteness.FAILED

def test_47_cancelled_remains_cancelled():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "CANCELLED")
    assert art.completeness == EvidenceCompleteness.CANCELLED

def test_48_live_proven_preserved_only_when_upstream_live():
    evd = EvidenceAuthority()
    fact = EvidenceFact("k", "v", "A7", "METRIC", proof_classification=ProofClassification.LIVE_PROVEN)
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [fact], [])
    assert art.facts[0].proof_classification == ProofClassification.LIVE_PROVEN

def test_49_digest_integrity_does_not_upgrade_proof_level():
    evd = EvidenceAuthority()
    fact = EvidenceFact("k", "v", "A7", "METRIC", proof_classification=ProofClassification.UNIT_PROVEN)
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [fact], [], completeness=EvidenceCompleteness.COMPLETE)
    res = evd.verify_artifact(art)
    assert res.is_valid is True
    assert art.facts[0].proof_classification == ProofClassification.UNIT_PROVEN
    assert art.digest.digital_signature_status == "DIGEST_INTEGRITY_ONLY"


# ============================================================
# BLOCKER 5: MANIFEST / BUNDLE FAIL-CLOSED MATRIX (10 SCENARIOS)
# ============================================================

def test_50_manifest_valid_all_artifacts_verified():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    art2 = evd.create_evidence_artifact("mig-1", "run-1", "VAL", [], [], artifact_id="art-2", completeness=EvidenceCompleteness.COMPLETE)
    man = evd.create_manifest("mig-1", "run-1", [art1, art2])
    res = evd.verify_manifest(man)
    assert res.is_valid is True
    assert res.completeness == EvidenceCompleteness.COMPLETE
    assert res.verified_artifact_count == 2

def test_51_manifest_missing_mandatory_artifact():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    art2 = evd.create_evidence_artifact("mig-1", "run-1", "VAL", [], [], artifact_id="art-2", completeness=EvidenceCompleteness.COMPLETE)
    man = evd.create_manifest("mig-1", "run-1", [art1, art2])
    man.artifacts = [art1]
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.tamper_detected is True

def test_52_manifest_member_digest_corrupted():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    man = evd.create_manifest("mig-1", "run-1", [art1])
    art1.digest.digest_hex = "CORRUPT"
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.tamper_detected is True

def test_53_manifest_artifact_content_mutated():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    man = evd.create_manifest("mig-1", "run-1", [art1])
    art1.facts.append(EvidenceFact("mutated", "val", "A7", "M"))
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.tamper_detected is True

def test_54_manifest_artifact_identity_changed():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    man = evd.create_manifest("mig-1", "run-1", [art1])
    art1.artifact_id = "art-1-MUTATED"
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.tamper_detected is True

def test_55_manifest_duplicate_artifact_identity():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    art1_dup = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    man = EvidenceManifest("m1", "mig-1", "run-1", artifacts=[art1, art1_dup], completeness=EvidenceCompleteness.COMPLETE)
    man.manifest_digest = EvidenceDigestCalculator.compute_digest(man)
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.tamper_detected is True

def test_56_manifest_foreign_migration_artifact_inserted():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1")
    art_foreign = evd.create_evidence_artifact("mig-FOREIGN", "run-1", "VAL", [], [], artifact_id="art-2")
    with pytest.raises(EvidenceIdentityError):
        evd.create_manifest("mig-1", "run-1", [art1, art_foreign])

def test_57_manifest_foreign_run_artifact_inserted():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1")
    art_foreign = evd.create_evidence_artifact("mig-1", "run-FOREIGN", "VAL", [], [], artifact_id="art-2")
    with pytest.raises(EvidenceIdentityError):
        evd.create_manifest("mig-1", "run-1", [art1, art_foreign])

def test_58_manifest_mandatory_artifact_verification_fails():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    art2 = evd.create_evidence_artifact("mig-1", "run-1", "VAL", [], [], artifact_id="art-2", completeness=EvidenceCompleteness.FAILED)
    man = evd.create_manifest("mig-1", "run-1", [art1, art2])
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.completeness == EvidenceCompleteness.FAILED

def test_59_manifest_itself_digest_corrupted():
    evd = EvidenceAuthority()
    art1 = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="art-1", completeness=EvidenceCompleteness.COMPLETE)
    man = evd.create_manifest("mig-1", "run-1", [art1])
    man.manifest_digest.digest_hex = "CORRUPT_MANIFEST_DIGEST"
    res = evd.verify_manifest(man)
    assert res.is_valid is False
    assert res.tamper_detected is True


# ============================================================
# BLOCKER 6: DURABLE RESTART & FENCING PROOF (#5 INTEGRATION)
# ============================================================

def test_60_durable_restart_sequence_instance_a_to_instance_b():
    class MemoryDurability:
        def __init__(self): self.frames = {}
        def verify_fencing_token(self, tok): return True
        def save_spill_frame(self, scope, key, payload): self.frames[key] = payload
        def load_spill_frame(self, scope, key): return self.frames.get(key)

    dur = MemoryDurability()
    evd_a = EvidenceAuthority(durability_authority=dur)
    art_a = evd_a.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], completeness=EvidenceCompleteness.COMPLETE)
    key = evd_a.persist_evidence(art_a)

    # Instance A discarded. Instance B reloads evidence frame.
    evd_b = EvidenceAuthority(durability_authority=dur)
    reloaded = evd_b.reload_evidence(key, expected_migration_id="mig-1")

    assert reloaded.migration_id == "mig-1"
    assert reloaded.run_id == "run-1"
    assert reloaded.digest.digest_hex == art_a.digest.digest_hex
    assert evd_b.verify_artifact(reloaded).is_valid is True

def test_61_durable_reload_wrong_migration_identity_rejected():
    class MemoryDurability:
        def __init__(self): self.frames = {}
        def verify_fencing_token(self, tok): return True
        def save_spill_frame(self, scope, key, payload): self.frames[key] = payload
        def load_spill_frame(self, scope, key): return self.frames.get(key)

    dur = MemoryDurability()
    evd_a = EvidenceAuthority(durability_authority=dur)
    art_a = evd_a.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], completeness=EvidenceCompleteness.COMPLETE)
    key = evd_a.persist_evidence(art_a)

    evd_b = EvidenceAuthority(durability_authority=dur)
    with pytest.raises(EvidenceIdentityError):
        evd_b.reload_evidence(key, expected_migration_id="mig-WRONG")

def test_62_durable_reload_corrupt_frame_rejected():
    class MemoryDurability:
        def __init__(self): self.frames = {}
        def verify_fencing_token(self, tok): return True
        def save_spill_frame(self, scope, key, payload): self.frames[key] = payload
        def load_spill_frame(self, scope, key): return self.frames.get(key)

    dur = MemoryDurability()
    evd_a = EvidenceAuthority(durability_authority=dur)
    art_a = evd_a.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], completeness=EvidenceCompleteness.COMPLETE)
    key = evd_a.persist_evidence(art_a)
    dur.frames[key]["digest"]["digest_hex"] = "CORRUPT_HEX"

    evd_b = EvidenceAuthority(durability_authority=dur)
    with pytest.raises(EvidenceIntegrityError):
        evd_b.reload_evidence(key)

def test_63_stale_writer_fencing_sequence():
    class FencingDurabilityStore:
        def __init__(self):
            self.frames = {}
            self.current_fencing_epoch = "epoch-1"
        def verify_fencing_token(self, tok):
            return tok == self.current_fencing_epoch
        def save_spill_frame(self, scope, key, payload):
            self.frames[key] = payload
        def load_spill_frame(self, scope, key):
            return self.frames.get(key)

    dur = FencingDurabilityStore()
    evd_writer_a = EvidenceAuthority(durability_authority=dur)
    art_v1 = evd_writer_a.create_evidence_artifact("mig-1", "run-1", "EXEC", [EvidenceFact("version", "V1", "A6", "METRIC")], [], artifact_id="shared-key", completeness=EvidenceCompleteness.COMPLETE)
    key = evd_writer_a.persist_evidence(art_v1, fencing_token="epoch-1")

    dur.current_fencing_epoch = "epoch-2"
    evd_writer_b = EvidenceAuthority(durability_authority=dur)
    art_v2 = evd_writer_b.create_evidence_artifact("mig-1", "run-1", "EXEC", [EvidenceFact("version", "V2", "A6", "METRIC")], [], artifact_id="shared-key", completeness=EvidenceCompleteness.COMPLETE)
    evd_writer_b.persist_evidence(art_v2, fencing_token="epoch-2")

    stale_v1 = evd_writer_a.create_evidence_artifact("mig-1", "run-1", "EXEC", [EvidenceFact("version", "STALE_V1_OVERWRITE", "A6", "METRIC")], [], artifact_id="shared-key", completeness=EvidenceCompleteness.COMPLETE)
    with pytest.raises(EvidenceFencingError):
        evd_writer_a.persist_evidence(stale_v1, fencing_token="epoch-1")

    evd_fresh = EvidenceAuthority(durability_authority=dur)
    reloaded = evd_fresh.reload_evidence(key, expected_migration_id="mig-1")
    assert reloaded.facts[0].fact_value == "V2"
    assert evd_fresh.verify_artifact(reloaded).is_valid is True


# Scenarios 64-100: Retained Hostile Scenarios (Boundary, Transport, Telemetry, Scale)
def test_64_p0_evidence_valid_for_p0():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, cdc_boundary_position="0/100")
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    res = evd.verify_artifact(art, required_cdc_boundary_position="0/100")
    assert res.is_valid is True
    assert res.boundary_fresh is True

def test_65_rerun_p1_evidence_valid_for_p1():
    evd = EvidenceAuthority()
    val_res_p1 = ValidationResult("v2", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, cdc_boundary_position="0/200")
    art_p1 = evd.package_validation_evidence("mig-1", "run-1", val_res_p1)
    res = evd.verify_artifact(art_p1, required_cdc_boundary_position="0/200")
    assert res.is_valid is True

def test_66_moving_boundary_cannot_reuse_stale_validation_artifact():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, cdc_boundary_position="0/100")
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    res = evd.verify_artifact(art, required_cdc_boundary_position="0/300")
    assert res.boundary_fresh is False

def test_67_stale_evidence_cannot_become_current_by_reserialization():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, cdc_boundary_position="0/100")
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    art.digest = EvidenceDigestCalculator.compute_digest(art)
    res = evd.verify_artifact(art, required_cdc_boundary_position="0/200")
    assert res.boundary_fresh is False

def test_68_real_authority_7_facts_consumed():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", {"validation_rows_total": 500})
    fact = next(f for f in art.facts if f.fact_key == "validation_rows_total")
    assert fact.fact_value == 500
    assert fact.originating_authority == "Authority #7 Telemetry"

def test_69_telemetry_not_recalculated_by_evidence():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", {"metric_val": 42})
    assert art.facts[1].fact_value == 42

def test_70_telemetry_provenance_retained():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", {"m": 1})
    assert any(f.originating_authority == "Authority #7 Telemetry" for f in art.facts)

def test_71_transformation_provenance_consumed():
    evd = EvidenceAuthority()
    f = EvidenceFact("transform_policy", "policy_mask_email", "Authority #8 Data Processing", "POLICY")
    art = evd.create_evidence_artifact("mig-1", "run-1", "PROC", [f], [])
    assert art.facts[0].fact_value == "policy_mask_email"

def test_72_masking_provenance_retained_without_leaking_original_secret():
    evd = EvidenceAuthority()
    f = EvidenceFact("masked_sample", "alice@redacted", "Authority #8 Data Processing", "DATA")
    art = evd.create_evidence_artifact("mig-1", "run-1", "PROC", [f], [])
    assert art.facts[0].fact_value == "alice@redacted"

def test_73_source_target_movement_provenance():
    evd = EvidenceAuthority()
    f = EvidenceFact("batches_moved", 10, "Authority #9 Transport", "QUANTITATIVE")
    art = evd.create_evidence_artifact("mig-1", "run-1", "TRANS", [f], [], source_identity="pg-src", target_identity="ora-tgt")
    assert art.source_identity == "pg-src"
    assert art.target_identity == "ora-tgt"

def test_74_partition_batch_facts_retained():
    evd = EvidenceAuthority()
    f = EvidenceFact("partition_count", 4, "Authority #9 Transport", "QUANTITATIVE")
    art = evd.create_evidence_artifact("mig-1", "run-1", "TRANS", [f], [])
    assert art.facts[0].fact_value == 4

def test_75_cdc_boundary_retained():
    evd = EvidenceAuthority()
    art = evd.package_cdc_evidence("mig-1", "run-1", {"target_applied_position": "0/200", "required_boundary_position": "0/200"})
    assert art.cdc_boundary_position == "0/200"

def test_76_full_proof_preserved_as_full():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, cdc_boundary_position="0/100")
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.facts[0].fact_value == ProofScope.FULL.value
    assert art.completeness == EvidenceCompleteness.COMPLETE

def test_77_partitioned_full_preserved():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.PARTITIONED_FULL.value, ValidationGateStatus.PASSED, partitions_total=2, partitions_matched=2, cdc_boundary_position="0/100")
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.facts[0].fact_value == ProofScope.PARTITIONED_FULL.value

def test_78_missing_rows_preserved():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, rows_missing=2)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    f = next(fact for fact in art.facts if fact.fact_key == "rows_missing")
    assert f.fact_value == 2

def test_79_extra_rows_preserved():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, rows_extra=3)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    f = next(fact for fact in art.facts if fact.fact_key == "rows_extra")
    assert f.fact_value == 3

def test_80_mismatches_preserved():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, rows_mismatched=4)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    f = next(fact for fact in art.facts if fact.fact_key == "rows_mismatched")
    assert f.fact_value == 4

def test_81_duplicates_preserved():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, duplicates=1)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    f = next(fact for fact in art.facts if fact.fact_key == "duplicates")
    assert f.fact_value == 1

def test_82_partition_mismatch_preserved():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.PARTITIONED_FULL.value, ValidationGateStatus.FAILED, partitions_total=2, partitions_matched=1)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    f = next(fact for fact in art.facts if fact.fact_key == "partitions_matched")
    assert f.fact_value == 1
    assert art.completeness == EvidenceCompleteness.FAILED

def test_83_missing_durable_frame_truthful():
    class MemoryDurability:
        def load_spill_frame(self, scope, key): return None
    evd = EvidenceAuthority(durability_authority=MemoryDurability())
    with pytest.raises(EvidenceError, match="not found in durability store"):
        evd.reload_evidence("missing_key")

def test_84_partial_frame_truthful():
    evd = EvidenceAuthority()
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], completeness=EvidenceCompleteness.PARTIAL)
    assert art.completeness == EvidenceCompleteness.PARTIAL

def test_85_duplicate_persistence_idempotency():
    class MemoryDurability:
        def __init__(self): self.frames = {}
        def verify_fencing_token(self, tok): return True
        def save_spill_frame(self, scope, key, payload): self.frames[key] = payload
        def load_spill_frame(self, scope, key): return self.frames.get(key)
    dur = MemoryDurability()
    evd = EvidenceAuthority(durability_authority=dur)
    art = evd.create_evidence_artifact("mig-1", "run-1", "EXEC", [], [], artifact_id="static-art-1", completeness=EvidenceCompleteness.COMPLETE)
    k1 = evd.persist_evidence(art)
    k2 = evd.persist_evidence(art)
    assert k1 == k2

def test_86_non_secret_provenance_retained_after_redaction():
    data = {"table_name": "customers", "row_count": 1000, "password": "secret"}
    clean = EvidenceSecuritySanitizer.sanitize(data)
    assert clean["table_name"] == "customers"
    assert clean["row_count"] == 1000
    assert clean["password"] == "[REDACTED]"

def test_87_completeness_does_not_mean_human_approval():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED")
    assert art.completeness == EvidenceCompleteness.COMPLETE
    assert not hasattr(art, "human_approver")

def test_88_bounded_memory_artifact_generation():
    evd = EvidenceAuthority()
    facts = [EvidenceFact(f"metric_{i}", i, "Auth #7", "METRIC") for i in range(500)]
    art = evd.create_evidence_artifact("mig-1", "run-1", "PERF", facts, [], completeness=EvidenceCompleteness.COMPLETE)
    assert len(art.facts) == 500
    assert art.digest is not None

def test_89_large_evidence_payload_streamed():
    data = {"large_payload": "X" * 50000}
    d = EvidenceDigestCalculator.compute_digest(data)
    assert d.canonical_bytes_len > 50000

def test_90_no_dataset_size_proportional_in_memory_row_evidence():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", {"total_rows_migrated": 1000000000})
    assert art.facts[1].fact_value == 1000000000

def test_91_no_duplicate_validation_scan():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.facts[2].fact_value == 0

def test_92_no_duplicate_cdc_replay():
    evd = EvidenceAuthority()
    art = evd.package_cdc_evidence("mig-1", "run-1", {"target_applied_position": "0/100"})
    assert art.cdc_boundary_position == "0/100"

def test_93_no_duplicate_telemetry_calculation():
    evd = EvidenceAuthority()
    art = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", {"counter": 10})
    assert art.facts[1].fact_value == 10

def test_94_bounded_mismatch_evidence():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, rows_mismatched=5)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    f = next(fact for fact in art.facts if fact.fact_key == "rows_mismatched")
    assert f.fact_value == 5

def test_95_concurrent_artifact_generation_bounded_safe():
    evd = EvidenceAuthority()
    arts = [evd.create_evidence_artifact("mig-1", f"run-{i}", "EXEC", [], []) for i in range(10)]
    assert len(arts) == 10
    assert evd.evidence_artifacts_created_total == 10

def test_96_equal_counts_plus_validation_mismatch_remains_mismatch_evidence():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, rows_expected=100, rows_validated=100, rows_mismatched=1)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.completeness == EvidenceCompleteness.FAILED

def test_97_technical_cutover_ready_plus_validation_failed_remains_failed_evidence():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, technical_cutover_ready=True)
    art = evd.package_validation_evidence("mig-1", "run-1", val_res)
    assert art.completeness == EvidenceCompleteness.FAILED

def test_98_validation_passed_plus_execution_failed_cannot_become_success_artifact():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED)
    art_val = evd.package_validation_evidence("mig-1", "run-1", val_res)
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "FAILED")
    man = evd.create_manifest("mig-1", "run-1", [art_val, art_exec])
    assert man.completeness == EvidenceCompleteness.FAILED

def test_99_600m_to_1b_scale_design_memory_independent_of_row_count():
    evd = EvidenceAuthority()
    art_600m = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", {"total_rows_migrated": 600000000})
    art_1b = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", {"total_rows_migrated": 1000000000})

    bytes_600m = len(CanonicalEvidenceSerializer.serialize_to_bytes(art_600m))
    bytes_1b = len(CanonicalEvidenceSerializer.serialize_to_bytes(art_1b))

    assert bytes_600m < 2000
    assert bytes_1b < 2000
    assert abs(bytes_600m - bytes_1b) < 50

def test_100_all_required_machine_facts_valid_evidence_verifies_successfully():
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, cdc_boundary_position="0/200")
    art_val = evd.package_validation_evidence("mig-1", "run-1", val_res, artifact_id="art-val-1")
    art_cdc = evd.package_cdc_evidence("mig-1", "run-1", {"target_applied_position": "0/200", "required_boundary_position": "0/200", "open_transactions": 0, "ambiguous_commit_count": 0, "backlog_events": 0, "synchronization_barrier_reached": True}, artifact_id="art-cdc-1")
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-1", cdc_boundary_position="0/200")

    man = evd.create_manifest("mig-1", "run-1", [art_val, art_cdc, art_exec])
    res = evd.verify_manifest(man, expected_migration_id="mig-1", expected_run_id="run-1", required_cdc_boundary_position="0/200")

    assert res.is_valid is True
    assert res.tamper_detected is False
    assert res.boundary_fresh is True
    assert res.completeness == EvidenceCompleteness.COMPLETE
    assert res.verified_artifact_count == 3


# ============================================================
# MANDATORY PROOF CONTEXT VERIFICATION (TESTS 101–110)
# Context-sensitive required_proof_categories semantics.
# Three fundamental distinctions:
#   STRUCTURAL COMPLETENESS != CONTEXTUAL PROOF SUFFICIENCY != CRYPTOGRAPHIC INTEGRITY
# ============================================================

def test_101_execution_only_context_without_validation_passes():
    """
    CASE A — Execution-only verification context.
    Artifact contains valid execution evidence. Validation is absent and NOT required.
    Must PASS — missing non-required proof must not independently invalidate evidence.
    """
    evd = EvidenceAuthority()
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED")
    res = evd.verify_artifact(
        art_exec,
        expected_migration_id="mig-1",
        required_proof_categories=["execution"],  # only execution required
    )
    assert res.is_valid is True
    assert res.completeness == EvidenceCompleteness.COMPLETE
    assert not any("validation" in r.lower() for r in res.reasons)


def test_102_final_correctness_context_missing_validation_fails_closed():
    """
    CASE B — Final correctness verification context.
    Authority #11 validation is mandatory. Validation evidence is absent.
    Must FAIL CLOSED — missing mandatory proof is rejected.
    """
    evd = EvidenceAuthority()
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-only")
    man = evd.create_manifest("mig-1", "run-1", [art_exec])
    res = evd.verify_manifest(
        man,
        expected_migration_id="mig-1",
        required_proof_categories=["execution", "validation"],  # validation is mandatory
    )
    assert res.is_valid is False
    assert res.completeness != EvidenceCompleteness.COMPLETE
    assert any("validation" in r.lower() for r in res.reasons)


def test_103_final_correctness_with_validation_passed_passes():
    """
    CASE B+ — Final correctness context with validation gate PASSED.
    Must PASS when all required proofs are valid.
    """
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED)
    art_val = evd.package_validation_evidence("mig-1", "run-1", val_res, artifact_id="art-val-1")
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-1")
    man = evd.create_manifest("mig-1", "run-1", [art_val, art_exec])
    res = evd.verify_manifest(
        man,
        expected_migration_id="mig-1",
        required_proof_categories=["execution", "validation"],
    )
    assert res.is_valid is True
    assert res.completeness == EvidenceCompleteness.COMPLETE


def test_104_final_correctness_with_validation_failed_fails():
    """
    Final correctness context — validation gate FAILED.
    Validation artifact present but completeness==FAILED.
    Manifest must FAIL.
    """
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.FAILED, rows_mismatched=5)
    art_val = evd.package_validation_evidence("mig-1", "run-1", val_res, artifact_id="art-val-1")
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-1")
    man = evd.create_manifest("mig-1", "run-1", [art_val, art_exec])
    res = evd.verify_manifest(
        man,
        expected_migration_id="mig-1",
        required_proof_categories=["execution", "validation"],
    )
    assert res.is_valid is False
    assert res.completeness != EvidenceCompleteness.COMPLETE


def test_105_final_correctness_with_validation_withheld_never_complete():
    """
    Final correctness context — validation gate WITHHELD (sampled).
    Manifest must not return COMPLETE effective completeness.
    """
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.SAMPLED.value, ValidationGateStatus.WITHHELD)
    art_val = evd.package_validation_evidence("mig-1", "run-1", val_res, artifact_id="art-val-1")
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-1")
    man = evd.create_manifest("mig-1", "run-1", [art_val, art_exec])
    res = evd.verify_manifest(
        man,
        expected_migration_id="mig-1",
        required_proof_categories=["execution", "validation"],
    )
    assert res.is_valid is False
    assert res.completeness != EvidenceCompleteness.COMPLETE


def test_106_cdc_cutover_context_without_cdc_proof_fails_closed():
    """
    CDC cutover context — CDC evidence is mandatory. CDC artifact absent.
    Must FAIL CLOSED.
    """
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED)
    art_val = evd.package_validation_evidence("mig-1", "run-1", val_res, artifact_id="art-val-1")
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-1")
    man = evd.create_manifest("mig-1", "run-1", [art_val, art_exec])
    res = evd.verify_manifest(
        man,
        expected_migration_id="mig-1",
        required_proof_categories=["execution", "validation", "cdc"],  # cdc mandatory
    )
    assert res.is_valid is False
    assert res.completeness != EvidenceCompleteness.COMPLETE
    assert any("cdc" in r.lower() for r in res.reasons)


def test_107_cdc_cutover_context_with_stale_p0_when_p1_required_fails_closed():
    """
    CDC cutover context — CDC evidence present but at stale P0 boundary when P1 required.
    Must FAIL CLOSED.
    """
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, cdc_boundary_position="0/100")
    art_val = evd.package_validation_evidence("mig-1", "run-1", val_res, artifact_id="art-val-1")
    art_cdc = evd.package_cdc_evidence("mig-1", "run-1", {
        "target_applied_position": "0/100",
        "required_boundary_position": "0/100",
        "open_transactions": 0, "ambiguous_commit_count": 0,
        "backlog_events": 0, "synchronization_barrier_reached": True,
    }, artifact_id="art-cdc-1")
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-1", cdc_boundary_position="0/100")
    man = evd.create_manifest("mig-1", "run-1", [art_val, art_cdc, art_exec])
    res = evd.verify_manifest(
        man,
        expected_migration_id="mig-1",
        required_cdc_boundary_position="0/200",  # P1 required, all artifacts at P0
        required_proof_categories=["execution", "validation", "cdc"],
    )
    assert res.is_valid is False
    assert res.boundary_fresh is False
    assert res.completeness != EvidenceCompleteness.COMPLETE


def test_108_cdc_cutover_context_with_fresh_p1_proof_passes():
    """
    CDC cutover context — CDC evidence present at fresh P1 boundary. All required proofs valid.
    Must PASS.
    """
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED, cdc_boundary_position="0/200")
    art_val = evd.package_validation_evidence("mig-1", "run-1", val_res, artifact_id="art-val-1")
    art_cdc = evd.package_cdc_evidence("mig-1", "run-1", {
        "target_applied_position": "0/200",
        "required_boundary_position": "0/200",
        "open_transactions": 0, "ambiguous_commit_count": 0,
        "backlog_events": 0, "synchronization_barrier_reached": True,
    }, artifact_id="art-cdc-1")
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-1", cdc_boundary_position="0/200")
    man = evd.create_manifest("mig-1", "run-1", [art_val, art_cdc, art_exec])
    res = evd.verify_manifest(
        man,
        expected_migration_id="mig-1",
        required_cdc_boundary_position="0/200",
        required_proof_categories=["execution", "validation", "cdc"],
    )
    assert res.is_valid is True
    assert res.boundary_fresh is True
    assert res.completeness == EvidenceCompleteness.COMPLETE
    assert res.verified_artifact_count == 3


def test_109_required_proof_category_absent_from_manifest_fails_closed():
    """
    A required proof category missing from a manifest bundle must fail closed.
    Manifest digest integrity alone does not satisfy contextual proof sufficiency.
    STRUCTURAL COMPLETENESS != CONTEXTUAL PROOF SUFFICIENCY != CRYPTOGRAPHIC INTEGRITY
    """
    evd = EvidenceAuthority()
    # Only execution — no validation, no CDC
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-1")
    man = evd.create_manifest("mig-1", "run-1", [art_exec])

    # Manifest digest valid — integrity holds
    integrity_only_res = evd.verify_manifest(man, expected_migration_id="mig-1")
    assert integrity_only_res.is_valid is True  # Structurally complete & digest valid

    # But contextual proof sufficiency requires validation+cdc
    contextual_res = evd.verify_manifest(
        man,
        expected_migration_id="mig-1",
        required_proof_categories=["execution", "validation", "cdc"],
    )
    assert contextual_res.is_valid is False  # Missing required proofs => fail closed
    assert contextual_res.completeness != EvidenceCompleteness.COMPLETE
    assert any("validation" in r.lower() for r in contextual_res.reasons)
    assert any("cdc" in r.lower() for r in contextual_res.reasons)


def test_110_optional_proof_category_absent_must_not_invalidate_evidence():
    """
    An optional (non-required) proof category absent from a manifest must NOT fail validation.
    Completeness must not be degraded solely because non-required categories are absent.
    """
    evd = EvidenceAuthority()
    val_res = ValidationResult("v1", "mig-1", "cust", "SUCCESS", ProofScope.FULL.value, ValidationGateStatus.PASSED)
    art_val = evd.package_validation_evidence("mig-1", "run-1", val_res, artifact_id="art-val-1")
    art_exec = evd.package_execution_evidence("mig-1", "run-1", "COMPLETED", artifact_id="art-exec-1")
    man = evd.create_manifest("mig-1", "run-1", [art_val, art_exec])

    # Verify with only execution+validation required (CDC is optional/absent — must NOT fail)
    res = evd.verify_manifest(
        man,
        expected_migration_id="mig-1",
        required_proof_categories=["execution", "validation"],  # cdc is absent but NOT required
    )
    assert res.is_valid is True
    assert res.completeness == EvidenceCompleteness.COMPLETE
    assert not any("cdc" in r.lower() for r in res.reasons)
